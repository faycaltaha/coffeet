#!/usr/bin/env python3
"""
LeBonCoin Stealth Car Scraper — __NEXT_DATA__ extraction
=========================================================
Uses nodriver (undetected Chrome) to browse leboncoin.fr/voitures
exactly like a human, then extracts the __NEXT_DATA__ JSON blob
that Next.js embeds in every page — giving perfectly structured
listing data without fragile CSS selectors.

Steps followed (per Gemini recommendation):
  1. Stealth browser via nodriver (no automation fingerprints)
  2. Human simulation: random 3-8s delays, natural scroll
  3. Sequential page loading (never concurrent)
  4. __NEXT_DATA__ JSON extraction instead of fragile HTML parsing

Usage:
    python3 stealth_scraper.py                    # scrape 3 pages, print results
    python3 stealth_scraper.py --pages 3          # explicit page count
    python3 stealth_scraper.py --out results.json # export to JSON
    python3 stealth_scraper.py --db cars.db       # save to SQLite (upsert)
    python3 stealth_scraper.py --headless false   # visible browser (debug)
"""

import argparse
import asyncio
import json
import logging
import random
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ─────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("stealth_scraper")

# ─────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────

CHROME_PATH = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

# LeBonCoin /voitures search, newest first, no extra filters
BASE_URL = "https://www.leboncoin.fr/recherche?category=2&sort=time&order=desc"

DEFAULT_DB = Path(__file__).parent / "cars.db"


# ─────────────────────────────────────────────────────────────
# Human-like helpers
# ─────────────────────────────────────────────────────────────

async def human_delay(min_s: float = 3.0, max_s: float = 8.0):
    """Random pause — mimics human reading/thinking time."""
    wait = random.uniform(min_s, max_s)
    log.info("  Waiting %.1fs (human delay)...", wait)
    await asyncio.sleep(wait)


async def human_scroll(tab):
    """Scroll the page in small natural increments."""
    for target in [200, 500, 900, 1400]:
        await tab.evaluate(
            f"window.scrollTo({{top: {target}, behavior: 'smooth'}})"
        )
        await asyncio.sleep(random.uniform(0.4, 1.0))


# ─────────────────────────────────────────────────────────────
# __NEXT_DATA__ extractor
# ─────────────────────────────────────────────────────────────

def extract_next_data(html: str) -> Optional[dict]:
    """
    Find <script id="__NEXT_DATA__" type="application/json">…</script>
    and return the parsed JSON dict.
    """
    m = re.search(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        html,
        re.DOTALL | re.IGNORECASE,
    )
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError as e:
        log.error("  __NEXT_DATA__ JSON parse error: %s", e)
        return None


def find_ads_in_next_data(data: dict) -> list[dict]:
    """
    Walk the __NEXT_DATA__ tree to find the ads array.
    Tries known paths first, falls back to recursive search.
    """
    candidate_paths = [
        ["props", "pageProps", "searchData", "ads"],
        ["props", "pageProps", "ads"],
        ["props", "pageProps", "initialData", "ads"],
        ["props", "pageProps", "data", "ads"],
        ["props", "pageProps", "searchResults", "ads"],
    ]
    for path in candidate_paths:
        node = data
        for key in path:
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                node = None
                break
        if isinstance(node, list) and node:
            log.info("  Ads found at path: %s", " → ".join(path))
            return node

    # Recursive fallback
    def _search(obj, depth=0):
        if depth > 8:
            return None
        if isinstance(obj, dict):
            if "ads" in obj and isinstance(obj["ads"], list) and obj["ads"]:
                return obj["ads"]
            for v in obj.values():
                r = _search(v, depth + 1)
                if r:
                    return r
        elif isinstance(obj, list):
            for item in obj:
                r = _search(item, depth + 1)
                if r:
                    return r
        return None

    result = _search(data)
    if result:
        log.info("  Ads found via recursive search")
    return result or []


# ─────────────────────────────────────────────────────────────
# Ad field parser
# ─────────────────────────────────────────────────────────────

def _attr(attributes: list, key: str) -> str:
    for a in attributes:
        if a.get("key") == key:
            v = a.get("value_label") or a.get("values_label") or a.get("value", "")
            if isinstance(v, list):
                return str(v[0]) if v else ""
            return str(v) if v else ""
    return ""


def parse_ad(ad: dict, scraped_at: str) -> dict:
    attrs = ad.get("attributes", [])
    list_id = str(ad.get("list_id", ad.get("id", "")))

    price_raw = ad.get("price", [])
    price = None
    if isinstance(price_raw, list) and price_raw:
        try:
            price = int(price_raw[0])
        except (ValueError, TypeError):
            pass
    elif isinstance(price_raw, (int, float)):
        price = int(price_raw)

    year_str = _attr(attrs, "regdate")
    year = None
    if year_str:
        try:
            year = int(str(year_str)[:4])
        except (ValueError, TypeError):
            pass

    mileage_str = _attr(attrs, "mileage")
    mileage = None
    if mileage_str:
        try:
            mileage = int(str(mileage_str).replace(" ", "").replace(" ", "").replace("km", ""))
        except (ValueError, TypeError):
            pass

    loc = ad.get("location", {})
    imgs = ad.get("images", {})
    owner = ad.get("owner", {})

    return {
        "ad_id": list_id,
        "url": f"https://www.leboncoin.fr/voitures/{list_id}.htm",
        "title": ad.get("subject", ""),
        "description": (ad.get("body", "") or "")[:500],
        "price": price,
        "brand": _attr(attrs, "brand").lower(),
        "model": _attr(attrs, "model").lower(),
        "version": _attr(attrs, "version"),
        "year": year,
        "mileage": mileage,
        "fuel": _attr(attrs, "fuel").lower(),
        "gearbox": _attr(attrs, "gearbox").lower(),
        "doors": _attr(attrs, "doors"),
        "color": _attr(attrs, "color").lower(),
        "car_type": _attr(attrs, "car_type").lower(),
        "power_din": _attr(attrs, "horse_power_din"),
        "euro_norm": _attr(attrs, "euro_norm"),
        "crit_air": _attr(attrs, "ecological_sticker"),
        "vehicle_condition": _attr(attrs, "vehicle_condition").lower(),
        "seller_type": owner.get("type", "").lower(),
        "seller_name": owner.get("name", ""),
        "location_city": loc.get("city", ""),
        "location_dept": loc.get("department_id", ""),
        "location_region": loc.get("region_name", ""),
        "location_lat": loc.get("lat"),
        "location_lng": loc.get("lng"),
        "nb_images": len(imgs.get("urls", [])),
        "published_at": ad.get("first_publication_date", ""),
        "scraped_at": scraped_at,
        "raw_json": json.dumps(ad, ensure_ascii=False, default=str),
    }


# ─────────────────────────────────────────────────────────────
# Core stealth scraping loop
# ─────────────────────────────────────────────────────────────

async def scrape_pages(pages: int = 3, headless: bool = True) -> list[dict]:
    import nodriver as uc

    log.info("Starting stealth Chromium (headless=%s, binary=%s)...", headless, CHROME_PATH)

    browser = await uc.start(
        browser_executable_path=CHROME_PATH,
        headless=headless,
        browser_args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--window-size=1366,768",
            "--lang=fr-FR,fr",
            "--ignore-certificate-errors",       # sandbox TLS inspection proxy
            "--ignore-ssl-errors",
        ],
    )

    all_ads: list[dict] = []
    scraped_at = datetime.now(timezone.utc).isoformat()

    try:
        for page_num in range(1, pages + 1):
            url = BASE_URL if page_num == 1 else f"{BASE_URL}&page={page_num}"
            log.info("─── Page %s/%s → %s", page_num, pages, url)

            # Sequential, never concurrent
            tab = await browser.get(url)

            # Let Next.js fully hydrate before we read anything
            await asyncio.sleep(random.uniform(4, 7))

            # Simulate human scrolling through the listing page
            await human_scroll(tab)

            # Grab full page HTML
            html = await tab.get_content()
            log.info("  HTML size: %s chars", len(html) if html else 0)

            if not html:
                log.warning("  Empty page content — skipping")
                continue

            # ── Step 3: extract __NEXT_DATA__ ─────────────────
            next_data = extract_next_data(html)

            if not next_data:
                log.warning("  __NEXT_DATA__ not found — saving debug HTML")
                dbg = Path(__file__).parent / f"debug_page{page_num}.html"
                dbg.write_text(html, encoding="utf-8")
                log.warning("  Saved to %s", dbg)
                continue

            log.info("  __NEXT_DATA__ extracted (top-level keys: %s)",
                     list(next_data.keys())[:6])

            # ── Find ads array ─────────────────────────────────
            ads_raw = find_ads_in_next_data(next_data)
            log.info("  Raw ads in JSON: %s", len(ads_raw))

            for ad in ads_raw:
                try:
                    all_ads.append(parse_ad(ad, scraped_at))
                except Exception as e:
                    log.warning("  Parse error for ad %s: %s", ad.get("list_id", "?"), e)

            log.info("  Running total: %s ads", len(all_ads))

            # Human delay between pages (3-8 s) — never load pages concurrently
            if page_num < pages:
                await human_delay(3, 8)

    finally:
        try:
            browser.stop()
        except Exception:
            pass
        log.info("Browser stopped.")

    return all_ads


# ─────────────────────────────────────────────────────────────
# Output
# ─────────────────────────────────────────────────────────────

def print_table(ads: list[dict], top: int = 20):
    sep = "─" * 130
    print(f"\n{sep}")
    print(f"  {'#':>3}  {'Brand/Model':<22} {'Title':<36} {'Price':>7}  "
          f"{'Year':>4}  {'km':>8}  {'Fuel':<9}  {'City':<18}  Seller")
    print(sep)
    for i, ad in enumerate(ads[:top], 1):
        bm   = f"{ad['brand'].title()} {ad['model'].title()}"[:22]
        ttl  = ad["title"][:36]
        pr   = f"€{ad['price']:,}" if ad["price"] else "?"
        yr   = str(ad["year"]) if ad["year"] else "?"
        km   = f"{ad['mileage']:,}" if ad["mileage"] else "?"
        fuel = ad["fuel"][:9]
        city = ad["location_city"][:18]
        sel  = ad["seller_type"] or "?"
        print(f"  {i:>3}  {bm:<22} {ttl:<36} {pr:>7}  {yr:>4}  {km:>8}  {fuel:<9}  {city:<18}  {sel}")
    print(sep)
    print(f"  Total scraped: {len(ads)} ads\n")


def save_json(ads: list[dict], path: str):
    out = [{k: v for k, v in ad.items() if k != "raw_json"} for ad in ads]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    log.info("Exported %s ads → %s", len(out), path)


UPSERT_SQL = """
INSERT INTO cars (
    ad_id, url, title, description, price,
    brand, model, version, year, mileage,
    fuel, gearbox, doors, color, car_type,
    power_din, euro_norm, crit_air, vehicle_condition,
    seller_type, seller_name,
    location_city, location_dept_id, location_region_name,
    location_lat, location_lng,
    nb_images, published_at,
    first_seen_at, last_seen_at, raw_json
) VALUES (
    :ad_id, :url, :title, :description, :price,
    :brand, :model, :version, :year, :mileage,
    :fuel, :gearbox, :doors, :color, :car_type,
    :power_din, :euro_norm, :crit_air, :vehicle_condition,
    :seller_type, :seller_name,
    :location_city, :location_dept, :location_region,
    :location_lat, :location_lng,
    :nb_images, :published_at,
    :scraped_at, :scraped_at, :raw_json
)
ON CONFLICT(ad_id) DO UPDATE SET
    url=excluded.url, title=excluded.title, price=excluded.price,
    mileage=excluded.mileage, last_seen_at=excluded.last_seen_at,
    raw_json=excluded.raw_json
"""

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cars (
    ad_id TEXT PRIMARY KEY, url TEXT, title TEXT, description TEXT,
    price INTEGER, brand TEXT, model TEXT, version TEXT,
    year INTEGER, mileage INTEGER, fuel TEXT, gearbox TEXT,
    doors TEXT, color TEXT, car_type TEXT,
    power_din TEXT, euro_norm TEXT, crit_air TEXT, vehicle_condition TEXT,
    seller_type TEXT, seller_name TEXT,
    location_city TEXT, location_dept_id TEXT, location_region_name TEXT,
    location_lat REAL, location_lng REAL,
    nb_images INTEGER, published_at TEXT,
    first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL,
    raw_json TEXT
);
"""

def save_db(ads: list[dict], db_path: str):
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(CREATE_TABLE_SQL)
        conn.executemany(UPSERT_SQL, ads)
        conn.commit()
        log.info("Saved %s ads → %s", len(ads), db_path)
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Stealth LeBonCoin car scraper using nodriver + __NEXT_DATA__ extraction"
    )
    parser.add_argument("--pages", type=int, default=3,
                        help="Pages to scrape (35 ads/page, default: 3)")
    parser.add_argument("--out", type=str, default=None,
                        help="Export results to JSON file")
    parser.add_argument("--db", type=str, default=None,
                        help="Save to SQLite DB (upsert on ad_id)")
    parser.add_argument("--top", type=int, default=30,
                        help="Rows to show in table (default: 30)")
    parser.add_argument("--headless", type=str, default="true",
                        help="Headless browser — true/false (default: true)")
    args = parser.parse_args()

    headless = args.headless.lower() not in ("false", "0", "no")

    log.info("=== Stealth LeBonCoin scraper | pages=%s | headless=%s ===",
             args.pages, headless)

    ads = asyncio.run(scrape_pages(pages=args.pages, headless=headless))

    if not ads:
        log.error("No ads collected. Check debug_page*.html if saved.")
        sys.exit(1)

    print_table(ads, top=args.top)

    if args.out:
        save_json(ads, args.out)

    if args.db:
        save_db(ads, args.db)

    brands: dict[str, int] = {}
    for ad in ads:
        b = ad["brand"] or "unknown"
        brands[b] = brands.get(b, 0) + 1
    top_brands = sorted(brands.items(), key=lambda x: -x[1])[:8]
    print(f"Top brands: {', '.join(f'{b}({n})' for b, n in top_brands)}")

    prices = [ad["price"] for ad in ads if ad["price"]]
    if prices:
        print(f"Price range: €{min(prices):,} – €{max(prices):,}  |  avg €{sum(prices)//len(prices):,}")

    fuels: dict[str, int] = {}
    for ad in ads:
        f = ad["fuel"] or "unknown"
        fuels[f] = fuels.get(f, 0) + 1
    print(f"Fuels: {dict(sorted(fuels.items(), key=lambda x: -x[1]))}")


if __name__ == "__main__":
    main()
