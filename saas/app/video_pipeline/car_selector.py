"""
Stage 1 – Data Extraction.

Queries the latest ScanRun from the database and returns the single most
interesting car as a CarOfTheDay payload ready for the rest of the pipeline.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ScanRun

logger = logging.getLogger(__name__)

# Maximum normalized score ceiling used to convert roi_score → 0-100 scale.
_SCORE_CEILING = 150.0


@dataclass(frozen=True)
class CarOfTheDay:
    make: str
    model: str
    year: int
    mileage_km: int
    price_eur: int
    reliability_score: float   # 0-100, based on brand/engine quality
    price_score: float          # 0-100, based on margin vs estimated resale
    overall_score: float        # 0-100, normalized roi_score
    image_url: str
    ad_url: str
    title: str
    fuel: str
    estimated_profit: int


def _normalize(value: float, ceiling: float = _SCORE_CEILING) -> float:
    """Clamp a raw score to the 0-100 range."""
    return round(min(100.0, max(0.0, (value / ceiling) * 100)), 1)


def _reliability_score(listing: dict) -> float:
    """
    Derive a 0-100 reliability score from brand and blacklist signals already
    embedded in the listing dict produced by the scraper.
    """
    from ..scraper import BRAND_SCORES

    brand = listing.get("brand", "").lower()
    brand_pts = BRAND_SCORES.get(brand, 5)
    # brand_pts range: 3 (lancia) → 20 (toyota).  Map to 0-100.
    base = round(min(100.0, (brand_pts / 20.0) * 100), 1)

    if listing.get("blacklisted"):
        base = max(0.0, base - 40.0)

    return base


def _price_score(listing: dict) -> float:
    """
    Derive a 0-100 price score from the estimated profit margin.
    A margin ≥ €3 000 scores 100, €0 scores 0.
    """
    profit = listing.get("estimated_profit", 0)
    if profit <= 0:
        return 0.0
    return round(min(100.0, (profit / 3_000.0) * 100), 1)


async def get_car_of_the_day(db: AsyncSession) -> Optional[CarOfTheDay]:
    """
    Return the highest-scoring non-blacklisted car from the latest scan run,
    mapped to a CarOfTheDay dataclass.  Returns None if no scan exists yet.
    """
    result = await db.execute(
        select(ScanRun).order_by(ScanRun.run_at.desc()).limit(1)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        logger.warning("[car_selector] No scan run found in DB.")
        return None

    listings: list[dict] = json.loads(scan.listings_json)
    if not listings:
        logger.warning("[car_selector] Latest scan run has zero listings.")
        return None

    # Prefer non-blacklisted; fall back to any car if everything is flagged.
    candidates = [c for c in listings if not c.get("blacklisted")] or listings
    best = candidates[0]  # already sorted by roi_score desc in the scraper

    image_url = ""
    if best.get("images"):
        image_url = best["images"][0]

    car = CarOfTheDay(
        make=best.get("brand", "").title(),
        model=best.get("model", "").title(),
        year=best.get("year") or 0,
        mileage_km=best.get("mileage") or 0,
        price_eur=best.get("price") or 0,
        reliability_score=_reliability_score(best),
        price_score=_price_score(best),
        overall_score=_normalize(best.get("roi_score", 0)),
        image_url=image_url,
        ad_url=best.get("url", ""),
        title=best.get("title", ""),
        fuel=best.get("fuel", ""),
        estimated_profit=best.get("estimated_profit", 0),
    )
    logger.info(
        "[car_selector] Car of the Day: %s %s %d – overall score %.1f",
        car.make, car.model, car.year, car.overall_score,
    )
    return car


def car_to_json_payload(car: CarOfTheDay) -> dict:
    """Serialise a CarOfTheDay to the JSON payload format used by the pipeline."""
    return {
        "make": car.make,
        "model": car.model,
        "year": car.year,
        "mileage_km": car.mileage_km,
        "price_eur": car.price_eur,
        "reliability_score": car.reliability_score,
        "price_score": car.price_score,
        "overall_score": car.overall_score,
        "image_url": car.image_url,
        "ad_url": car.ad_url,
        "fuel": car.fuel,
        "estimated_profit": car.estimated_profit,
    }
