"""
Core scraping + ROI scoring logic — adapted from car_dealer_scraper.py
for use as a library (no CLI, no Rich output).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import httpx

LEBONCOIN_API = "https://api.leboncoin.fr/finder/classified/search"
CATEGORY_CARS = "2"
IDF_REGION = "12"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Content-Type": "application/json",
    "Origin": "https://www.leboncoin.fr",
    "Referer": "https://www.leboncoin.fr/",
    "api_key": "ba0c2dad52b3565c9a1be3a1d3b5cc2e",
}

CURRENT_YEAR = datetime.now().year

HIGH_DEMAND_MODELS = {
    "duster": 30, "captur": 28, "peugeot 2008": 28, "clio": 25,
    "polo": 25, "golf": 30, "tiguan": 28, "3008": 28, "208": 25,
    "yaris": 28, "corolla": 25, "c3": 22, "sandero": 22,
    "bmw serie 3": 32, "bmw serie 1": 28, "serie 3": 32, "serie 1": 28,
    "audi a3": 30, "audi a4": 28, "mercedes classe a": 28, "classe a": 28,
    "mercedes classe c": 30, "classe c": 30,
    "berlingo": 28, "kangoo": 26, "partner": 26, "transit": 22,
    "honda civic": 28, "mazda 3": 26, "mazda cx-5": 28,
}

BRAND_SCORES = {
    "toyota": 20, "honda": 18, "mazda": 16,
    "volkswagen": 15, "audi": 15, "bmw": 14, "mercedes": 13,
    "renault": 10, "peugeot": 10, "citroen": 9, "dacia": 12,
    "ford": 10, "opel": 8, "seat": 10, "skoda": 12,
    "hyundai": 13, "kia": 13, "nissan": 10, "mitsubishi": 11,
    "fiat": 7, "alfa romeo": 6, "lancia": 3,
}

FUEL_SCORES = {
    "diesel": 8, "essence": 10, "hybride": 15, "electrique": 12, "gpl": 5, "": 5,
}

GEARBOX_SCORES = {"automatique": 10, "manuelle": 5, "": 5}

ENGINE_BLACKLIST: list[tuple[str, Optional[str], str]] = [
    ("puretech", None,        "1.2 PureTech: timing chain failure"),
    ("1.2 vti", "peugeot",    "1.2 VTi: camshaft follower wear"),
    ("1.2 vti", "citroen",    "1.2 VTi: camshaft follower wear"),
    ("1.2 tce 115", "renault", "1.2 TCe 115: timing chain + head gasket"),
    ("1.2 tce 120", "renault", "1.2 TCe 120: timing chain + head gasket"),
    ("1.2 tce 130", "renault", "1.2 TCe 130: timing chain + head gasket"),
    ("1.4 multiair", None,    "1.4 MultiAir: valve carbon build-up"),
    ("1.4 t-jet", "fiat",     "1.4 T-Jet: timing belt failure"),
    ("n47",   "bmw",          "BMW N47: rear timing chain — catastrophic failure"),
    ("116d",  "bmw",          "BMW N47 (116d): catastrophic failure risk"),
    ("118d",  "bmw",          "BMW N47 (118d): catastrophic failure risk"),
    ("120d",  "bmw",          "BMW N47 (120d): catastrophic failure risk"),
    ("318d",  "bmw",          "BMW N47 (318d): catastrophic failure risk"),
    ("320d",  "bmw",          "BMW N47 (320d): catastrophic failure risk"),
    ("1.0 ecoboost", "ford",  "1.0 EcoBoost: head gasket failure"),
    ("1.0 scti",     "ford",  "1.0 EcoBoost (SCTi): head gasket failure"),
    ("1.4 tb multiair", None, "1.4 TB MultiAir: valve actuator failures"),
    ("1.6 cdti", "opel",      "1.6 CDTI: timing chain tensioner failure"),
]


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
    roi_score: float = 0.0
    estimated_resale: int = 0
    estimated_profit: int = 0
    roi_reasons: list[str] = field(default_factory=list)
    blacklisted: bool = False
    blacklist_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "ad_id": self.ad_id,
            "title": self.title,
            "price": self.price,
            "year": self.year,
            "mileage": self.mileage,
            "fuel": self.fuel,
            "gearbox": self.gearbox,
            "brand": self.brand,
            "model": self.model,
            "location": self.location,
            "url": self.url,
            "images": self.images,
            "roi_score": self.roi_score,
            "estimated_resale": self.estimated_resale,
            "estimated_profit": self.estimated_profit,
            "roi_reasons": self.roi_reasons,
            "blacklisted": self.blacklisted,
            "blacklist_reason": self.blacklist_reason,
        }


def _estimate_resale(listing: CarListing) -> int:
    if not listing.year:
        return 0
    age = CURRENT_YEAR - listing.year
    base = 25_000
    if age <= 1:    factor = 0.80
    elif age <= 2:  factor = 0.72
    elif age <= 3:  factor = 0.65
    elif age <= 4:  factor = 0.58
    elif age <= 5:  factor = 0.52
    elif age <= 7:  factor = 0.42
    elif age <= 10: factor = 0.30
    elif age <= 13: factor = 0.20
    elif age <= 15: factor = 0.14
    else:           factor = 0.08

    value = base * factor

    if listing.mileage:
        km = listing.mileage
        if km < 50_000:    value *= 1.15
        elif km < 100_000: value *= 1.0
        elif km < 150_000: value *= 0.88
        elif km < 200_000: value *= 0.72
        else:              value *= 0.55

    brand_factor = {
        "toyota": 1.15, "honda": 1.10, "mazda": 1.08,
        "bmw": 1.12, "audi": 1.10, "mercedes": 1.10,
        "volkswagen": 1.05, "skoda": 1.05, "seat": 1.02,
        "renault": 0.95, "peugeot": 0.95, "citroen": 0.93,
        "dacia": 0.90, "fiat": 0.88, "opel": 0.90,
    }.get(listing.brand, 1.0)
    value *= brand_factor

    if "hybride" in listing.fuel:
        value *= 1.10
    elif "electrique" in listing.fuel:
        value *= 1.05

    return max(500, int(round(value / 100) * 100))


def score_listing(listing: CarListing) -> CarListing:
    score = 0.0
    reasons: list[str] = []

    brand_bonus = BRAND_SCORES.get(listing.brand, 5)
    score += brand_bonus
    if brand_bonus >= 15:
        reasons.append(f"Marque premium ({listing.brand.title()})")
    elif brand_bonus >= 12:
        reasons.append(f"Marque demandée ({listing.brand.title()})")

    model_bonus = 0
    for key, pts in HIGH_DEMAND_MODELS.items():
        if key in listing.title.lower() or key in listing.model.lower():
            model_bonus = max(model_bonus, pts)
    score += model_bonus
    if model_bonus >= 25:
        reasons.append("Modèle best-seller")
    elif model_bonus >= 15:
        reasons.append("Bonne demande marché")

    fuel_bonus = FUEL_SCORES.get(listing.fuel, 5)
    score += fuel_bonus
    if fuel_bonus >= 12:
        reasons.append(f"Carburant recherché ({listing.fuel})")

    gb_bonus = GEARBOX_SCORES.get(listing.gearbox, 5)
    score += gb_bonus
    if gb_bonus >= 10:
        reasons.append("Boîte automatique (+ d'acheteurs)")

    if listing.year:
        age = CURRENT_YEAR - listing.year
        if age <= 5:
            score += 25
            reasons.append(f"Véhicule récent ({listing.year}, {age} ans)")
        elif age <= 8:
            score += 18
            reasons.append(f"Véhicule moderne ({listing.year}, {age} ans)")
        elif age <= 12:
            score += 10
        elif age <= 15:
            score += 5
        else:
            score -= 5

    if listing.mileage:
        km = listing.mileage
        if km < 50_000:
            score += 25
            reasons.append(f"Faible kilométrage ({km:,} km)")
        elif km < 100_000:
            score += 18
            reasons.append(f"Kilométrage correct ({km:,} km)")
        elif km < 150_000:
            score += 8
        elif km < 200_000:
            score += 2
        else:
            score -= 10

        if listing.year:
            age = max(1, CURRENT_YEAR - listing.year)
            km_per_year = km / age
            if km_per_year < 10_000:
                score += 10
                reasons.append(f"Excellent ratio km/an ({km_per_year:,.0f} km/an)")
            elif km_per_year < 15_000:
                score += 5
            elif km_per_year > 25_000:
                score -= 8

    estimated_resale = _estimate_resale(listing)
    listing.estimated_resale = estimated_resale
    if estimated_resale > 0 and listing.price > 0:
        margin = estimated_resale - listing.price
        margin_pct = (margin / listing.price) * 100
        listing.estimated_profit = margin
        if margin_pct >= 60:
            score += 40
            reasons.append(f"Sous-coté ~{margin_pct:.0f}% (revente est. €{estimated_resale:,})")
        elif margin_pct >= 40:
            score += 28
            reasons.append(f"Bonne marge ~{margin_pct:.0f}% (est. €{estimated_resale:,})")
        elif margin_pct >= 25:
            score += 16
            reasons.append(f"Marge correcte ~{margin_pct:.0f}% (est. €{estimated_resale:,})")
        elif margin_pct >= 10:
            score += 8
        elif margin_pct < 0:
            score -= 15
            reasons.append("Surestimé vs marché")

    if listing.price <= 2000:
        score += 10
        reasons.append(f"Prix d'entrée très bas (€{listing.price:,})")
    elif listing.price <= 4000:
        score += 6

    listing.roi_score = round(score, 1)
    listing.roi_reasons = reasons
    return listing


def apply_blacklist(listings: list[CarListing]) -> None:
    for car in listings:
        title_lower = car.title.lower()
        for keyword, brand_filter, reason in ENGINE_BLACKLIST:
            if keyword in title_lower:
                if brand_filter is None or brand_filter == car.brand:
                    car.blacklisted = True
                    car.blacklist_reason = reason
                    car.roi_score -= 60
                    break


def _extract_attribute(attributes: list, key: str) -> str:
    for attr in attributes:
        if attr.get("key") == key:
            values = attr.get("value_label") or attr.get("values_label")
            if isinstance(values, list):
                return values[0] if values else ""
            return values or attr.get("value", "")
    return ""


def _parse_ad(ad: dict, max_mileage: int, min_year: int) -> Optional[CarListing]:
    try:
        attrs = ad.get("attributes", [])
        price_raw = ad.get("price", [None])
        price = price_raw[0] if isinstance(price_raw, list) and price_raw else price_raw
        if not price or not isinstance(price, (int, float)):
            return None
        price = int(price)

        year_str = _extract_attribute(attrs, "regdate")
        try:
            year = int(year_str) if year_str else None
        except ValueError:
            year = None

        mileage_str = _extract_attribute(attrs, "mileage")
        try:
            mileage = int(mileage_str.replace(" ", "").replace("km", "")) if mileage_str else None
        except (ValueError, AttributeError):
            mileage = None

        if mileage and mileage > max_mileage:
            return None
        if year and year < min_year:
            return None

        fuel = _extract_attribute(attrs, "fuel").lower()
        gearbox = _extract_attribute(attrs, "gearbox").lower()
        brand = _extract_attribute(attrs, "brand").lower()
        model_name = _extract_attribute(attrs, "model").lower()
        location_city = ad.get("location", {}).get("city", "")
        location_dept = ad.get("location", {}).get("department_id", "")
        location = f"{location_city} ({location_dept})" if location_city else location_dept

        images = ad.get("images", {}).get("urls_large", [])[:3]
        ad_id = str(ad.get("list_id", ""))

        return CarListing(
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
            url=f"https://www.leboncoin.fr/voitures/{ad_id}.htm",
            images=images,
        )
    except Exception:
        return None


def run_scan(
    max_price: int = 8000,
    min_price: int = 500,
    max_pages: int = 5,
    min_year: int = 2005,
    max_mileage: int = 250_000,
    top_n: int = 20,
) -> list[dict]:
    """Scrape leboncoin, score listings, return top_n as list of dicts."""
    client = httpx.Client(headers=HEADERS, timeout=20, follow_redirects=True)
    all_listings: list[CarListing] = []

    for page in range(max_pages):
        offset = page * 35
        payload = {
            "filters": {
                "category": {"id": CATEGORY_CARS},
                "location": {"regions": [IDF_REGION]},
                "keywords": {},
                "ranges": {
                    "price": {"min": min_price, "max": max_price},
                    "regdate": {"min": min_year},
                },
                "enums": {},
            },
            "limit": 35,
            "limit_alu": 3,
            "offset": offset,
            "sort_by": "price",
            "sort_order": "asc",
            "owner_type": "private",
        }
        try:
            resp = client.post(LEBONCOIN_API, json=payload)
            if resp.status_code == 429:
                time.sleep(10)
                resp = client.post(LEBONCOIN_API, json=payload)
            resp.raise_for_status()
            ads = resp.json().get("ads", [])
        except Exception:
            break

        for ad in ads:
            listing = _parse_ad(ad, max_mileage, min_year)
            if listing:
                all_listings.append(listing)

        if page < max_pages - 1:
            time.sleep(1.5)

    apply_blacklist(all_listings)
    for listing in all_listings:
        score_listing(listing)

    all_listings.sort(key=lambda x: x.roi_score, reverse=True)
    return [c.to_dict() for c in all_listings[:top_n]]
