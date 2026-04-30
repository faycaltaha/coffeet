"""Unit tests for Stage 1 – car_selector."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.video_pipeline.car_selector import (
    CarOfTheDay,
    _ROAST_GAP_THRESHOLD,
    _hater_filter,
    _normalize,
    _price_score,
    _reliability_score,
    car_to_json_payload,
    get_car_of_the_day,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

_LISTING_OK = {
    "brand": "toyota",
    "model": "yaris",
    "year": 2020,
    "mileage": 45_000,
    "price": 9_500,
    "fuel": "essence",
    "gearbox": "manuelle",
    "location": "Paris (75)",
    "url": "https://www.leboncoin.fr/voitures/123.htm",
    "images": ["https://example.com/car.jpg"],
    "roi_score": 95.0,
    "estimated_resale": 12_500,
    "estimated_profit": 3_000,
    "roi_reasons": ["Faible kilométrage", "Marque fiable"],
    "blacklisted": False,
    "blacklist_reason": "",
    "title": "Toyota Yaris 2020",
}

_LISTING_BLACKLISTED = dict(_LISTING_OK, blacklisted=True, roi_score=35.0)


# ── _normalize ────────────────────────────────────────────────────────────────

def test_normalize_zero():
    assert _normalize(0) == 0.0


def test_normalize_ceiling():
    assert _normalize(150) == 100.0


def test_normalize_over_ceiling():
    assert _normalize(999) == 100.0


def test_normalize_negative():
    assert _normalize(-50) == 0.0


def test_normalize_typical():
    result = _normalize(75.0, ceiling=150.0)
    assert result == 50.0


# ── _reliability_score ────────────────────────────────────────────────────────

def test_reliability_score_toyota():
    score = _reliability_score({"brand": "toyota", "blacklisted": False})
    assert score == 100.0


def test_reliability_score_unknown_brand():
    score = _reliability_score({"brand": "unknownbrand", "blacklisted": False})
    # brand_pts default = 5, so (5/20)*100 = 25.0
    assert score == 25.0


def test_reliability_score_blacklisted():
    score = _reliability_score({"brand": "toyota", "blacklisted": True})
    assert score == 60.0  # 100 - 40


def test_reliability_score_blacklisted_low_brand():
    score = _reliability_score({"brand": "lancia", "blacklisted": True})
    # lancia = 3 → (3/20)*100 = 15.0 - 40 → clamped to 0
    assert score == 0.0


# ── _price_score ──────────────────────────────────────────────────────────────

def test_price_score_zero_profit():
    assert _price_score({"estimated_profit": 0}) == 0.0


def test_price_score_negative_profit():
    assert _price_score({"estimated_profit": -500}) == 0.0


def test_price_score_max_profit():
    assert _price_score({"estimated_profit": 3_000}) == 100.0


def test_price_score_over_max():
    assert _price_score({"estimated_profit": 6_000}) == 100.0


def test_price_score_half():
    assert _price_score({"estimated_profit": 1_500}) == 50.0


# ── car_to_json_payload ────────────────────────────────────────────────────────

def test_car_to_json_payload_keys():
    car = CarOfTheDay(
        make="Toyota", model="Yaris", year=2020, mileage_km=45_000,
        price_eur=9_500, reliability_score=100.0, price_score=80.0,
        overall_score=63.3, image_url="https://example.com/car.jpg",
        ad_url="https://www.leboncoin.fr/voitures/123.htm",
        title="Toyota Yaris 2020", fuel="essence", estimated_profit=3_000,
    )
    payload = car_to_json_payload(car)
    expected_keys = {
        "make", "model", "year", "mileage_km", "price_eur",
        "reliability_score", "price_score", "overall_score",
        "image_url", "ad_url", "fuel", "estimated_profit",
        "mode", "score_gap", "comparison_summary",
    }
    assert set(payload.keys()) == expected_keys
    assert payload["make"] == "Toyota"
    assert payload["overall_score"] == 63.3
    assert payload["mode"] == "DIAMOND"
    assert payload["score_gap"] == 0.0
    assert payload["comparison_summary"] == ""


def test_car_to_json_payload_roast_fields():
    car = CarOfTheDay(
        make="Fiat", model="Stilo", year=2005, mileage_km=200_000,
        price_eur=6_000, reliability_score=15.0, price_score=80.0,
        overall_score=10.0, image_url="", ad_url="", title="Fiat Stilo",
        fuel="essence", estimated_profit=0,
        mode="ROAST", score_gap=65.0,
        comparison_summary="2019 Toyota Yaris – score Autoradar 88/100 – 9 500 €",
    )
    payload = car_to_json_payload(car)
    assert payload["mode"] == "ROAST"
    assert payload["score_gap"] == 65.0
    assert "Toyota" in payload["comparison_summary"]


# ── _hater_filter ─────────────────────────────────────────────────────────────

# A listing with very high price_score (big profit margin) but very low reliability.
_LISTING_OVERPRICED = {
    "ad_id": "overpriced-1",
    "brand": "fiat",          # reliability very low
    "model": "stilo",
    "year": 2005,
    "mileage": 200_000,
    "price": 6_000,
    "fuel": "essence",
    "images": [],
    "roi_score": 20.0,
    "estimated_profit": 2_800,   # price_score ≈ 93
    "blacklisted": False,
}

def test_hater_filter_finds_worst_gap():
    listings = [_LISTING_OK, _LISTING_OVERPRICED]
    worst, gap, _ = _hater_filter(listings)
    # _LISTING_OK:       price_score=100, reliability=100 → gap=0
    # _LISTING_OVERPRICED: price_score≈93, reliability≈15 → gap≈78
    assert worst["ad_id"] == "overpriced-1"
    assert gap > 50


def test_hater_filter_ignores_blacklisted():
    blacklisted_overpriced = dict(_LISTING_OVERPRICED, blacklisted=True, ad_id="bl-1")
    listings = [_LISTING_OK, blacklisted_overpriced]
    worst, gap, _ = _hater_filter(listings)
    # Only _LISTING_OK is valid; it has gap=0, so it wins (not the blacklisted one).
    assert worst is not None
    assert worst.get("brand") == "toyota"


def test_hater_filter_builds_comparison_summary():
    listings = [_LISTING_OK, _LISTING_OVERPRICED]
    _, _, summary = _hater_filter(listings)
    # The best alternative to the roast target should be _LISTING_OK (Toyota)
    assert "Toyota" in summary or "toyota" in summary.lower()
    assert "/100" in summary


def test_hater_filter_empty_list():
    worst, gap, summary = _hater_filter([])
    assert worst is None
    assert gap == 0.0
    assert summary == ""


def test_hater_filter_all_blacklisted():
    listings = [dict(_LISTING_OVERPRICED, blacklisted=True)]
    worst, gap, summary = _hater_filter(listings)
    assert worst is None


def test_hater_filter_single_candidate_no_comparison():
    listings = [_LISTING_OVERPRICED]
    worst, gap, summary = _hater_filter(listings)
    assert worst is not None
    assert summary == ""   # no alternative exists


# ── get_car_of_the_day ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_car_of_the_day_no_scan():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    result = await get_car_of_the_day(db)
    assert result is None


@pytest.mark.asyncio
async def test_get_car_of_the_day_empty_listings():
    db = AsyncMock()
    scan = MagicMock()
    scan.listings_json = json.dumps([])
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = scan
    db.execute = AsyncMock(return_value=mock_result)

    result = await get_car_of_the_day(db)
    assert result is None


@pytest.mark.asyncio
async def test_get_car_of_the_day_diamond_when_gap_small():
    """When no car has a gap ≥ threshold, return the best-scoring car as DIAMOND."""
    db = AsyncMock()
    scan = MagicMock()
    # _LISTING_OK: toyota with 100% reliability and 100% price_score → gap = 0
    scan.listings_json = json.dumps([_LISTING_OK, _LISTING_BLACKLISTED])
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = scan
    db.execute = AsyncMock(return_value=mock_result)

    result = await get_car_of_the_day(db)
    assert result is not None
    assert result.mode == "DIAMOND"
    assert result.make == "Toyota"
    assert result.year == 2020


@pytest.mark.asyncio
async def test_get_car_of_the_day_roast_mode():
    """When a car's gap ≥ threshold, return it as ROAST with a comparison summary."""
    db = AsyncMock()
    scan = MagicMock()
    scan.listings_json = json.dumps([_LISTING_OK, _LISTING_OVERPRICED])
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = scan
    db.execute = AsyncMock(return_value=mock_result)

    result = await get_car_of_the_day(db)
    assert result is not None
    assert result.mode == "ROAST"
    assert result.score_gap >= _ROAST_GAP_THRESHOLD
    assert result.comparison_summary != ""


@pytest.mark.asyncio
async def test_get_car_of_the_day_all_blacklisted():
    """Falls back to the only available car even if blacklisted."""
    db = AsyncMock()
    scan = MagicMock()
    scan.listings_json = json.dumps([_LISTING_BLACKLISTED])
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = scan
    db.execute = AsyncMock(return_value=mock_result)

    result = await get_car_of_the_day(db)
    assert result is not None


@pytest.mark.asyncio
async def test_get_car_of_the_day_no_image():
    listing = dict(_LISTING_OK, images=[])
    db = AsyncMock()
    scan = MagicMock()
    scan.listings_json = json.dumps([listing])
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = scan
    db.execute = AsyncMock(return_value=mock_result)

    result = await get_car_of_the_day(db)
    assert result is not None
    assert result.image_url == ""
