"""
Stage 1 – Data Extraction.

Queries the latest ScanRun from the database and returns the single most
interesting car as a CarOfTheDay payload ready for the rest of the pipeline.

Two selection modes:
  DIAMOND – highest overall ROI score (a genuine great deal, Marcel praises it)
  ROAST   – biggest (price_score − reliability_score) gap, i.e. the most
             overpriced and unreliable car in the scan.  Marcel tears it apart
             and points to a better alternative ("The Alternative" segment).

The Hater Filter selects ROAST when the gap is ≥ _ROAST_GAP_THRESHOLD because
controversy drives engagement — people who own that car flood the comments.
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

_SCORE_CEILING = 150.0
# Minimum price_score − reliability_score gap to trigger ROAST mode.
_ROAST_GAP_THRESHOLD = 30.0


@dataclass(frozen=True)
class CarOfTheDay:
    make: str
    model: str
    year: int
    mileage_km: int
    price_eur: int
    reliability_score: float    # 0-100, based on brand/engine quality
    price_score: float           # 0-100, based on margin vs estimated resale
    overall_score: float         # 0-100, normalized roi_score
    image_url: str
    ad_url: str
    title: str
    fuel: str
    estimated_profit: int
    # "DIAMOND" (great deal Marcel recommends) or "ROAST" (overpriced trap).
    mode: str = "DIAMOND"
    # For ROAST: magnitude of (price_score − reliability_score).
    score_gap: float = 0.0
    # For ROAST: one-liner describing Marcel's recommended alternative.
    comparison_summary: str = ""


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


def _hater_gap(listing: dict) -> float:
    """price_score − reliability_score: positive = overpriced vs unreliable."""
    return _price_score(listing) - _reliability_score(listing)


def _hater_filter(listings: list[dict]) -> tuple[Optional[dict], float, str]:
    """
    Hater Filter: find the car with the largest (price_score − reliability_score)
    gap — the most overpriced and unreliable combination in today's scan.

    Returns (worst_listing, gap, comparison_summary).
    comparison_summary is a one-liner about the best alternative for
    Marcel's "The Alternative" script segment.
    Returns (None, 0.0, "") when no valid candidates exist.
    """
    candidates = [c for c in listings if not c.get("blacklisted") and c.get("price", 0) > 0]
    if not candidates:
        return None, 0.0, ""

    worst = max(candidates, key=_hater_gap)
    gap = _hater_gap(worst)

    best_alt = next(
        (c for c in listings if not c.get("blacklisted") and c.get("ad_id") != worst.get("ad_id")),
        None,
    )
    comparison_summary = ""
    if best_alt:
        make = best_alt.get("brand", "").title()
        model = best_alt.get("model", "").title()
        year = best_alt.get("year", "")
        price = best_alt.get("price", 0)
        score = _normalize(best_alt.get("roi_score", 0))
        comparison_summary = (
            f"{year} {make} {model} – score Autoradar {score:.0f}/100 – {price:,} €"
        ).replace(",", " ")

    return worst, gap, comparison_summary


def _build_car(
    listing: dict,
    mode: str,
    score_gap: float = 0.0,
    comparison_summary: str = "",
) -> CarOfTheDay:
    image_url = listing["images"][0] if listing.get("images") else ""
    return CarOfTheDay(
        make=listing.get("brand", "").title(),
        model=listing.get("model", "").title(),
        year=listing.get("year") or 0,
        mileage_km=listing.get("mileage") or 0,
        price_eur=listing.get("price") or 0,
        reliability_score=_reliability_score(listing),
        price_score=_price_score(listing),
        overall_score=_normalize(listing.get("roi_score", 0)),
        image_url=image_url,
        ad_url=listing.get("url", ""),
        title=listing.get("title", ""),
        fuel=listing.get("fuel", ""),
        estimated_profit=listing.get("estimated_profit", 0),
        mode=mode,
        score_gap=score_gap,
        comparison_summary=comparison_summary,
    )


async def get_car_of_the_day(db: AsyncSession) -> Optional[CarOfTheDay]:
    """
    Return today's featured car using the best available selection strategy:

    • ROAST  – Hater Filter finds a car with gap ≥ _ROAST_GAP_THRESHOLD
               (most overpriced + unreliable car in today's scan).
    • DIAMOND – otherwise, pick the highest-scoring deal in the scan.

    Returns None if no scan data is available yet.
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

    # ── Hater Filter ──────────────────────────────────────────────────────────
    roast_listing, gap, comparison_summary = _hater_filter(listings)
    if roast_listing is not None and gap >= _ROAST_GAP_THRESHOLD:
        car = _build_car(roast_listing, "ROAST", score_gap=gap, comparison_summary=comparison_summary)
        logger.info(
            "[car_selector] ROAST: %s %s %d – gap %.1f (price − reliability).",
            car.make, car.model, car.year, gap,
        )
        return car

    # ── DIAMOND ───────────────────────────────────────────────────────────────
    candidates = [c for c in listings if not c.get("blacklisted")] or listings
    car = _build_car(candidates[0], "DIAMOND")
    logger.info(
        "[car_selector] DIAMOND: %s %s %d – overall score %.1f.",
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
        "mode": car.mode,
        "score_gap": car.score_gap,
        "comparison_summary": car.comparison_summary,
    }
