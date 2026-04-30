#!/usr/bin/env python3
"""
LeBonCoin Daily Car Scraper — database builder
================================================
Scrapes the first 3 pages of /voitures (all France, zero filters) every day
and persists every available field to a local SQLite database.

Usage:
    python3 daily_scraper.py                          # scrape + save
    python3 daily_scraper.py --pages 5                # more pages
    python3 daily_scraper.py --db /path/to/cars.db    # custom DB path
    python3 daily_scraper.py --dry-run                # scrape but do not write

Cron example (run every day at 07:00):
    0 7 * * * cd /home/user/coffeet/car_database && python3 daily_scraper.py >> scraper.log 2>&1
"""

import argparse
import json
import logging
import os
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

# ─────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("lbc_scraper")

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────

LEBONCOIN_API = "https://api.leboncoin.fr/finder/classified/search"
CATEGORY_CARS = "2"
ADS_PER_PAGE = 35

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Content-Type": "application/json",
    "Origin": "https://www.leboncoin.fr",
    "Referer": "https://www.leboncoin.fr/",
    "api_key": "ba0c2dad52b3565c9a1be3a1d3b5cc2e",
}

DEFAULT_DB = Path(__file__).parent / "cars.db"

# ─────────────────────────────────────────────────────────────
# Data model — every field the API can return for a car ad
# ─────────────────────────────────────────────────────────────

@dataclass
class CarAd:
    # ── Core identifiers ─────────────────────────────────────
    ad_id: str                          # list_id from API
    url: str

    # ── Ad text ──────────────────────────────────────────────
    title: str = ""
    description: str = ""

    # ── Price ────────────────────────────────────────────────
    price: Optional[int] = None
    price_cents: Optional[int] = None  # raw price if given in cents

    # ── Car attributes (from attributes[] array) ─────────────
    brand: str = ""
    model: str = ""
    version: str = ""
    year: Optional[int] = None          # regdate
    mileage: Optional[int] = None
    fuel: str = ""
    gearbox: str = ""
    doors: Optional[int] = None
    seats: Optional[int] = None
    color: str = ""
    vehicle_damage: str = ""            # damaged / not_damaged
    vehicle_condition: str = ""         # new / used / etc.
    first_hand: Optional[bool] = None   # 1ère main
    power_din: Optional[int] = None     # puissance DIN (ch)
    power_kw: Optional[int] = None
    engine_displacement: Optional[int] = None  # cylindrée cm³
    euro_norm: str = ""                 # norme euro (Euro 5, Euro 6…)
    crit_air: str = ""                  # vignette Crit'Air
    car_type: str = ""                  # berline, SUV, break, etc.
    nb_doors_label: str = ""

    # ── Seller ───────────────────────────────────────────────
    seller_type: str = ""               # "private" | "pro"
    seller_id: Optional[int] = None
    seller_name: str = ""
    seller_store_id: Optional[int] = None

    # ── Location ─────────────────────────────────────────────
    location_city: str = ""
    location_zipcode: str = ""
    location_dept_id: str = ""
    location_dept_name: str = ""
    location_region_id: str = ""
    location_region_name: str = ""
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None

    # ── Media ────────────────────────────────────────────────
    nb_images: int = 0
    images_thumb: str = ""              # JSON list of thumbnail URLs
    images_large: str = ""              # JSON list of large URLs

    # ── Timestamps ───────────────────────────────────────────
    published_at: str = ""
    expires_at: str = ""
    first_seen_at: str = ""            # set once, never overwritten
    last_seen_at: str = ""             # updated every run

    # ── Raw payload ──────────────────────────────────────────
    raw_json: str = ""                  # full API ad object — lose nothing


# ─────────────────────────────────────────────────────────────
# Parser: raw API ad dict → CarAd
# ─────────────────────────────────────────────────────────────

def _attr(attributes: list[dict], key: str) -> str:
    """Extract the first value for an attribute key."""
    for a in attributes:
        if a.get("key") == key:
            v = a.get("value_label") or a.get("values_label") or a.get("value", "")
            if isinstance(v, list):
                return str(v[0]) if v else ""
            return str(v) if v else ""
    return ""


def _attr_int(attributes: list[dict], key: str) -> Optional[int]:
    raw = _attr(attributes, key)
    if not raw:
        return None
    try:
        return int(str(raw).replace(" ", "").replace(" ", "").replace(",", ""))
    except (ValueError, TypeError):
        return None


def parse_ad(ad: dict, now_iso: str) -> CarAd:
    attrs = ad.get("attributes", [])
    list_id = str(ad.get("list_id", ""))

    # Price
    price_raw = ad.get("price", [])
    price = None
    if isinstance(price_raw, list) and price_raw:
        try:
            price = int(price_raw[0])
        except (ValueError, TypeError):
            pass
    elif isinstance(price_raw, (int, float)):
        price = int(price_raw)

    # Location
    loc = ad.get("location", {})

    # Images
    imgs = ad.get("images", {})
    thumbs = imgs.get("urls", [])
    larges = imgs.get("urls_large", [])

    # Seller
    owner = ad.get("owner", {})

    # Regdate / year — may be full date string or just year
    regdate_raw = _attr(attrs, "regdate")
    year = None
    if regdate_raw:
        try:
            year = int(str(regdate_raw)[:4])
        except (ValueError, TypeError):
            pass

    # Mileage
    mileage_raw = _attr(attrs, "mileage")
    mileage = None
    if mileage_raw:
        try:
            mileage = int(str(mileage_raw).replace(" ", "").replace(" ", "").replace("km", ""))
        except (ValueError, TypeError):
            pass

    # first_hand
    first_hand_raw = _attr(attrs, "vehicle_vsp")  # sometimes key varies
    if not first_hand_raw:
        first_hand_raw = _attr(attrs, "first_hand")
    first_hand: Optional[bool] = None
    if first_hand_raw in ("1", "true", "oui", "Yes"):
        first_hand = True
    elif first_hand_raw in ("0", "false", "non", "No"):
        first_hand = False

    return CarAd(
        ad_id=list_id,
        url=f"https://www.leboncoin.fr/voitures/{list_id}.htm",
        title=ad.get("subject", ""),
        description=ad.get("body", ""),
        price=price,
        brand=_attr(attrs, "brand").lower(),
        model=_attr(attrs, "model").lower(),
        version=_attr(attrs, "version"),
        year=year,
        mileage=mileage,
        fuel=_attr(attrs, "fuel").lower(),
        gearbox=_attr(attrs, "gearbox").lower(),
        doors=_attr_int(attrs, "doors"),
        seats=_attr_int(attrs, "seats"),
        color=_attr(attrs, "color").lower(),
        vehicle_damage=_attr(attrs, "vehicle_damage").lower(),
        vehicle_condition=_attr(attrs, "vehicle_condition").lower(),
        first_hand=first_hand,
        power_din=_attr_int(attrs, "horse_power_din"),
        power_kw=_attr_int(attrs, "power"),
        engine_displacement=_attr_int(attrs, "engine_displacement"),
        euro_norm=_attr(attrs, "euro_norm"),
        crit_air=_attr(attrs, "ecological_sticker"),
        car_type=_attr(attrs, "car_type").lower(),
        nb_doors_label=_attr(attrs, "nb_doors"),
        seller_type=owner.get("type", "").lower(),
        seller_id=owner.get("user_id") or None,
        seller_name=owner.get("name", ""),
        seller_store_id=owner.get("store_id") or None,
        location_city=loc.get("city", ""),
        location_zipcode=loc.get("zipcode", ""),
        location_dept_id=loc.get("department_id", ""),
        location_dept_name=loc.get("department_name", ""),
        location_region_id=loc.get("region_id", ""),
        location_region_name=loc.get("region_name", ""),
        location_lat=loc.get("lat"),
        location_lng=loc.get("lng"),
        nb_images=len(thumbs),
        images_thumb=json.dumps(thumbs, ensure_ascii=False),
        images_large=json.dumps(larges, ensure_ascii=False),
        published_at=ad.get("first_publication_date", ""),
        expires_at=ad.get("expiration_date", ""),
        first_seen_at=now_iso,
        last_seen_at=now_iso,
        raw_json=json.dumps(ad, ensure_ascii=False, default=str),
    )


# ─────────────────────────────────────────────────────────────
# Scraper — no filters, sorts newest-first
# ─────────────────────────────────────────────────────────────

class Scraper:
    def __init__(self, pages: int = 3, proxy: Optional[str] = None):
        self.pages = pages
        # LeBonCoin blocks datacenter IPs (WAF: host_not_allowed).
        # Pass a residential proxy URL via --proxy or HTTPS_PROXY env var
        # when running on a VPS/cloud server.
        proxy_url = proxy or os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        self.client = httpx.Client(
            headers=HEADERS,
            timeout=25,
            follow_redirects=True,
            proxy=proxy_url,
        )

    def _payload(self, offset: int) -> dict:
        return {
            "filters": {
                "category": {"id": CATEGORY_CARS},
                "keywords": {},
                "ranges": {},
                "enums": {},
            },
            "limit": ADS_PER_PAGE,
            "limit_alu": 3,
            "offset": offset,
            "sort_by": "time",
            "sort_order": "desc",
        }

    def _fetch_page(self, offset: int) -> list[dict]:
        payload = self._payload(offset)
        for attempt in range(3):
            try:
                resp = self.client.post(LEBONCOIN_API, json=payload)
                if resp.status_code == 429:
                    wait = 15 * (attempt + 1)
                    log.warning("Rate limited — waiting %ss", wait)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json().get("ads", [])
            except httpx.HTTPStatusError as e:
                log.error("HTTP %s on offset=%s (attempt %s)", e.response.status_code, offset, attempt + 1)
                if attempt == 2:
                    return []
                time.sleep(3)
            except Exception as e:
                log.error("Network error on offset=%s: %s", offset, e)
                if attempt == 2:
                    return []
                time.sleep(3)
        return []

    def scrape(self) -> list[dict]:
        raw_ads: list[dict] = []
        for page in range(self.pages):
            offset = page * ADS_PER_PAGE
            log.info("Fetching page %s/%s (offset=%s)", page + 1, self.pages, offset)
            ads = self._fetch_page(offset)
            if not ads:
                log.warning("Empty page at offset=%s — stopping early", offset)
                break
            raw_ads.extend(ads)
            log.info("  → %s ads (total so far: %s)", len(ads), len(raw_ads))
            if page < self.pages - 1:
                time.sleep(2)
        return raw_ads


# ─────────────────────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS cars (
    ad_id                TEXT PRIMARY KEY,
    url                  TEXT,
    title                TEXT,
    description          TEXT,
    price                INTEGER,
    brand                TEXT,
    model                TEXT,
    version              TEXT,
    year                 INTEGER,
    mileage              INTEGER,
    fuel                 TEXT,
    gearbox              TEXT,
    doors                INTEGER,
    seats                INTEGER,
    color                TEXT,
    vehicle_damage       TEXT,
    vehicle_condition    TEXT,
    first_hand           INTEGER,
    power_din            INTEGER,
    power_kw             INTEGER,
    engine_displacement  INTEGER,
    euro_norm            TEXT,
    crit_air             TEXT,
    car_type             TEXT,
    nb_doors_label       TEXT,
    seller_type          TEXT,
    seller_id            INTEGER,
    seller_name          TEXT,
    seller_store_id      INTEGER,
    location_city        TEXT,
    location_zipcode     TEXT,
    location_dept_id     TEXT,
    location_dept_name   TEXT,
    location_region_id   TEXT,
    location_region_name TEXT,
    location_lat         REAL,
    location_lng         REAL,
    nb_images            INTEGER,
    images_thumb         TEXT,
    images_large         TEXT,
    published_at         TEXT,
    expires_at           TEXT,
    first_seen_at        TEXT NOT NULL,
    last_seen_at         TEXT NOT NULL,
    raw_json             TEXT
);

CREATE TABLE IF NOT EXISTS scrape_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    pages_requested INTEGER,
    ads_fetched     INTEGER,
    ads_new         INTEGER,
    ads_updated     INTEGER,
    status          TEXT,
    error_message   TEXT
);

CREATE INDEX IF NOT EXISTS idx_cars_brand    ON cars (brand);
CREATE INDEX IF NOT EXISTS idx_cars_model    ON cars (model);
CREATE INDEX IF NOT EXISTS idx_cars_year     ON cars (year);
CREATE INDEX IF NOT EXISTS idx_cars_price    ON cars (price);
CREATE INDEX IF NOT EXISTS idx_cars_fuel     ON cars (fuel);
CREATE INDEX IF NOT EXISTS idx_cars_dept     ON cars (location_dept_id);
CREATE INDEX IF NOT EXISTS idx_cars_seen     ON cars (last_seen_at);
"""


@contextmanager
def get_db(path: Path):
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(path: Path):
    with get_db(path) as conn:
        conn.executescript(SCHEMA)
    log.info("Database ready: %s", path)


def upsert_ads(conn: sqlite3.Connection, ads: list[CarAd]) -> tuple[int, int]:
    """Insert new ads; update last_seen_at (and raw_json) for existing ones.
    Returns (new_count, updated_count).
    """
    new_count = 0
    upd_count = 0

    for ad in ads:
        existing = conn.execute(
            "SELECT ad_id, first_seen_at FROM cars WHERE ad_id = ?", (ad.ad_id,)
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE cars SET
                    url=?, title=?, description=?, price=?,
                    brand=?, model=?, version=?, year=?, mileage=?,
                    fuel=?, gearbox=?, doors=?, seats=?, color=?,
                    vehicle_damage=?, vehicle_condition=?, first_hand=?,
                    power_din=?, power_kw=?, engine_displacement=?,
                    euro_norm=?, crit_air=?, car_type=?, nb_doors_label=?,
                    seller_type=?, seller_id=?, seller_name=?, seller_store_id=?,
                    location_city=?, location_zipcode=?, location_dept_id=?,
                    location_dept_name=?, location_region_id=?, location_region_name=?,
                    location_lat=?, location_lng=?,
                    nb_images=?, images_thumb=?, images_large=?,
                    published_at=?, expires_at=?,
                    last_seen_at=?, raw_json=?
                WHERE ad_id = ?""",
                (
                    ad.url, ad.title, ad.description, ad.price,
                    ad.brand, ad.model, ad.version, ad.year, ad.mileage,
                    ad.fuel, ad.gearbox, ad.doors, ad.seats, ad.color,
                    ad.vehicle_damage, ad.vehicle_condition,
                    None if ad.first_hand is None else int(ad.first_hand),
                    ad.power_din, ad.power_kw, ad.engine_displacement,
                    ad.euro_norm, ad.crit_air, ad.car_type, ad.nb_doors_label,
                    ad.seller_type, ad.seller_id, ad.seller_name, ad.seller_store_id,
                    ad.location_city, ad.location_zipcode, ad.location_dept_id,
                    ad.location_dept_name, ad.location_region_id, ad.location_region_name,
                    ad.location_lat, ad.location_lng,
                    ad.nb_images, ad.images_thumb, ad.images_large,
                    ad.published_at, ad.expires_at,
                    ad.last_seen_at, ad.raw_json,
                    ad.ad_id,
                ),
            )
            upd_count += 1
        else:
            conn.execute(
                """INSERT INTO cars VALUES (
                    :ad_id, :url, :title, :description, :price,
                    :brand, :model, :version, :year, :mileage,
                    :fuel, :gearbox, :doors, :seats, :color,
                    :vehicle_damage, :vehicle_condition, :first_hand,
                    :power_din, :power_kw, :engine_displacement,
                    :euro_norm, :crit_air, :car_type, :nb_doors_label,
                    :seller_type, :seller_id, :seller_name, :seller_store_id,
                    :location_city, :location_zipcode, :location_dept_id,
                    :location_dept_name, :location_region_id, :location_region_name,
                    :location_lat, :location_lng,
                    :nb_images, :images_thumb, :images_large,
                    :published_at, :expires_at,
                    :first_seen_at, :last_seen_at, :raw_json
                )""",
                {
                    **{k: v for k, v in asdict(ad).items() if k != "first_hand"},
                    "first_hand": None if ad.first_hand is None else int(ad.first_hand),
                },
            )
            new_count += 1

    return new_count, upd_count


def log_run(
    conn: sqlite3.Connection,
    started_at: str,
    finished_at: str,
    pages: int,
    fetched: int,
    new: int,
    updated: int,
    status: str,
    error: str = "",
):
    conn.execute(
        """INSERT INTO scrape_runs
           (started_at, finished_at, pages_requested, ads_fetched, ads_new, ads_updated, status, error_message)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (started_at, finished_at, pages, fetched, new, updated, status, error),
    )


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Scrape LeBonCoin /voitures (no filter, all France) and save to SQLite"
    )
    parser.add_argument("--pages", type=int, default=3,
                        help="Number of pages to scrape (35 ads/page, default: 3)")
    parser.add_argument("--db", type=str, default=str(DEFAULT_DB),
                        help=f"SQLite database path (default: {DEFAULT_DB})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Scrape but do not write to database")
    parser.add_argument("--proxy", type=str, default=None,
                        help="Residential proxy URL, e.g. http://user:pass@host:port  "
                             "(also reads HTTPS_PROXY env var). Required on cloud/VPS servers "
                             "since LeBonCoin blocks datacenter IPs.")
    args = parser.parse_args()

    db_path = Path(args.db)
    started_at = datetime.now(timezone.utc).isoformat()
    now_iso = started_at

    proxy = args.proxy or os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

    log.info("=== LeBonCoin daily car scraper — %s ===", started_at[:10])
    log.info("Pages: %s  |  DB: %s  |  dry-run: %s  |  proxy: %s",
             args.pages, db_path, args.dry_run, proxy or "none")

    if not args.dry_run:
        init_db(db_path)

    # ── Scrape ─────────────────────────────────────────────
    scraper = Scraper(pages=args.pages, proxy=args.proxy)
    status = "ok"
    error_msg = ""
    raw_ads: list[dict] = []
    parsed_ads: list[CarAd] = []

    try:
        raw_ads = scraper.scrape()
        log.info("Total raw ads fetched: %s", len(raw_ads))

        for raw in raw_ads:
            try:
                parsed_ads.append(parse_ad(raw, now_iso))
            except Exception as e:
                log.warning("Failed to parse ad %s: %s", raw.get("list_id"), e)

        log.info("Successfully parsed: %s ads", len(parsed_ads))
    except Exception as e:
        status = "error"
        error_msg = str(e)
        log.error("Scrape failed: %s", e)

    # ── Persist ────────────────────────────────────────────
    new_count = updated_count = 0
    finished_at = datetime.now(timezone.utc).isoformat()

    if not args.dry_run and parsed_ads:
        try:
            with get_db(db_path) as conn:
                new_count, updated_count = upsert_ads(conn, parsed_ads)
                log_run(
                    conn, started_at, finished_at,
                    args.pages, len(raw_ads), new_count, updated_count,
                    status, error_msg,
                )
            log.info("DB write done — new: %s  updated: %s", new_count, updated_count)
        except Exception as e:
            log.error("DB write failed: %s", e)
            status = "error"
    elif args.dry_run:
        log.info("DRY-RUN — would have written %s ads (skipping DB)", len(parsed_ads))
        if parsed_ads:
            sample = parsed_ads[0]
            log.info("Sample ad: [%s] %s — €%s — %s %s %s km",
                     sample.ad_id, sample.title, sample.price,
                     sample.year, sample.fuel, sample.mileage)

    log.info("=== Run finished | status: %s | new: %s | updated: %s ===",
             status, new_count, updated_count)


if __name__ == "__main__":
    main()
