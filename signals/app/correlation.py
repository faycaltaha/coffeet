"""
Correlation engine — discovers statistical relationships between signal patterns
and historical crises.

Algorithm:
  1. For each crisis with a peak_date, examine the 90-day pre-crisis window.
  2. For each signal category, build a daily severity series over that window.
  3. Correlate it against a linearly-rising "proximity to crisis" series.
  4. Store significant results (p < 0.10, |r| >= 0.25) in CorrelationResult.
  5. Active pattern detection: z-score current signal activity vs 30-day baseline,
     then match elevated categories against stored CorrelationResult records.
"""
from __future__ import annotations

import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean, stdev

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import CorrelationResult, Crisis, Signal

logger = logging.getLogger(__name__)

MIN_SAMPLE = 5
P_VALUE_THRESHOLD = 0.10
MIN_CORRELATION = 0.25


# ── Pure statistical helpers ────────────────────────────────────────────────


def _normal_cdf(x: float) -> float:
    """CDF of the standard normal distribution using math.erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _pearson(x: list[float], y: list[float]) -> tuple[float, float]:
    """
    Pearson r and two-tailed p-value (normal approximation via t-statistic).
    Returns (0.0, 1.0) when correlation cannot be computed.
    """
    n = len(x)
    if n < MIN_SAMPLE:
        return 0.0, 1.0
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    den_x = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    den_y = math.sqrt(sum((yi - my) ** 2 for yi in y))
    if den_x == 0.0 or den_y == 0.0:
        return 0.0, 1.0
    r = max(-1.0, min(1.0, num / (den_x * den_y)))
    if abs(r) >= 1.0:
        return r, 0.0
    t = r * math.sqrt(n - 2) / math.sqrt(1.0 - r * r)
    p = 2.0 * (1.0 - _normal_cdf(abs(t)))
    return r, max(0.0, min(1.0, p))


def _daily_severity_bins(
    signals: list[Signal], start: datetime, end: datetime
) -> list[float]:
    """
    Average signal severity per calendar day over [start, end].
    Days with no signals get 0.0.
    Normalizes to naive datetimes so SQLite (strips tz) and PostgreSQL
    (preserves tz) both work.
    """
    start_n = start.replace(tzinfo=None) if start.tzinfo else start
    end_n = end.replace(tzinfo=None) if end.tzinfo else end
    days = max(1, (end_n - start_n).days + 1)
    bins: dict[int, list[float]] = defaultdict(list)
    for sig in signals:
        st = sig.signal_time
        st_n = st.replace(tzinfo=None) if st.tzinfo else st
        idx = (st_n - start_n).days
        if 0 <= idx < days:
            bins[idx].append(sig.severity)
    return [mean(bins[i]) if i in bins else 0.0 for i in range(days)]


def _lead_time_series(n: int) -> list[float]:
    """
    Linearly rising series of length n from 0.0 to 1.0.
    Represents increasing proximity to a crisis peak.
    """
    if n <= 1:
        return [1.0] * max(1, n)
    return [i / (n - 1) for i in range(n)]


def _z_score(value: float, baseline: list[float]) -> float:
    """Standard-score of value relative to a baseline distribution."""
    if len(baseline) < 2:
        return 0.0
    m = mean(baseline)
    s = stdev(baseline)
    if s == 0.0:
        return 0.0
    return (value - m) / s


# ── Main analysis functions ─────────────────────────────────────────────────


async def compute_correlations(db: AsyncSession) -> int:
    """
    Run correlation analysis over all (crisis, signal_category) pairs.

    For each crisis that has a peak_date, fetch signals in the 90-day window
    before the peak, build a daily severity timeseries, correlate it against
    a linearly-rising proximity series, and store significant results.

    Returns the number of CorrelationResult records stored.
    """
    now = datetime.now(timezone.utc)
    window_days = 90

    crises_result = await db.execute(
        select(Crisis).where(Crisis.peak_date.is_not(None))
    )
    crises = crises_result.scalars().all()

    if not crises:
        logger.info("No crises with peak_date; skipping correlation analysis")
        return 0

    cats_result = await db.execute(select(Signal.category).distinct())
    categories = [row[0] for row in cats_result.all()]

    if not categories:
        logger.info("No signal categories found; skipping correlation analysis")
        return 0

    stored = 0

    for crisis in crises:
        peak: datetime = crisis.peak_date  # type: ignore[assignment]
        window_start = peak - timedelta(days=window_days)

        for category in categories:
            sigs_result = await db.execute(
                select(Signal).where(
                    and_(
                        Signal.category == category,
                        Signal.signal_time >= window_start,
                        Signal.signal_time <= peak,
                    )
                )
            )
            signals = sigs_result.scalars().all()

            if len(signals) < MIN_SAMPLE:
                continue

            severity_series = _daily_severity_bins(signals, window_start, peak)
            proximity_series = _lead_time_series(len(severity_series))

            r, p = _pearson(severity_series, proximity_series)

            if p > P_VALUE_THRESHOLD or abs(r) < MIN_CORRELATION:
                continue

            max_sev = max(severity_series)
            peak_day = next(
                i for i, v in enumerate(severity_series) if v == max_sev
            )
            lag_days = max(0, len(severity_series) - peak_day - 1)

            db.add(CorrelationResult(
                signal_category=category,
                crisis_type=crisis.crisis_type,
                region=crisis.region,
                lag_days=lag_days,
                correlation_coefficient=round(r, 4),
                p_value=round(p, 4),
                sample_size=len(signals),
                computed_at=now,
            ))
            stored += 1

    if stored:
        await db.commit()

    logger.info("Correlation analysis complete: %d significant results stored", stored)
    return stored


async def detect_active_patterns(
    db: AsyncSession,
    region: str | None = None,
) -> list[dict]:
    """
    Compare current 24-hour signal activity against stored CorrelationResult
    records.  Returns up to 10 pattern matches sorted by z-score descending.

    A match fires when:
      - A signal category has a stored significant correlation with some crisis type
      - The category's current severity is elevated (z-score >= 1.0) vs
        the prior 30-day baseline
    """
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)
    thirty_ago = now - timedelta(days=30)

    sig_query = select(Signal).where(Signal.signal_time >= day_ago)
    if region:
        sig_query = sig_query.where(Signal.region == region)
    recent_sigs = (await db.execute(sig_query)).scalars().all()

    if not recent_sigs:
        return []

    baseline_result = await db.execute(
        select(Signal.category, Signal.severity).where(
            and_(
                Signal.signal_time >= thirty_ago,
                Signal.signal_time < day_ago,
            )
        )
    )
    baseline_by_cat: dict[str, list[float]] = defaultdict(list)
    for cat, sev in baseline_result.all():
        baseline_by_cat[cat].append(sev)

    current_by_cat: dict[str, list[float]] = defaultdict(list)
    for sig in recent_sigs:
        current_by_cat[sig.category].append(sig.severity)

    corr_result = await db.execute(
        select(CorrelationResult).order_by(
            CorrelationResult.correlation_coefficient.desc()
        )
    )
    correlations = corr_result.scalars().all()

    matches: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for corr in correlations:
        cat = corr.signal_category
        key = (cat, corr.crisis_type)
        if key in seen or cat not in current_by_cat:
            continue

        current_avg = mean(current_by_cat[cat])
        z = _z_score(current_avg, baseline_by_cat.get(cat, []))

        if z < 1.0:
            continue

        seen.add(key)
        matches.append({
            "signal_category": cat,
            "crisis_type": corr.crisis_type,
            "region": corr.region,
            "lag_days": corr.lag_days,
            "correlation": corr.correlation_coefficient,
            "z_score": round(z, 2),
            "risk_level": "high" if z >= 2.0 else "elevated",
            "description": (
                f"Elevated {cat} signals (z={z:.1f}) match historical precursor "
                f"pattern for {corr.crisis_type} crises "
                f"(typical lead time {corr.lag_days}d, r={corr.correlation_coefficient:.2f})"
            ),
        })

    return sorted(matches, key=lambda m: m["z_score"], reverse=True)[:10]
