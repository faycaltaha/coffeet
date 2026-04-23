"""Tests for the v2 risk assessment engine."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CorrelationResult, Crisis, RiskAssessment, Signal
from app.risk_engine import (
    _classify_alert_tier,
    _compute_risk_score,
    _lead_time_probability,
    compute_risk_assessments,
)

UTC = timezone.utc
NOW = datetime.now(UTC)


# ── _classify_alert_tier ─────────────────────────────────────────────────────


class TestClassifyAlertTier:
    def test_critical_high_p7d(self):
        assert _classify_alert_tier(0.45, 0.30, 0.60) == "critical"

    def test_critical_high_p30d(self):
        assert _classify_alert_tier(0.10, 0.75, 0.90) == "critical"

    def test_warning_moderate_p7d(self):
        assert _classify_alert_tier(0.25, 0.40, 0.60) == "warning"

    def test_warning_moderate_p30d(self):
        assert _classify_alert_tier(0.10, 0.55, 0.70) == "warning"

    def test_watch(self):
        assert _classify_alert_tier(0.05, 0.35, 0.55) == "watch"

    def test_informational(self):
        assert _classify_alert_tier(0.02, 0.18, 0.30) == "informational"

    def test_none(self):
        assert _classify_alert_tier(0.01, 0.05, 0.10) == "none"


# ── _lead_time_probability ───────────────────────────────────────────────────


class TestLeadTimeProbability:
    def test_all_within_horizon(self):
        assert _lead_time_probability([5, 10, 15], 30) == 1.0

    def test_none_within_horizon(self):
        assert _lead_time_probability([60, 90, 120], 30) == 0.0

    def test_partial(self):
        assert abs(_lead_time_probability([10, 20, 30, 60, 90], 30) - 0.6) < 1e-9

    def test_empty_returns_zero(self):
        assert _lead_time_probability([], 30) == 0.0

    def test_boundary_equal(self):
        assert _lead_time_probability([30], 30) == 1.0

    def test_boundary_over(self):
        assert _lead_time_probability([31], 30) == 0.0


# ── _compute_risk_score ──────────────────────────────────────────────────────


class TestComputeRiskScore:
    def test_all_elevated(self):
        z = {"economic": 2.5, "geopolitical": 3.0}
        score, low, high = _compute_risk_score(z, 0.8, 0.7, 0.9)
        assert 40 < score <= 100
        assert low < score < high

    def test_no_elevation_returns_zero(self):
        z = {"economic": 0.5, "geopolitical": 0.3}
        score, low, high = _compute_risk_score(z, 0.8, 0.7, 0.9)
        assert score == 0.0

    def test_confidence_interval_ordering(self):
        z = {"conflict": 2.0}
        score, low, high = _compute_risk_score(z, 0.5, 0.3, 0.6)
        assert low <= score <= high

    def test_more_sources_tighter_confidence(self):
        z = {"a": 2.0, "b": 2.0, "c": 2.0}
        _, low_many, high_many = _compute_risk_score(z, 0.8, 0.7, 0.8)
        z2 = {"a": 2.0}
        _, low_few, high_few = _compute_risk_score(z2, 0.0, 0.0, 0.0)
        spread_many = high_many - low_many
        spread_few = high_few - low_few
        assert spread_many <= spread_few


# ── Integration: compute_risk_assessments ────────────────────────────────────


class TestComputeRiskAssessments:
    @pytest.mark.asyncio
    async def test_empty_db_returns_zero(self, db: AsyncSession):
        assert await compute_risk_assessments(db) == 0

    @pytest.mark.asyncio
    async def test_no_correlations_returns_zero(self, db: AsyncSession):
        db.add(Signal(
            source="fred", category="economic", title="Test",
            severity=0.9, region="Global",
            signal_time=NOW - timedelta(hours=2),
        ))
        await db.commit()
        assert await compute_risk_assessments(db) == 0

    @pytest.mark.asyncio
    async def test_elevated_signals_produce_assessment(self, db: AsyncSession):
        # Seed correlation result
        db.add(CorrelationResult(
            signal_category="economic",
            crisis_type="financial",
            region="Global",
            lag_days=14,
            correlation_coefficient=0.72,
            p_value=0.03,
            sample_size=20,
        ))
        # Low baseline
        for i in range(28):
            db.add(Signal(
                source="fred", category="economic", title=f"Base {i}",
                severity=0.1 + (i % 3) * 0.01,
                region="Global",
                signal_time=NOW - timedelta(days=30 - i),
            ))
        # High current signals
        for i in range(5):
            db.add(Signal(
                source="fred", category="economic", title=f"High {i}",
                severity=0.9,
                region="Global",
                signal_time=NOW - timedelta(hours=i + 1),
            ))
        await db.commit()

        count = await compute_risk_assessments(db)
        assert count >= 1

        from sqlalchemy import select
        rows = (await db.execute(select(RiskAssessment))).scalars().all()
        assert len(rows) >= 1
        r = rows[0]
        assert r.region == "Global"
        assert r.crisis_type == "financial"
        assert r.risk_score > 0
        assert r.alert_tier in ("informational", "watch", "warning", "critical")
        assert 0 <= r.p_7d <= 1
        assert 0 <= r.p_30d <= 1
        assert 0 <= r.p_90d <= 1

    @pytest.mark.asyncio
    async def test_returns_int(self, db: AsyncSession):
        result = await compute_risk_assessments(db)
        assert isinstance(result, int)
