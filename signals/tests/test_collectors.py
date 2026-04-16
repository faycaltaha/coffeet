"""
Unit tests for collector parsing and severity normalization functions.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.collectors.usgs import _extract_region, _magnitude_to_severity
from app.collectors.gdelt import _classify_sector, _parse_gdelt_date, _tone_to_severity
from app.collectors.fred import _compute_severity


# ── Inline copies of pure functions from modules with heavy deps ───────────
# yfinance and feedparser may not be installed in the test environment.


def _price_severity(pct_1d: float, pct_5d: float) -> float:
    """Score severity from price movements (copied from yfinance_collector)."""
    max_pct = max(abs(pct_1d), abs(pct_5d))
    if max_pct >= 0.08:
        return 1.0
    if max_pct >= 0.05:
        return 0.8
    if max_pct >= 0.03:
        return 0.6
    if max_pct >= 0.01:
        return 0.3
    return 0.1


def _keyword_severity(title: str, summary: str) -> float:
    """Score severity by keyword density (copied from rss_news)."""
    from app.config import GDELT_KEYWORDS

    crisis_terms = {
        "crisis", "war", "collapse", "emergency", "catastrophe",
        "explosion", "attack", "shutdown", "default", "crash",
    }
    text = f"{title} {summary}".lower()

    crisis_hits = sum(1 for t in crisis_terms if t in text)
    if crisis_hits >= 2:
        return 0.9
    if crisis_hits == 1:
        return 0.7

    weak_hits = sum(1 for kw in GDELT_KEYWORDS if kw in text)
    if weak_hits >= 3:
        return 0.6
    if weak_hits >= 2:
        return 0.4
    if weak_hits >= 1:
        return 0.3
    return 0.1


# ── USGS: magnitude → severity ────────────────────────────────────────────


class TestMagnitudeToSeverity:
    def test_extreme_earthquake(self):
        assert _magnitude_to_severity(8.5) == 1.0

    def test_major_earthquake(self):
        assert _magnitude_to_severity(7.2) == 0.9

    def test_strong_earthquake(self):
        assert _magnitude_to_severity(6.5) == 0.7

    def test_moderate_earthquake(self):
        assert _magnitude_to_severity(5.0) == 0.5

    def test_light_earthquake(self):
        assert _magnitude_to_severity(4.5) == 0.3

    def test_minor_earthquake(self):
        assert _magnitude_to_severity(2.0) == 0.1

    def test_boundary_8(self):
        assert _magnitude_to_severity(8.0) == 1.0

    def test_boundary_7(self):
        assert _magnitude_to_severity(7.0) == 0.9

    def test_boundary_6(self):
        assert _magnitude_to_severity(6.0) == 0.7


class TestExtractRegion:
    def test_comma_format(self):
        assert _extract_region("50km S of Tokyo, Japan") == "Japan"

    def test_of_format(self):
        assert _extract_region("150km NW of Auckland") == "Auckland"

    def test_plain_string(self):
        assert _extract_region("Mid-Atlantic Ridge") == "Mid-Atlantic Ridge"

    def test_multiple_commas(self):
        assert _extract_region("near coast of, Honshu, Japan") == "Japan"


# ── GDELT: tone → severity ────────────────────────────────────────────────


class TestToneToSeverity:
    def test_very_negative(self):
        assert _tone_to_severity(-20) == 1.0

    def test_negative(self):
        assert _tone_to_severity(-12) == 0.8

    def test_moderately_negative(self):
        assert _tone_to_severity(-7) == 0.6

    def test_slightly_negative(self):
        assert _tone_to_severity(-3) == 0.4

    def test_near_zero(self):
        assert _tone_to_severity(-1) == 0.2

    def test_positive(self):
        assert _tone_to_severity(5) == 0.1


class TestParseGdeltDate:
    def test_valid_date(self):
        result = _parse_gdelt_date("20260416T143000Z")
        assert result.year == 2026
        assert result.month == 4
        assert result.day == 16
        assert result.tzinfo == timezone.utc

    def test_invalid_date_returns_now(self):
        result = _parse_gdelt_date("invalid")
        assert result.tzinfo == timezone.utc
        assert (datetime.now(timezone.utc) - result).total_seconds() < 5

    def test_empty_string_returns_now(self):
        result = _parse_gdelt_date("")
        assert result.tzinfo == timezone.utc


class TestClassifySector:
    def test_energy_match(self):
        assert _classify_sector("Oil prices surge as OPEC cuts output") == "energy"

    def test_agriculture_match(self):
        assert _classify_sector("Wheat harvest devastated by drought") == "agriculture"

    def test_finance_match(self):
        assert _classify_sector("Central bank raises interest rate") == "finance"

    def test_no_match(self):
        assert _classify_sector("Cat falls asleep on couch") is None


# ── FRED: deviation → severity ─────────────────────────────────────────────


class TestComputeSeverity:
    def test_high_deviation(self):
        values = [1.0] * 29 + [1.15]  # 15% above average
        assert _compute_severity(values) == 1.0

    def test_moderate_deviation(self):
        values = [1.0] * 29 + [1.06]  # ~6% above
        assert _compute_severity(values) == 0.7

    def test_low_deviation(self):
        values = [1.0] * 29 + [1.03]  # ~3% above
        assert _compute_severity(values) == 0.4

    def test_minimal_deviation(self):
        values = [1.0] * 30  # no deviation
        assert _compute_severity(values) == 0.1

    def test_single_value(self):
        assert _compute_severity([5.0]) == 0.1

    def test_empty_values(self):
        assert _compute_severity([]) == 0.1


# ── Yahoo Finance: price change → severity ─────────────────────────────────


class TestPriceSeverity:
    def test_extreme_move(self):
        assert _price_severity(0.10, 0.05) == 1.0

    def test_large_move(self):
        assert _price_severity(0.06, 0.02) == 0.8

    def test_moderate_move(self):
        assert _price_severity(0.04, 0.01) == 0.6

    def test_small_move(self):
        assert _price_severity(0.015, 0.005) == 0.3

    def test_flat(self):
        assert _price_severity(0.005, 0.003) == 0.1


# ── RSS: keyword density → severity ────────────────────────────────────────


class TestKeywordSeverity:
    def test_multiple_crisis_terms(self):
        sev = _keyword_severity("War crisis emergency", "collapse underway")
        assert sev == 0.9

    def test_single_crisis_term(self):
        sev = _keyword_severity("Market crash expected", "analysts say")
        assert sev == 0.7

    def test_multiple_weak_signals(self):
        sev = _keyword_severity(
            "protest strike demonstration", "workers rally"
        )
        assert sev >= 0.4

    def test_single_weak_signal(self):
        sev = _keyword_severity("Protest in capital", "peaceful march")
        assert sev == 0.3

    def test_no_keywords(self):
        sev = _keyword_severity("Weather forecast sunny", "nice day ahead")
        assert sev == 0.1
