"""
Tests for the composite scoring engine — pure function unit tests + integration.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CorrelationResult, Signal
from app.scoring import (
    CONVERGENCE_FACTOR,
    RECENCY_LAMBDA,
    _compute_composite,
    _compute_trend,
    _load_correlation_weights,
    _recency_decay,
)
from tests.conftest import make_signal

UTC = timezone.utc


# ── _recency_decay ────────────────────────────────────────────────────────────


class TestRecencyDecay:
    def test_age_zero_is_one(self):
        assert abs(_recency_decay(0.0) - 1.0) < 1e-9

    def test_half_life_at_12h(self):
        """By definition of RECENCY_LAMBDA, decay at 12h should be ~0.5."""
        assert abs(_recency_decay(12.0) - 0.5) < 1e-6

    def test_quarter_at_24h(self):
        assert abs(_recency_decay(24.0) - 0.25) < 1e-6

    def test_negative_age_clamped_to_one(self):
        assert _recency_decay(-5.0) == 1.0

    def test_strictly_decreasing(self):
        ages = [0, 6, 12, 18, 24, 48]
        vals = [_recency_decay(a) for a in ages]
        assert all(vals[i] > vals[i + 1] for i in range(len(vals) - 1))

    def test_always_positive(self):
        for hours in [0, 1, 12, 24, 72, 168]:
            assert _recency_decay(hours) > 0.0


# ── _compute_trend ────────────────────────────────────────────────────────────


class TestComputeTrend:
    def test_rising(self):
        assert _compute_trend(70, 60) == "rising"

    def test_falling(self):
        assert _compute_trend(50, 60) == "falling"

    def test_stable(self):
        assert _compute_trend(60, 58) == "stable"

    def test_no_previous(self):
        assert _compute_trend(50, None) == "stable"

    def test_boundary_below_rising(self):
        assert _compute_trend(65, 60) == "stable"

    def test_boundary_above_rising(self):
        assert _compute_trend(65.1, 60) == "rising"


# ── _compute_composite ────────────────────────────────────────────────────────


class TestComputeComposite:
    def test_single_signal(self):
        now = datetime.now(UTC)
        score = _compute_composite([make_signal(severity=0.5, signal_time=now)], now)
        assert 0 < score <= 100

    def test_empty_returns_zero(self):
        assert _compute_composite([], datetime.now(UTC)) == 0.0

    def test_score_capped_at_100(self):
        now = datetime.now(UTC)
        signals = [
            make_signal(category=cat, severity=1.0, signal_time=now)
            for cat in ["seismic", "geopolitical", "energy", "economic", "financial", "news"]
            for _ in range(5)
        ]
        assert _compute_composite(signals, now) == 100.0

    def test_recency_boost(self):
        """Recent signals decay less → higher score."""
        now = datetime.now(UTC)
        recent = [make_signal(severity=0.5, signal_time=now - timedelta(hours=1))]
        older = [make_signal(severity=0.5, signal_time=now - timedelta(hours=20))]
        assert _compute_composite(recent, now) > _compute_composite(older, now)

    def test_convergence_multiplier_increases_with_categories(self):
        """More unique categories → larger convergence_mult → higher score."""
        now = datetime.now(UTC)
        same_cat = [make_signal(category="geopolitical", severity=0.5, signal_time=now) for _ in range(3)]
        diverse = [
            make_signal(category="geopolitical", severity=0.5, signal_time=now),
            make_signal(category="seismic", severity=0.5, signal_time=now),
            make_signal(category="energy", severity=0.5, signal_time=now),
        ]
        assert _compute_composite(diverse, now) > _compute_composite(same_cat, now)

    def test_more_signals_higher_score(self):
        now = datetime.now(UTC)
        one = [make_signal(severity=0.5, signal_time=now)]
        five = [make_signal(severity=0.5, signal_time=now) for _ in range(5)]
        assert _compute_composite(five, now) > _compute_composite(one, now)

    def test_fallback_to_config_weights(self):
        """Without correlation_weights, seismic (1.5) > news (0.8)."""
        now = datetime.now(UTC)
        seismic = [make_signal(category="seismic", severity=0.5, signal_time=now)]
        news = [make_signal(category="news", severity=0.5, signal_time=now)]
        assert _compute_composite(seismic, now) > _compute_composite(news, now)

    def test_evidence_based_weight_overrides_default(self):
        """Passing high correlation weight for 'news' should flip the ordering."""
        now = datetime.now(UTC)
        seismic = [make_signal(category="seismic", severity=0.5, signal_time=now)]
        news = [make_signal(category="news", severity=0.5, signal_time=now)]
        # Give 'news' a very high evidence weight, leave 'seismic' absent → falls back to config
        high_news_weights = {"news": 2.0}
        assert _compute_composite(news, now, high_news_weights) > _compute_composite(seismic, now, high_news_weights)

    def test_convergence_factor_math(self):
        """Verify the multiplier: 1 + (n_cats-1) * CONVERGENCE_FACTOR.
        Use explicit equal weights so the only variable is the multiplier.
        """
        now = datetime.now(UTC)
        equal_w = {"cat_a": 1.0, "cat_b": 1.0, "cat_c": 1.0, "single": 1.0}
        diverse = [make_signal(category=f"cat_{c}", severity=0.5, signal_time=now) for c in "abc"]
        single = [make_signal(category="single", severity=0.5, signal_time=now) for _ in range(3)]
        score_multi = _compute_composite(diverse, now, equal_w)
        score_single = _compute_composite(single, now, equal_w)
        expected_ratio = 1.0 + 2 * CONVERGENCE_FACTOR  # 3 cats → mult = 1 + 2*0.15 = 1.30
        actual_ratio = score_multi / score_single
        assert abs(actual_ratio - expected_ratio) < 0.01

    def test_naive_signal_time_handled(self):
        """SQLite returns naive datetimes; _compute_composite must not raise."""
        now = datetime.now(UTC)
        naive_sig = make_signal(severity=0.5, signal_time=datetime(2024, 1, 1, 12, 0))
        assert _compute_composite([naive_sig], now) >= 0.0


# ── Integration: _load_correlation_weights ────────────────────────────────────


class TestLoadCorrelationWeights:
    @pytest.mark.asyncio
    async def test_empty_db_returns_empty_dict(self, db: AsyncSession):
        weights = await _load_correlation_weights(db)
        assert weights == {}

    @pytest.mark.asyncio
    async def test_returns_avg_abs_r_per_category(self, db: AsyncSession):
        db.add(CorrelationResult(
            signal_category="economic", crisis_type="financial", region="Global",
            lag_days=5, correlation_coefficient=0.80, p_value=0.02, sample_size=20,
        ))
        db.add(CorrelationResult(
            signal_category="economic", crisis_type="supply_chain", region="Global",
            lag_days=3, correlation_coefficient=0.60, p_value=0.04, sample_size=15,
        ))
        db.add(CorrelationResult(
            signal_category="geopolitical", crisis_type="conflict", region="Asia",
            lag_days=7, correlation_coefficient=-0.70, p_value=0.01, sample_size=12,
        ))
        await db.commit()

        weights = await _load_correlation_weights(db)
        assert abs(weights["economic"] - 0.70) < 1e-6       # avg(0.80, 0.60)
        assert abs(weights["geopolitical"] - 0.70) < 1e-6   # avg(|-0.70|) = 0.70

    @pytest.mark.asyncio
    async def test_negative_r_taken_as_absolute(self, db: AsyncSession):
        db.add(CorrelationResult(
            signal_category="climate", crisis_type="humanitarian", region=None,
            lag_days=10, correlation_coefficient=-0.50, p_value=0.05, sample_size=8,
        ))
        await db.commit()
        weights = await _load_correlation_weights(db)
        assert abs(weights["climate"] - 0.50) < 1e-6

    @pytest.mark.asyncio
    async def test_weight_drives_higher_score(self, db: AsyncSession):
        """Category with higher |r| in DB should score higher than one without."""
        db.add(CorrelationResult(
            signal_category="trade", crisis_type="financial", region=None,
            lag_days=2, correlation_coefficient=0.95, p_value=0.001, sample_size=30,
        ))
        await db.commit()

        now = datetime.now(UTC)
        weights = await _load_correlation_weights(db)

        high = [make_signal(category="trade", severity=0.5, signal_time=now)]
        low = [make_signal(category="climate", severity=0.5, signal_time=now)]  # no DB entry → config fallback

        assert _compute_composite(high, now, weights) > _compute_composite(low, now, weights)
