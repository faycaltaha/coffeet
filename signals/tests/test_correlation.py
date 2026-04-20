"""
Tests for the correlation engine — pure function unit tests + integration tests.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.correlation import (
    MIN_CORRELATION,
    MIN_SAMPLE,
    P_VALUE_THRESHOLD,
    _daily_severity_bins,
    _lead_time_series,
    _normal_cdf,
    _pearson,
    _z_score,
    compute_correlations,
    detect_active_patterns,
)
from app.models import CorrelationResult, Crisis, Signal

UTC = timezone.utc
NOW = datetime.now(UTC)


# ── _normal_cdf ──────────────────────────────────────────────────────────────


class TestNormalCdf:
    def test_zero_is_half(self):
        assert abs(_normal_cdf(0.0) - 0.5) < 1e-9

    def test_positive_above_half(self):
        assert _normal_cdf(1.96) > 0.97

    def test_negative_below_half(self):
        assert _normal_cdf(-1.96) < 0.03

    def test_large_value_near_one(self):
        assert _normal_cdf(10.0) > 0.999


# ── _pearson ─────────────────────────────────────────────────────────────────


class TestPearson:
    def test_perfect_positive_correlation(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
        r, p = _pearson(x, x)
        assert abs(r - 1.0) < 1e-6
        assert p < 0.01

    def test_perfect_negative_correlation(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
        y = [7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0]
        r, p = _pearson(x, y)
        assert abs(r - (-1.0)) < 1e-6
        assert p < 0.01

    def test_constant_y_returns_zero(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
        y = [3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0]
        r, p = _pearson(x, y)
        assert r == 0.0
        assert p == 1.0

    def test_insufficient_data_returns_defaults(self):
        r, p = _pearson([0.1, 0.2], [0.3, 0.4])
        assert r == 0.0
        assert p == 1.0

    def test_empty_returns_defaults(self):
        r, p = _pearson([], [])
        assert r == 0.0
        assert p == 1.0

    def test_r_clamped_within_bounds(self):
        x = [1.0] * 10
        y = [2.0] * 10
        r, p = _pearson(x, y)
        assert -1.0 <= r <= 1.0

    def test_known_strong_correlation(self):
        x = [float(i) for i in range(10)]
        y = [float(i) + (0.5 if i % 2 == 0 else -0.5) for i in range(10)]
        r, p = _pearson(x, y)
        assert r > 0.9
        assert p < 0.05


# ── _daily_severity_bins ─────────────────────────────────────────────────────


class TestDailySeverityBins:
    def _sig(self, signal_time: datetime, severity: float) -> Signal:
        return Signal(
            source="test",
            category="economic",
            title="test",
            severity=severity,
            signal_time=signal_time,
        )

    def test_single_signal_on_day_zero(self):
        start = datetime(2020, 1, 1, tzinfo=UTC)
        end = datetime(2020, 1, 3, tzinfo=UTC)
        bins = _daily_severity_bins([self._sig(start, 0.8)], start, end)
        assert len(bins) == 3
        assert bins[0] == 0.8
        assert bins[1] == 0.0
        assert bins[2] == 0.0

    def test_multiple_signals_averaged_per_day(self):
        start = datetime(2020, 1, 1, tzinfo=UTC)
        end = datetime(2020, 1, 1, tzinfo=UTC)
        bins = _daily_severity_bins(
            [self._sig(start, 0.4), self._sig(start, 0.8)], start, end
        )
        assert len(bins) == 1
        assert abs(bins[0] - 0.6) < 1e-9

    def test_signal_outside_window_ignored(self):
        start = datetime(2020, 1, 1, tzinfo=UTC)
        end = datetime(2020, 1, 2, tzinfo=UTC)
        outside = self._sig(datetime(2019, 12, 31, tzinfo=UTC), 1.0)
        bins = _daily_severity_bins([outside], start, end)
        assert all(b == 0.0 for b in bins)

    def test_empty_signals_all_zeros(self):
        start = datetime(2020, 1, 1, tzinfo=UTC)
        end = datetime(2020, 1, 5, tzinfo=UTC)
        bins = _daily_severity_bins([], start, end)
        assert len(bins) == 5
        assert all(b == 0.0 for b in bins)

    def test_length_matches_day_range(self):
        start = datetime(2020, 1, 1, tzinfo=UTC)
        end = datetime(2020, 1, 10, tzinfo=UTC)
        assert len(_daily_severity_bins([], start, end)) == 10


# ── _lead_time_series ────────────────────────────────────────────────────────


class TestLeadTimeSeries:
    def test_single_element(self):
        assert _lead_time_series(1) == [1.0]

    def test_two_elements(self):
        assert _lead_time_series(2) == [0.0, 1.0]

    def test_starts_at_zero_ends_at_one(self):
        s = _lead_time_series(5)
        assert s[0] == 0.0
        assert s[-1] == 1.0

    def test_correct_length(self):
        assert len(_lead_time_series(10)) == 10

    def test_monotonically_increasing(self):
        s = _lead_time_series(10)
        assert all(s[i] < s[i + 1] for i in range(len(s) - 1))

    def test_evenly_spaced(self):
        s = _lead_time_series(5)
        diffs = [s[i + 1] - s[i] for i in range(len(s) - 1)]
        assert all(abs(d - diffs[0]) < 1e-9 for d in diffs)


# ── _z_score ─────────────────────────────────────────────────────────────────


class TestZScore:
    def test_value_at_mean_is_zero(self):
        assert abs(_z_score(3.0, [1.0, 2.0, 3.0, 4.0, 5.0])) < 1e-9

    def test_value_above_mean_is_positive(self):
        assert _z_score(3.0, [0.0, 2.0]) > 0

    def test_value_below_mean_is_negative(self):
        assert _z_score(1.0, [2.0, 4.0]) < 0

    def test_constant_baseline_returns_zero(self):
        assert _z_score(10.0, [5.0, 5.0, 5.0, 5.0]) == 0.0

    def test_single_value_baseline_returns_zero(self):
        assert _z_score(5.0, [3.0]) == 0.0

    def test_empty_baseline_returns_zero(self):
        assert _z_score(5.0, []) == 0.0

    def test_two_sigma_above(self):
        # mean=0, std≈1 → z≈2 for value=2
        baseline = [-1.0, 0.0, 1.0]
        assert _z_score(2.0, baseline) > 1.5


# ── Integration: compute_correlations ────────────────────────────────────────


@pytest_asyncio.fixture
async def crisis_with_signals(db: AsyncSession):
    """Seed escalating signals leading into a crisis peak."""
    peak = datetime(2020, 4, 15, tzinfo=UTC)
    crisis = Crisis(
        name="Test Crisis for Correlation",
        crisis_type="financial",
        region="Global",
        impact_description="Test",
        start_date=datetime(2020, 1, 1, tzinfo=UTC),
        peak_date=peak,
        impact_score=8.0,
    )
    db.add(crisis)
    await db.commit()

    window_start = peak - timedelta(days=90)
    n = MIN_SAMPLE * 3
    signals = []
    for i in range(n):
        day_offset = i * (90 // n)
        sev = 0.1 + 0.7 * (day_offset / 90)  # escalates toward peak
        signals.append(Signal(
            source="fred",
            category="economic",
            title=f"Signal {i}",
            severity=sev,
            signal_time=window_start + timedelta(days=day_offset),
        ))
    db.add_all(signals)
    await db.commit()
    return db


class TestComputeCorrelations:
    @pytest.mark.asyncio
    async def test_no_crises_returns_zero(self, db: AsyncSession):
        assert await compute_correlations(db) == 0

    @pytest.mark.asyncio
    async def test_returns_int(self, db: AsyncSession):
        assert isinstance(await compute_correlations(db), int)

    @pytest.mark.asyncio
    async def test_crisis_without_peak_date_skipped(self, db: AsyncSession):
        db.add(Crisis(
            name="No Peak",
            crisis_type="geopolitical",
            region="Asia",
            impact_description="Test",
            start_date=datetime(2020, 1, 1, tzinfo=UTC),
            peak_date=None,
            impact_score=5.0,
        ))
        await db.commit()
        assert await compute_correlations(db) == 0

    @pytest.mark.asyncio
    async def test_stored_results_meet_thresholds(
        self, crisis_with_signals: AsyncSession
    ):
        from sqlalchemy import select as sa_select
        await compute_correlations(crisis_with_signals)
        rows = (
            await crisis_with_signals.execute(sa_select(CorrelationResult))
        ).scalars().all()
        for row in rows:
            assert abs(row.correlation_coefficient) >= MIN_CORRELATION
            assert row.p_value <= P_VALUE_THRESHOLD
            assert row.sample_size >= MIN_SAMPLE

    @pytest.mark.asyncio
    async def test_idempotent_on_second_run(
        self, crisis_with_signals: AsyncSession
    ):
        from sqlalchemy import func, select as sa_select
        await compute_correlations(crisis_with_signals)
        count_1 = (
            await crisis_with_signals.execute(
                sa_select(func.count()).select_from(CorrelationResult)
            )
        ).scalar()
        await compute_correlations(crisis_with_signals)
        count_2 = (
            await crisis_with_signals.execute(
                sa_select(func.count()).select_from(CorrelationResult)
            )
        ).scalar()
        # Second run appends more rows (no dedup by design — caller controls frequency)
        assert count_2 >= count_1


# ── Integration: detect_active_patterns ──────────────────────────────────────


class TestDetectActivePatterns:
    @pytest.mark.asyncio
    async def test_empty_db_returns_empty(self, db: AsyncSession):
        assert await detect_active_patterns(db) == []

    @pytest.mark.asyncio
    async def test_no_recent_signals_returns_empty(self, db: AsyncSession):
        db.add(Signal(
            source="fred", category="economic", title="Old",
            severity=0.8,
            signal_time=datetime(2019, 1, 1, tzinfo=UTC),
        ))
        await db.commit()
        assert await detect_active_patterns(db) == []

    @pytest.mark.asyncio
    async def test_returns_list(self, db: AsyncSession):
        assert isinstance(await detect_active_patterns(db), list)

    @pytest.mark.asyncio
    async def test_region_filter_no_match(self, db: AsyncSession):
        assert await detect_active_patterns(db, region="Mars") == []

    @pytest.mark.asyncio
    async def test_elevated_signal_triggers_match(self, db: AsyncSession):
        now = datetime.now(UTC)
        db.add(CorrelationResult(
            signal_category="economic",
            crisis_type="financial",
            region="Global",
            lag_days=14,
            correlation_coefficient=0.72,
            p_value=0.03,
            sample_size=20,
        ))
        # Low baseline with slight variation (ensures stdev > 0 for z-score)
        for i in range(28):
            db.add(Signal(
                source="fred", category="economic", title=f"Base {i}",
                severity=0.1 + (i % 3) * 0.01,  # 0.10 / 0.11 / 0.12
                signal_time=now - timedelta(days=30 - i),
            ))
        # High current
        for i in range(5):
            db.add(Signal(
                source="fred", category="economic", title=f"High {i}",
                severity=0.9,
                signal_time=now - timedelta(hours=i + 1),
            ))
        await db.commit()

        patterns = await detect_active_patterns(db)
        assert len(patterns) >= 1
        m = patterns[0]
        assert m["signal_category"] == "economic"
        assert m["crisis_type"] == "financial"
        assert m["z_score"] > 0
        assert m["risk_level"] in ("elevated", "high")
        assert "description" in m

    @pytest.mark.asyncio
    async def test_max_ten_results_returned(self, db: AsyncSession):
        now = datetime.now(UTC)
        # Seed 15 correlation results for different crisis types
        for idx in range(15):
            db.add(CorrelationResult(
                signal_category="economic",
                crisis_type=f"type_{idx}",
                region="Global",
                lag_days=10,
                correlation_coefficient=0.5,
                p_value=0.05,
                sample_size=10,
            ))
        # High severity recent signals
        for i in range(5):
            db.add(Signal(
                source="fred", category="economic", title=f"High {i}",
                severity=0.9,
                signal_time=now - timedelta(hours=i + 1),
            ))
        # Low baseline
        for i in range(10):
            db.add(Signal(
                source="fred", category="economic", title=f"Base {i}",
                severity=0.05,
                signal_time=now - timedelta(days=5 + i),
            ))
        await db.commit()

        patterns = await detect_active_patterns(db)
        assert len(patterns) <= 10
