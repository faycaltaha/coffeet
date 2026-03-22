#!/usr/bin/env python3
"""
Car Dealer Scraper - leboncoin.fr (Île-de-France)
Identifies cheap cars with high resale potential.

Usage:
    python3 car_dealer_scraper.py                    # live scrape
    python3 car_dealer_scraper.py --demo             # demo with mock data
    python3 car_dealer_scraper.py --max-price 6000 --top 30
    python3 car_dealer_scraper.py --export results.json
"""

import argparse
import json
import os
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────

LEBONCOIN_API = "https://api.leboncoin.fr/finder/classified/search"
CATEGORY_CARS = "2"
IDF_REGION = "12"  # Île-de-France region code in leboncoin

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Content-Type": "application/json",
    "Origin": "https://www.leboncoin.fr",
    "Referer": "https://www.leboncoin.fr/",
    "api_key": "ba0c2dad52b3565c9a1be3a1d3b5cc2e",  # public key embedded in LBC frontend
}

CURRENT_YEAR = datetime.now().year

# ─────────────────────────────────────────────────────────────
# Market knowledge for ROI scoring
# ─────────────────────────────────────────────────────────────

# Models known for high resale demand in France (sorted by desirability)
HIGH_DEMAND_MODELS = {
    # Compact SUVs / crossovers — best sellers
    "duster": 30, "captur": 28, "peugeot 2008": 28, "clio": 25,
    "polo": 25, "golf": 30, "tiguan": 28, "3008": 28, "208": 25,
    "yaris": 28, "corolla": 25, "c3": 22, "sandero": 22,
    # Premiums — high margin potential
    "bmw serie 3": 32, "bmw serie 1": 28, "serie 3": 32, "serie 1": 28,
    "audi a3": 30, "audi a4": 28, "mercedes classe a": 28, "classe a": 28,
    "mercedes classe c": 30, "classe c": 30,
    # Vans / utility — trade value
    "berlingo": 28, "kangoo": 26, "partner": 26, "transit": 22,
    # Reliable Japanese
    "honda civic": 28, "mazda 3": 26, "mazda cx-5": 28,
}

# Brands — base resale score bonus
BRAND_SCORES = {
    "toyota": 20, "honda": 18, "mazda": 16,       # Most reliable
    "volkswagen": 15, "audi": 15, "bmw": 14, "mercedes": 13,  # Premium
    "renault": 10, "peugeot": 10, "citroen": 9, "dacia": 12,   # Common / easy parts
    "ford": 10, "opel": 8, "seat": 10, "skoda": 12,
    "hyundai": 13, "kia": 13, "nissan": 10, "mitsubishi": 11,
    "fiat": 7, "alfa romeo": 6, "lancia": 3,       # Harder to sell
}

# Fuel type scoring for resale
FUEL_SCORES = {
    "diesel": 8,    # Good resale especially > 100k km
    "essence": 10,  # Better for city use, lower CTM cost
    "hybride": 15,  # Premium resale
    "electrique": 12,
    "gpl": 5,
    "": 5,
}

# Gearbox
GEARBOX_SCORES = {
    "automatique": 10,
    "manuelle": 5,
    "": 5,
}

# ─────────────────────────────────────────────────────────────
# Known problematic engines — hard blacklist (pre-filter)
# ─────────────────────────────────────────────────────────────
# Format: (title_keyword, brand_or_None, reason)
# A listing matches if title_keyword is found in the ad title (case-insensitive)
# and brand matches (or brand is None = match any brand).

ENGINE_BLACKLIST: list[tuple[str, Optional[str], str]] = [
    # Peugeot / Citroën / Opel 1.2 PureTech — timing chain stretches, snaps
    ("puretech", None,        "1.2 PureTech: timing chain failure (PSA/Stellantis recall issue)"),
    ("1.2 vti", "peugeot",    "1.2 VTi: camshaft follower wear, oil starvation"),
    ("1.2 vti", "citroen",    "1.2 VTi: camshaft follower wear, oil starvation"),

    # Renault 1.2 TCe 115 / 120 — timing chain + head gasket
    ("1.2 tce 115", "renault", "1.2 TCe 115: timing chain stretch + head gasket failure"),
    ("1.2 tce 120", "renault", "1.2 TCe 120: timing chain stretch + head gasket failure"),
    ("1.2 tce 130", "renault", "1.2 TCe 130: timing chain stretch + head gasket failure"),

    # Fiat 1.4 MultiAir T-Jet — inlet valve carbon build-up + timing
    ("1.4 multiair", None,    "1.4 MultiAir: valve carbon build-up, expensive to fix"),
    ("1.4 t-jet", "fiat",     "1.4 T-Jet: timing belt on wet clutch, frequent failures"),

    # BMW N47 diesel — timing chain at rear of engine (catastrophic)
    ("n47",   "bmw",          "BMW N47: rear timing chain — catastrophic failure, €4k+ repair"),
    ("116d",  "bmw",          "BMW N47 (116d): rear timing chain catastrophic failure risk"),
    ("118d",  "bmw",          "BMW N47 (118d): rear timing chain catastrophic failure risk"),
    ("120d",  "bmw",          "BMW N47 (120d): rear timing chain catastrophic failure risk"),
    ("318d",  "bmw",          "BMW N47 (318d): rear timing chain catastrophic failure risk"),
    ("320d",  "bmw",          "BMW N47 (320d): rear timing chain catastrophic failure risk"),

    # Volkswagen / Audi EA189 1.6 TDI — injector + EGR issues (less severe, flag only)
    # ("1.6 tdi", "volkswagen", "1.6 TDI: EGR/injector issues, also Dieselgate-affected"),

    # Ford EcoBoost 1.0 — head gasket / coolant mixing with oil
    ("1.0 ecoboost", "ford",  "1.0 EcoBoost: head gasket failure, coolant leaks into oil"),
    ("1.0 scti",     "ford",  "1.0 EcoBoost (SCTi): head gasket failure risk"),

    # Alfa Romeo / Fiat 1.4 TB MultiAir
    ("1.4 tb multiair", None, "1.4 TB MultiAir: valve actuator failures, expensive parts"),

    # Opel / Vauxhall 1.6 CDTI — timing chain
    ("1.6 cdti", "opel",      "1.6 CDTI: timing chain tensioner failure, engine damage"),
]

# ─────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────

@dataclass
class CarListing:
    ad_id: str
    title: str
    price: int
    year: Optional[int]
    mileage: Optional[int]
    fuel: str
    gearbox: str
    brand: str
    model: str
    location: str
    url: str
    images: list[str] = field(default_factory=list)
    # computed by ROI scorer
    roi_score: float = 0.0
    estimated_resale: int = 0
    estimated_profit: int = 0
    roi_reasons: list[str] = field(default_factory=list)
    # engine blacklist check
    blacklisted: bool = False
    blacklist_reason: str = ""
    # mechanic agent verdict
    mechanic_verdict: str = ""          # "BUY" | "INSPECT" | "AVOID" | ""
    mechanic_issues: list[str] = field(default_factory=list)
    mechanic_notes: str = ""


# ─────────────────────────────────────────────────────────────
# Scraper
# ─────────────────────────────────────────────────────────────

class LeboncoinScraper:
    def __init__(self, max_price: int = 8000, min_price: int = 500,
                 max_pages: int = 5, min_year: int = 2005,
                 max_mileage: int = 250000):
        self.max_price = max_price
        self.min_price = min_price
        self.max_pages = max_pages
        self.min_year = min_year
        self.max_mileage = max_mileage
        self.client = httpx.Client(headers=HEADERS, timeout=20, follow_redirects=True)
        self.console = Console()

    def _build_payload(self, offset: int = 0) -> dict:
        return {
            "filters": {
                "category": {"id": CATEGORY_CARS},
                "location": {"regions": [IDF_REGION]},
                "keywords": {},
                "ranges": {
                    "price": {"min": self.min_price, "max": self.max_price},
                    "regdate": {"min": self.min_year},
                },
                "enums": {},
            },
            "limit": 35,
            "limit_alu": 3,
            "offset": offset,
            "sort_by": "price",
            "sort_order": "asc",
            "owner_type": "private",  # private sellers only = better deals
        }

    def _extract_attribute(self, attributes: list, key: str) -> str:
        for attr in attributes:
            if attr.get("key") == key:
                values = attr.get("value_label") or attr.get("values_label")
                if isinstance(values, list):
                    return values[0] if values else ""
                return values or attr.get("value", "")
        return ""

    def _parse_listing(self, ad: dict) -> Optional[CarListing]:
        try:
            attrs = ad.get("attributes", [])
            price_raw = ad.get("price", [None])
            price = price_raw[0] if isinstance(price_raw, list) and price_raw else price_raw
            if not price or not isinstance(price, (int, float)):
                return None
            price = int(price)

            year_str = self._extract_attribute(attrs, "regdate")
            try:
                year = int(year_str) if year_str else None
            except ValueError:
                year = None

            mileage_str = self._extract_attribute(attrs, "mileage")
            try:
                mileage = int(mileage_str.replace(" ", "").replace("km", "")) if mileage_str else None
            except (ValueError, AttributeError):
                mileage = None

            fuel = self._extract_attribute(attrs, "fuel").lower()
            gearbox = self._extract_attribute(attrs, "gearbox").lower()
            brand = self._extract_attribute(attrs, "brand").lower()
            model_name = self._extract_attribute(attrs, "model").lower()
            location_city = ad.get("location", {}).get("city", "")
            location_dept = ad.get("location", {}).get("department_id", "")
            location = f"{location_city} ({location_dept})" if location_city else location_dept

            images = []
            for img in ad.get("images", {}).get("urls_large", [])[:3]:
                images.append(img)

            ad_id = str(ad.get("list_id", ""))
            url = f"https://www.leboncoin.fr/voitures/{ad_id}.htm"

            listing = CarListing(
                ad_id=ad_id,
                title=ad.get("subject", ""),
                price=price,
                year=year,
                mileage=mileage,
                fuel=fuel,
                gearbox=gearbox,
                brand=brand,
                model=model_name,
                location=location,
                url=url,
                images=images,
            )

            # Filter out high mileage
            if mileage and mileage > self.max_mileage:
                return None
            # Filter out very old cars
            if year and year < self.min_year:
                return None

            return listing
        except Exception:
            return None

    def fetch_page(self, offset: int) -> list[CarListing]:
        payload = self._build_payload(offset)
        try:
            resp = self.client.post(LEBONCOIN_API, json=payload)
            if resp.status_code == 429:
                self.console.print("[yellow]Rate limited, waiting 10s...[/yellow]")
                time.sleep(10)
                resp = self.client.post(LEBONCOIN_API, json=payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            self.console.print(f"[red]HTTP error {e.response.status_code} on page offset={offset}[/red]")
            return []
        except Exception as e:
            self.console.print(f"[red]Error fetching page: {e}[/red]")
            return []

        ads = data.get("ads", [])
        listings = []
        for ad in ads:
            listing = self._parse_listing(ad)
            if listing:
                listings.append(listing)
        return listings

    def scrape(self) -> list[CarListing]:
        all_listings = []
        with self.console.status("[bold green]Scraping leboncoin.fr Île-de-France cars...") as status:
            for page in range(self.max_pages):
                offset = page * 35
                status.update(f"[bold green]Fetching page {page + 1}/{self.max_pages} (offset={offset})...")
                listings = self.fetch_page(offset)
                if not listings:
                    self.console.print(f"[yellow]No results on page {page + 1}, stopping.[/yellow]")
                    break
                all_listings.extend(listings)
                self.console.print(f"  Page {page + 1}: {len(listings)} listings fetched")
                if page < self.max_pages - 1:
                    time.sleep(1.5)  # polite delay
        return all_listings


# ─────────────────────────────────────────────────────────────
# ROI Scoring Engine
# ─────────────────────────────────────────────────────────────

class ROIScorer:
    """
    Scores each listing based on:
    1. Price undervaluation vs market
    2. Brand/model resale demand
    3. Age & mileage quality ratio
    4. Fuel type desirability
    5. Gearbox type
    """

    def score(self, listing: CarListing) -> CarListing:
        score = 0.0
        reasons = []

        # ── Brand score ──────────────────────────────────────────
        brand_bonus = BRAND_SCORES.get(listing.brand, 5)
        score += brand_bonus
        if brand_bonus >= 15:
            reasons.append(f"Premium brand ({listing.brand.title()})")
        elif brand_bonus >= 12:
            reasons.append(f"High-demand brand ({listing.brand.title()})")

        # ── Model score ──────────────────────────────────────────
        model_bonus = 0
        for model_key, pts in HIGH_DEMAND_MODELS.items():
            if model_key in listing.title.lower() or model_key in listing.model.lower():
                model_bonus = max(model_bonus, pts)
        score += model_bonus
        if model_bonus >= 25:
            reasons.append(f"Top-selling model (high demand)")
        elif model_bonus >= 15:
            reasons.append(f"Good market demand model")

        # ── Fuel score ───────────────────────────────────────────
        fuel_bonus = FUEL_SCORES.get(listing.fuel, 5)
        score += fuel_bonus
        if fuel_bonus >= 12:
            reasons.append(f"Desirable fuel type ({listing.fuel})")

        # ── Gearbox ──────────────────────────────────────────────
        gb_bonus = GEARBOX_SCORES.get(listing.gearbox, 5)
        score += gb_bonus
        if gb_bonus >= 10:
            reasons.append("Automatic gearbox (wider buyer pool)")

        # ── Age scoring ──────────────────────────────────────────
        if listing.year:
            age = CURRENT_YEAR - listing.year
            if age <= 5:
                score += 25
                reasons.append(f"Recent vehicle ({listing.year}, {age}y)")
            elif age <= 8:
                score += 18
                reasons.append(f"Modern vehicle ({listing.year}, {age}y)")
            elif age <= 12:
                score += 10
            elif age <= 15:
                score += 5
            else:
                score -= 5  # very old

        # ── Mileage scoring ──────────────────────────────────────
        if listing.mileage:
            km = listing.mileage
            if km < 50_000:
                score += 25
                reasons.append(f"Low mileage ({km:,} km)")
            elif km < 100_000:
                score += 18
                reasons.append(f"Reasonable mileage ({km:,} km)")
            elif km < 150_000:
                score += 8
            elif km < 200_000:
                score += 2
            else:
                score -= 10

            # Mileage/year ratio
            if listing.year:
                age = max(1, CURRENT_YEAR - listing.year)
                km_per_year = km / age
                if km_per_year < 10_000:
                    score += 10
                    reasons.append(f"Excellent km/year ratio ({km_per_year:,.0f} km/yr)")
                elif km_per_year < 15_000:
                    score += 5
                elif km_per_year > 25_000:
                    score -= 8
                    reasons.append(f"High annual mileage ({km_per_year:,.0f} km/yr)")

        # ── Price undervaluation score ────────────────────────────
        estimated_resale = self._estimate_resale(listing)
        listing.estimated_resale = estimated_resale
        if estimated_resale > 0 and listing.price > 0:
            margin = estimated_resale - listing.price
            margin_pct = (margin / listing.price) * 100
            listing.estimated_profit = margin

            if margin_pct >= 60:
                score += 40
                reasons.append(f"Potentially underpriced by ~{margin_pct:.0f}% (est. resale €{estimated_resale:,})")
            elif margin_pct >= 40:
                score += 28
                reasons.append(f"Good margin ~{margin_pct:.0f}% (est. resale €{estimated_resale:,})")
            elif margin_pct >= 25:
                score += 16
                reasons.append(f"Decent margin ~{margin_pct:.0f}% (est. resale €{estimated_resale:,})")
            elif margin_pct >= 10:
                score += 8
            elif margin_pct < 0:
                score -= 15
                reasons.append(f"Overpriced vs market estimate")

        # ── Price absolute ────────────────────────────────────────
        if listing.price <= 2000:
            score += 10
            reasons.append(f"Very low entry price (€{listing.price:,})")
        elif listing.price <= 4000:
            score += 6

        listing.roi_score = round(score, 1)
        listing.roi_reasons = reasons
        return listing

    def _estimate_resale(self, listing: CarListing) -> int:
        """
        Rough market value estimate based on year, mileage, brand, and fuel.
        This is a heuristic — a real implementation would call argus/lacentrale.
        """
        if not listing.year:
            return 0

        age = CURRENT_YEAR - listing.year
        base = 25_000  # assumed new price for average car

        # Depreciation curve (French market)
        if age <= 1:
            factor = 0.80
        elif age <= 2:
            factor = 0.72
        elif age <= 3:
            factor = 0.65
        elif age <= 4:
            factor = 0.58
        elif age <= 5:
            factor = 0.52
        elif age <= 7:
            factor = 0.42
        elif age <= 10:
            factor = 0.30
        elif age <= 13:
            factor = 0.20
        elif age <= 15:
            factor = 0.14
        else:
            factor = 0.08

        value = base * factor

        # Mileage adjustment
        if listing.mileage:
            km = listing.mileage
            if km < 50_000:
                value *= 1.15
            elif km < 100_000:
                value *= 1.0
            elif km < 150_000:
                value *= 0.88
            elif km < 200_000:
                value *= 0.72
            else:
                value *= 0.55

        # Brand premium/discount
        brand_factor = {
            "toyota": 1.15, "honda": 1.10, "mazda": 1.08,
            "bmw": 1.12, "audi": 1.10, "mercedes": 1.10,
            "volkswagen": 1.05, "skoda": 1.05, "seat": 1.02,
            "renault": 0.95, "peugeot": 0.95, "citroen": 0.93,
            "dacia": 0.90, "fiat": 0.88, "opel": 0.90,
        }.get(listing.brand, 1.0)
        value *= brand_factor

        # Hybrid / EV premium
        if "hybride" in listing.fuel:
            value *= 1.10
        elif "electrique" in listing.fuel:
            value *= 1.05

        return max(500, int(round(value / 100) * 100))


# ─────────────────────────────────────────────────────────────
# Output formatter
# ─────────────────────────────────────────────────────────────

def render_results(listings: list[CarListing], console: Console, top_n: int = 20):
    if not listings:
        console.print("[red]No listings found.[/red]")
        return

    # Force wide console to prevent wrapping
    wide = Console(width=180)

    sorted_listings = sorted(listings, key=lambda x: x.roi_score, reverse=True)[:top_n]

    wide.print(f"\n[bold cyan]  Top {len(sorted_listings)} Cars — Best ROI Potential"
               f"  ·  Île-de-France  ·  leboncoin.fr (private sellers)[/bold cyan]\n")

    table = Table(
        box=box.SIMPLE_HEAVY,
        show_lines=False,
        header_style="bold magenta",
        padding=(0, 1),
    )

    table.add_column("#",        style="dim",        width=3,  justify="right")
    table.add_column("Title",    width=32)
    table.add_column("Buy",      style="bold green", width=8,  justify="right")
    table.add_column("Resale",   style="cyan",       width=8,  justify="right")
    table.add_column("Profit",   style="bold yellow",width=8,  justify="right")
    table.add_column("Year",     width=5,  justify="center")
    table.add_column("km",       width=9,  justify="right")
    table.add_column("Fuel",     width=9,  justify="center")
    table.add_column("Location", width=20)
    table.add_column("Score",    style="bold red",   width=6,  justify="right")
    table.add_column("Signals",  width=55)

    fuel_icons = {"diesel": "⛽ diesel", "essence": "⛽ essence", "hybride": "⚡ hybrid",
                  "electrique": "⚡ EV", "gpl": "🔵 GPL"}

    for i, car in enumerate(sorted_listings, 1):
        profit_text  = f"+€{car.estimated_profit:,}" if car.estimated_profit > 0 else "—"
        resale_text  = f"€{car.estimated_resale:,}"  if car.estimated_resale  > 0 else "—"
        km_text      = f"{car.mileage:,} km"         if car.mileage            else "?"
        year_text    = str(car.year)                  if car.year               else "?"
        fuel_text    = fuel_icons.get(car.fuel, car.fuel or "?")
        signals      = "  •  ".join(car.roi_reasons[:3])

        table.add_row(
            str(i),
            car.title[:32],
            f"€{car.price:,}",
            resale_text,
            profit_text,
            year_text,
            km_text,
            fuel_text,
            car.location[:20],
            str(car.roi_score),
            signals,
        )

    wide.print(table)

    wide.print("\n[bold]Direct links — top 10:[/bold]")
    for i, car in enumerate(sorted_listings[:10], 1):
        profit_str = f"  →  est. profit [bold yellow]+€{car.estimated_profit:,}[/bold yellow]" if car.estimated_profit > 0 else ""
        wide.print(
            f"  [dim]{i:2}.[/dim]  [link={car.url}][cyan]{car.url}[/cyan][/link]"
            f"  [dim]{car.title[:40]}  ·  €{car.price:,}{profit_str}[/dim]"
        )


# ─────────────────────────────────────────────────────────────
# Engine blacklist checker
# ─────────────────────────────────────────────────────────────

def apply_blacklist(listings: list[CarListing]) -> list[CarListing]:
    """Mark listings whose engine matches a known-problematic pattern."""
    for car in listings:
        title_lower = car.title.lower()
        for keyword, brand_filter, reason in ENGINE_BLACKLIST:
            if keyword in title_lower:
                if brand_filter is None or brand_filter == car.brand:
                    car.blacklisted = True
                    car.blacklist_reason = reason
                    # Also penalise score heavily
                    car.roi_score = max(0.0, car.roi_score - 60)
                    break
    return listings


# ─────────────────────────────────────────────────────────────
# Mechanic Agent — Claude-powered expert review
# ─────────────────────────────────────────────────────────────

MECHANIC_SYSTEM = """\
You are an expert used-car dealer in France with 25 years of experience and a background as a \
top automotive mechanic. You have an encyclopedic knowledge of:
- Common mechanical failures by make, model, engine, year, and mileage bracket
- Reliability data for all cars sold in France since 2000
- Resale market dynamics in Île-de-France
- Which cars are cheap to repair (parts availability, labour hours) vs money pits
- Hidden red flags: trim combos that signal fleet use, suspicious mileage, structural risk by age

Your task: review a batch of used-car listings and give a verdict for each one.

For every listing return a JSON object with exactly these keys:
  "ad_id"    : the listing's ad_id (string, unchanged)
  "verdict"  : one of "BUY" | "INSPECT" | "AVOID"
  "issues"   : array of strings — known mechanical or reliability issues for this exact \
engine/year/mileage combo. Empty array if none.
  "notes"    : 1-2 sentence dealer commentary (what to check, why it's interesting or risky)

Verdict guide:
  BUY     — solid car, known reliable engine, price is attractive, no major known issues
  INSPECT — interesting deal but has known issues that require professional inspection before buying
  AVOID   — known show-stopper defect, money pit, or the price makes no economic sense

Return ONLY a JSON array of objects, no prose, no markdown fences.
"""

class MechanicAgent:
    """
    LLM-powered expert mechanic/dealer review.

    Supported providers:
      openrouter — OpenRouter (default). Use your existing Claude/OpenAI subscription
                   or pay-per-use. Best model: anthropic/claude-opus-4-6
                   Free key: https://openrouter.ai  then: export OPENROUTER_API_KEY=sk-or-...
      ollama     — Local Ollama, 100% free, no account.
                   Install: https://ollama.com  then: ollama pull mistral
      groq       — Groq cloud free tier (generous daily limits).
                   Free key: https://console.groq.com  then: export GROQ_API_KEY=gsk_...
    """

    PROVIDERS = {
        "openrouter": {
            "base_url": "https://openrouter.ai/api/v1",
            # Claude Opus 4.6 — best reasoning + deepest automotive domain knowledge
            "default_model": "anthropic/claude-opus-4-6",
            "env_var": "OPENROUTER_API_KEY",
            "extra_headers": {
                "HTTP-Referer": "https://github.com/faycaltaha/coffeet",
                "X-Title": "Car Dealer ROI Scanner",
            },
        },
        "ollama": {
            "base_url": "http://localhost:11434/v1",
            "default_model": "mistral",
            "env_var": None,
            "api_key": "ollama",
            "extra_headers": {},
        },
        "groq": {
            "base_url": "https://api.groq.com/openai/v1",
            "default_model": "llama-3.3-70b-versatile",
            "env_var": "GROQ_API_KEY",
            "extra_headers": {},
        },
    }

    def __init__(self, console: Console, provider: str = "openrouter", model: str = ""):
        self.console = console
        if provider not in self.PROVIDERS:
            raise RuntimeError(f"Unknown provider '{provider}'. Choose: {list(self.PROVIDERS)}")

        cfg = self.PROVIDERS[provider]
        self.provider      = provider
        self.base_url      = cfg["base_url"]
        self.model         = model or cfg["default_model"]
        self.extra_headers = cfg.get("extra_headers", {})

        # Resolve API key — store lazily, validated only when _chat() is called
        env_var = cfg.get("env_var")
        self._env_var  = env_var
        self._provider = provider
        if env_var:
            self.api_key = os.environ.get(env_var, "")
        else:
            self.api_key = cfg.get("api_key", "no-key")

    def _chat(self, user_msg: str) -> str:
        """Call the OpenAI-compatible /chat/completions endpoint."""
        if not self.api_key and self._env_var:
            setup = {
                "openrouter": "Get a free key at https://openrouter.ai\n  export OPENROUTER_API_KEY=sk-or-...",
                "groq":       "Get a free key at https://console.groq.com\n  export GROQ_API_KEY=gsk_...",
            }.get(self._provider, f"export {self._env_var}=...")
            raise RuntimeError(f"Provider '{self._provider}' requires {self._env_var}.\n{setup}")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": MECHANIC_SYSTEM},
                {"role": "user",   "content": user_msg},
            ],
            "temperature": 0.2,
            "max_tokens": 4096,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.extra_headers,
        }
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def review_mock(self, listings: list[CarListing]) -> list[CarListing]:
        """Inject realistic pre-written verdicts — no API call, for demo/showcase only."""
        mock_db = {
            # title keyword → (verdict, issues, notes)
            "duster":    ("BUY",     [],
                          "The 1.5 dCi K9K engine is a Renault-Nissan workhorse — bulletproof past 300k km with regular oil changes. 4x4 version commands 15-20% premium on resale. At €3,900 this is a genuine buy."),
            "classe a":  ("INSPECT", ["W176 CDI models: DPF clogging on short trips", "7-speed DCT wet clutch can shudder if serviced late"],
                          "Good price for a Mercedes but the 180 CDI with 95k km is entering the DPF danger zone. Pull the maintenance history — if it's been city-driven, budget €600-800 for a forced regen or DPF replacement."),
            "fiat 500":  ("INSPECT", ["5-speed robotised gearbox (Dualogic) notorious for jerky engagement and clutch wear", "Rust on rear arches from 7 years old"],
                          "Lovely car that sells fast in Paris — but check under the rear arches for rust bubbles and test the Dualogic thoroughly. If manual gearbox, buy without hesitation at this price."),
            "polo":      ("BUY",     ["1.2 TSI chain tensioner: check for rattling on cold start"],
                          "VW Polo 1.2 TSI is one of the most sought-after city cars in IDF. Chain rattle on cold start is the only real concern — a €350 tensioner fix. Otherwise rock solid and sells in under a week on LBC."),
            "golf":      ("INSPECT", ["1.6 TDI: EGR valve fouling (€200-400 fix)", "High mileage: timing belt + water pump service due if not documented", "Dieselgate software update may affect performance"],
                          "Golf VII diesel at 153k km is a good workhorse but needs a documented service history. Insist on timing belt records — if unknown, budget €700 and factor it into your offer."),
            "hyundai":   ("BUY",     [],
                          "Hyundai i30 1.6 CRDi is criminally underrated on the French market — Korean build quality, cheap parts, and the diesel engine is genuinely reliable. Clean profit play at €4,100."),
            "ibiza":     ("BUY",     ["1.0 EcoTSI: carbon build-up on intake valves around 80k km (direct injection)"],
                          "SEAT Ibiza 1.0 EcoTSI is essentially a VW Polo in disguise at lower cost. Walnut-blast the intake if carbon build-up is present (~€150). Sells fast to young buyers — good flip candidate."),
            "mazda":     ("BUY",     [],
                          "Mazda CX-5 2.2 SkyActiv-D is one of the most reliable SUVs on the market — Mazda's own engine design with none of the PSA/VAG platform baggage. Strong resale, easy sell."),
            "honda":     ("INSPECT", ["i-DTEC diesel: timing chain service interval at 150k km approaching", "DPF: sensitive to short urban trips"],
                          "Honda Civic diesel is excellent mechanically but at 64k km and 2018 it's in the DPF sweet spot — fine if highway-driven, risky if city use. Ask for fuel consumption history as a proxy."),
            "kangoo":    ("BUY",     ["dCi K9K: injector wear after 150k km — still within acceptable range at 116k"],
                          "Kangoo dCi is a cash machine in IDF — tradespeople and families both want them, supply is tight. K9K diesel at 116k is young enough. Check for rust on the sliding door rails."),
        }

        for car in listings:
            title_lower = car.title.lower()
            matched = False
            for keyword, (verdict, issues, notes) in mock_db.items():
                if keyword in title_lower:
                    car.mechanic_verdict = verdict
                    car.mechanic_issues  = issues
                    car.mechanic_notes   = notes
                    matched = True
                    break
            if not matched:
                car.mechanic_verdict = "INSPECT"
                car.mechanic_issues  = ["Insufficient data for this model/engine combination"]
                car.mechanic_notes   = "Standard inspection recommended. Verify service history and request a pre-purchase diagnostic."

        return listings

    def review(self, listings: list[CarListing]) -> list[CarListing]:
        if not listings:
            return listings

        cars_data = [
            {
                "ad_id": car.ad_id,
                "title": car.title,
                "brand": car.brand,
                "price_eur": car.price,
                "year": car.year,
                "mileage_km": car.mileage,
                "fuel": car.fuel,
                "gearbox": car.gearbox,
                "estimated_resale_eur": car.estimated_resale,
                "roi_score": car.roi_score,
                "blacklisted": car.blacklisted,
                "blacklist_reason": car.blacklist_reason,
            }
            for car in listings
        ]

        user_msg = (
            f"Here are {len(cars_data)} used-car listings from Île-de-France. "
            f"Review each one and return your JSON verdict array.\n\n"
            f"{json.dumps(cars_data, ensure_ascii=False, indent=2)}"
        )

        self.console.print(
            f"\n[bold cyan]Mechanic Agent[/bold cyan] — "
            f"[dim]{self.provider}[/dim] / [dim]{self.model}[/dim] · "
            f"reviewing {len(listings)} listings  [green](free)[/green]"
        )

        try:
            with self.console.status("[dim]  ⟳ LLM thinking...[/dim]"):
                raw = self._chat(user_msg)
        except httpx.ConnectError:
            if self.provider == "ollama":
                self.console.print(
                    "[red]Cannot reach Ollama. Is it running?\n"
                    "  Install : https://ollama.com\n"
                    "  Start   : ollama serve\n"
                    "  Model   : ollama pull mistral[/red]"
                )
            else:
                self.console.print(f"[red]Network error reaching {self.provider} ({self.base_url}).[/red]")
            return listings
        except httpx.HTTPStatusError as e:
            self.console.print(f"[red]{self.provider} API error {e.response.status_code}: {e.response.text[:200]}[/red]")
            return listings

        # Strip optional markdown fences the model might add
        text = raw.strip()
        if text.startswith("```"):
            text = "\n".join(text.split("\n")[1:])
        if text.endswith("```"):
            text = "\n".join(text.split("\n")[:-1])
        text = text.strip()

        try:
            verdicts = json.loads(text)
        except json.JSONDecodeError:
            # Try to extract a JSON array from within the response
            import re
            m = re.search(r"\[.*\]", text, re.DOTALL)
            if m:
                try:
                    verdicts = json.loads(m.group())
                except json.JSONDecodeError:
                    self.console.print("[red]Could not parse mechanic JSON response.[/red]")
                    return listings
            else:
                self.console.print("[red]Could not parse mechanic JSON response.[/red]")
                return listings

        listing_map = {car.ad_id: car for car in listings}
        for v in verdicts:
            car = listing_map.get(str(v.get("ad_id", "")))
            if car:
                car.mechanic_verdict = v.get("verdict", "")
                car.mechanic_issues  = v.get("issues", [])
                car.mechanic_notes   = v.get("notes", "")

        self.console.print(
            f"[green]  ✓ Done — "
            f"{sum(1 for c in listings if c.mechanic_verdict == 'BUY')} BUY  "
            f"{sum(1 for c in listings if c.mechanic_verdict == 'INSPECT')} INSPECT  "
            f"{sum(1 for c in listings if c.mechanic_verdict == 'AVOID')} AVOID[/green]"
        )
        return listings


def render_mechanic_report(listings: list[CarListing], console: Console):
    """Print a detailed mechanic report for listings that have a verdict."""
    reviewed = [c for c in listings if c.mechanic_verdict]
    if not reviewed:
        return

    wide = Console(width=180)
    wide.print("\n[bold cyan]══ Mechanic Expert Report ══[/bold cyan]\n")

    verdict_order = {"BUY": 0, "INSPECT": 1, "AVOID": 2}
    reviewed_sorted = sorted(reviewed, key=lambda c: (verdict_order.get(c.mechanic_verdict, 9), -c.roi_score))

    for car in reviewed_sorted:
        v = car.mechanic_verdict
        colour = {"BUY": "green", "INSPECT": "yellow", "AVOID": "red"}.get(v, "white")
        icon   = {"BUY": "✅", "INSPECT": "⚠️ ", "AVOID": "🚫"}.get(v, "❔")

        km_part = f" · {car.mileage:,} km" if car.mileage else ""
        profit_part = f"  →  est. [bold yellow]+€{car.estimated_profit:,}[/bold yellow]" if car.estimated_profit > 0 else ""
        header = (
            f"[{colour}]{icon}  {v}[/{colour}]  "
            f"[bold]{car.title}[/bold]  ·  "
            f"[bold green]€{car.price:,}[/bold green]{profit_part}"
            f"  ·  {car.year or '?'}{km_part}"
            f"  ·  [dim]{car.location}[/dim]"
        )

        body_lines = []
        if car.blacklisted:
            body_lines.append(f"[red bold]⛔ BLACKLISTED ENGINE:[/red bold] {car.blacklist_reason}")
        if car.mechanic_issues:
            body_lines.append("[bold]Known issues:[/bold]  " + "  •  ".join(car.mechanic_issues))
        if car.mechanic_notes:
            body_lines.append(f"[italic]{car.mechanic_notes}[/italic]")
        body_lines.append(f"[dim]{car.url}[/dim]")

        wide.print(Panel(
            "\n".join(body_lines),
            title=header,
            border_style=colour,
            padding=(0, 2),
        ))


def generate_mock_listings(n: int = 80) -> list[CarListing]:
    """Generate realistic mock listings for demo/testing."""
    random.seed(42)
    idf_cities = [
        ("Paris 15e", "75"), ("Boulogne-Billancourt", "92"), ("Versailles", "78"),
        ("Créteil", "94"), ("Saint-Denis", "93"), ("Évry", "91"),
        ("Marne-la-Vallée", "77"), ("Cergy", "95"), ("Argenteuil", "95"),
        ("Montreuil", "93"), ("Nanterre", "92"), ("Vitry-sur-Seine", "94"),
        ("Aulnay-sous-Bois", "93"), ("Rueil-Malmaison", "92"), ("Meaux", "77"),
    ]
    samples = [
        # (brand, model, title_template, base_price, typical_year_range, typical_km)
        ("renault", "clio", "Renault Clio IV 1.2 TCe 120", 4500, (2014, 2018), (60000, 140000)),
        ("peugeot", "208", "Peugeot 208 1.2 PureTech 82", 5200, (2015, 2019), (50000, 120000)),
        ("volkswagen", "golf", "Volkswagen Golf VII 1.6 TDI 105", 7800, (2013, 2017), (80000, 180000)),
        ("dacia", "duster", "Dacia Duster 1.5 dCi 110 4x4", 6500, (2014, 2018), (70000, 160000)),
        ("toyota", "yaris", "Toyota Yaris 100h Hybride", 7200, (2015, 2019), (40000, 100000)),
        ("renault", "captur", "Renault Captur 1.5 dCi 90", 6800, (2014, 2018), (60000, 150000)),
        ("citroen", "c3", "Citroën C3 1.2 PureTech 82", 3800, (2013, 2017), (70000, 160000)),
        ("ford", "focus", "Ford Focus 1.6 TDCi 115", 4200, (2012, 2016), (90000, 200000)),
        ("bmw", "serie 1", "BMW Série 1 116d 116ch", 9500, (2013, 2017), (80000, 160000)),
        ("audi", "a3", "Audi A3 1.6 TDI 110", 8500, (2014, 2018), (70000, 150000)),
        ("peugeot", "3008", "Peugeot 3008 2.0 BlueHDi 150", 9200, (2015, 2018), (60000, 140000)),
        ("volkswagen", "polo", "Volkswagen Polo 1.2 TSI 90", 5800, (2014, 2018), (50000, 120000)),
        ("renault", "megane", "Renault Mégane III 1.5 dCi 95", 3500, (2012, 2016), (100000, 200000)),
        ("mercedes", "classe a", "Mercedes Classe A 180 CDI", 8900, (2013, 2017), (70000, 150000)),
        ("skoda", "octavia", "Skoda Octavia 1.6 TDI 105", 6200, (2013, 2017), (80000, 170000)),
        ("toyota", "corolla", "Toyota Corolla 122h Design", 12500, (2018, 2021), (30000, 70000)),
        ("hyundai", "i30", "Hyundai i30 1.6 CRDi 110", 5500, (2014, 2018), (60000, 140000)),
        ("seat", "ibiza", "SEAT Ibiza 1.0 EcoTSI 95", 4800, (2015, 2019), (50000, 120000)),
        ("opel", "astra", "Opel Astra 1.6 CDTI 110", 4100, (2013, 2017), (90000, 190000)),
        ("mazda", "cx-5", "Mazda CX-5 2.2 Skyactiv-D 150", 11000, (2015, 2019), (60000, 130000)),
        ("renault", "kangoo", "Renault Kangoo 1.5 dCi 90", 5500, (2013, 2018), (80000, 180000)),
        ("citroen", "berlingo", "Citroën Berlingo 1.6 BlueHDi 100", 6800, (2015, 2019), (70000, 160000)),
        ("honda", "civic", "Honda Civic 1.6 i-DTEC 120", 7500, (2014, 2018), (60000, 140000)),
        ("fiat", "500", "Fiat 500 1.2 69ch Lounge", 5200, (2015, 2019), (40000, 90000)),
        ("peugeot", "308", "Peugeot 308 SW 1.6 BlueHDi 120", 7200, (2015, 2018), (60000, 140000)),
    ]

    listings = []
    for i in range(n):
        brand, model, title, base_price, yr_range, km_range = random.choice(samples)
        # Introduce some pricing anomalies (underpriced listings)
        price_factor = random.choices(
            [0.45, 0.60, 0.75, 0.90, 1.0, 1.05],
            weights=[3, 8, 20, 35, 25, 9]
        )[0]
        price = max(500, int(base_price * price_factor / 100) * 100)
        year = random.randint(*yr_range)
        mileage = random.randint(*km_range)
        fuel = random.choice(["diesel", "essence", "essence", "hybride"]) if "hybride" in title.lower() else (
            "diesel" if "TDI" in title or "CDI" in title or "dCi" in title or "CDTI" in title or "BlueHDi" in title or "HDi" in title else "essence"
        )
        gearbox = random.choices(["manuelle", "automatique"], weights=[75, 25])[0]
        city, dept = random.choice(idf_cities)

        listings.append(CarListing(
            ad_id=str(2000000 + i),
            title=title,
            price=price,
            year=year,
            mileage=mileage,
            fuel=fuel,
            gearbox=gearbox,
            brand=brand,
            model=model,
            location=f"{city} ({dept})",
            url=f"https://www.leboncoin.fr/voitures/{2000000 + i}.htm",
            images=[],
        ))

    return listings


def export_json(listings: list[CarListing], path: str):
    data = []
    for car in listings:
        data.append({
            "ad_id": car.ad_id,
            "title": car.title,
            "url": car.url,
            "price": car.price,
            "year": car.year,
            "mileage": car.mileage,
            "fuel": car.fuel,
            "gearbox": car.gearbox,
            "brand": car.brand,
            "model": car.model,
            "location": car.location,
            "roi_score": car.roi_score,
            "estimated_resale": car.estimated_resale,
            "estimated_profit": car.estimated_profit,
            "roi_reasons": car.roi_reasons,
            "blacklisted": car.blacklisted,
            "blacklist_reason": car.blacklist_reason,
            "mechanic_verdict": car.mechanic_verdict,
            "mechanic_issues": car.mechanic_issues,
            "mechanic_notes": car.mechanic_notes,
            "images": car.images,
        })
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Scrape leboncoin.fr for cheap cars with high resale potential in Île-de-France"
    )
    parser.add_argument("--max-price", type=int, default=8000,
                        help="Maximum buy price in € (default: 8000)")
    parser.add_argument("--min-price", type=int, default=500,
                        help="Minimum buy price in € (default: 500)")
    parser.add_argument("--max-pages", type=int, default=5,
                        help="Number of pages to scrape (35 ads/page, default: 5)")
    parser.add_argument("--min-year", type=int, default=2005,
                        help="Minimum registration year (default: 2005)")
    parser.add_argument("--max-mileage", type=int, default=250000,
                        help="Max mileage in km (default: 250000)")
    parser.add_argument("--top", type=int, default=20,
                        help="Number of top results to display (default: 20)")
    parser.add_argument("--min-score", type=float, default=0.0,
                        help="Minimum ROI score to include (default: 0)")
    parser.add_argument("--export", type=str, default=None,
                        help="Export results to JSON file path")
    parser.add_argument("--demo", action="store_true",
                        help="Use mock data (no network required) — for testing")
    parser.add_argument("--mechanic", action="store_true",
                        help="Run LLM mechanic agent on top results (requires --llm-provider key)")
    parser.add_argument("--mechanic-mock", action="store_true",
                        help="Show example mechanic report with pre-written verdicts (no API key needed)")
    parser.add_argument("--mechanic-top", type=int, default=15,
                        help="How many top listings to send to the mechanic agent (default: 15)")
    parser.add_argument("--llm-provider", choices=["openrouter", "ollama", "groq"],
                        default="openrouter",
                        help="LLM provider (default: openrouter). "
                             "openrouter=best quality via OPENROUTER_API_KEY, "
                             "ollama=local free, groq=cloud free tier")
    parser.add_argument("--llm-model", type=str, default="",
                        help="Model override. Default per provider: "
                             "openrouter→anthropic/claude-opus-4-6, "
                             "ollama→mistral, groq→llama-3.3-70b-versatile")
    args = parser.parse_args()

    console = Console()
    console.print(f"\n[bold cyan]╔══════════════════════════════════════════╗[/bold cyan]")
    console.print(f"[bold cyan]║  LeBonCoin Car Dealer — IDF ROI Scanner  ║[/bold cyan]")
    console.print(f"[bold cyan]╚══════════════════════════════════════════╝[/bold cyan]")
    console.print(f"\n[bold]Config:[/bold] price €{args.min_price}–€{args.max_price} · "
                  f"year ≥{args.min_year} · mileage ≤{args.max_mileage:,} km · "
                  f"{args.max_pages} pages\n")

    if args.demo:
        console.print("[yellow bold]DEMO MODE[/yellow bold] — using mock data (no network)\n")
        listings = generate_mock_listings(80)
        # Apply same filters as live mode
        listings = [
            c for c in listings
            if args.min_price <= c.price <= args.max_price
            and (c.year is None or c.year >= args.min_year)
            and (c.mileage is None or c.mileage <= args.max_mileage)
        ]
    else:
        scraper = LeboncoinScraper(
            max_price=args.max_price,
            min_price=args.min_price,
            max_pages=args.max_pages,
            min_year=args.min_year,
            max_mileage=args.max_mileage,
        )
        listings = scraper.scrape()

    console.print(f"\n[green]Fetched {len(listings)} valid listings.[/green]")

    if not listings:
        console.print("[red]No listings to score. Try --demo to verify the pipeline, or check your network.[/red]")
        sys.exit(1)

    scorer = ROIScorer()
    console.print("[bold]Scoring ROI potential...[/bold]")
    scored = [scorer.score(car) for car in listings]

    # ── Engine blacklist ──────────────────────────────────────
    scored = apply_blacklist(scored)
    n_blacklisted = sum(1 for c in scored if c.blacklisted)
    if n_blacklisted:
        console.print(
            f"[red bold]⛔ {n_blacklisted} listing(s) flagged by engine blacklist "
            f"(score penalised -60)[/red bold]"
        )

    if args.min_score > 0:
        scored = [c for c in scored if c.roi_score >= args.min_score]
        console.print(f"[dim]After score filter (≥{args.min_score}): {len(scored)} listings[/dim]")

    render_results(scored, console, top_n=args.top)

    # ── Mechanic agent ────────────────────────────────────────
    if args.mechanic or args.mechanic_mock:
        top_for_review = sorted(scored, key=lambda c: c.roi_score, reverse=True)[:args.mechanic_top]
        try:
            agent = MechanicAgent(console, provider=args.llm_provider, model=args.llm_model)
            if args.mechanic_mock:
                console.print("\n[bold cyan]Mechanic Agent[/bold cyan] — [yellow]EXAMPLE MODE[/yellow] (pre-written verdicts, no API call)")
                top_for_review = agent.review_mock(top_for_review)
            else:
                top_for_review = agent.review(top_for_review)
            render_mechanic_report(top_for_review, console)
        except RuntimeError as e:
            console.print(f"[red]{e}[/red]")

    if args.export:
        sorted_all = sorted(scored, key=lambda x: x.roi_score, reverse=True)
        export_json(sorted_all, args.export)
        console.print(f"\n[green]Exported {len(sorted_all)} results → {args.export}[/green]")

    # Summary stats
    if scored:
        top5 = sorted(scored, key=lambda x: x.roi_score, reverse=True)[:5]
        avg_score = sum(c.roi_score for c in scored) / len(scored)
        high_margin = [c for c in scored if c.estimated_profit >= 2000]
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Total scored listings : {len(scored)}")
        console.print(f"  Average ROI score     : {avg_score:.1f}")
        console.print(f"  High margin (≥€2k)    : {len(high_margin)} listings")
        console.print(f"  Best score            : {top5[0].roi_score} — {top5[0].title[:40]}\n")


if __name__ == "__main__":
    main()
