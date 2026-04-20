"""
Composite scoring engine — aggregates weak signals into risk scores.

Sprint 4: category weights derived from CorrelationResult records (avg |r|)
instead of hardcoded guesses. Falls back to CATEGORY_WEIGHTS from config when
no correlation data exists (fresh deployment or first run).

Formula:
  weight  = avg|r| from CorrelationResult for that category, else config default
  recency = exp(-λ * age_hours)  [half-life 12 hours]
  base    = sum(severity * weight * recency)
  score   = min(100, base * 10 * (1 + (n_unique_categories - 1) * CONVERGENCE_FACTOR))
"""
from __future__ import annotations

import json
import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import CATEGORY_WEIGHTS
from .models import CorrelationResult, RegionScore, SectorScore, Signal

logger = logging.getLogger(__name__)

RECENCY_LAMBDA: float = math.log(2) / 12.0  # half-life 12 hours
CONVERGENCE_FACTOR: float = 0.15             # +15% per additional unique category


def _recency_decay(age_hours: float) -> float:
    """Exponential decay by signal age. Returns 1.0 at age 0, 0.5 at 12h, 0.25 at 24h."""
    return math.exp(-RECENCY_LAMBDA * max(0.0, age_hours))


def _compute_trend(current: float, previous: float | None) -> str:
    if previous is None:
        return "stable"
    diff = current - previous
    if diff > 5:
        return "rising"
    if diff < -5:
        return "falling"
    return "stable"


async def _get_previous_scores(
    db: AsyncSession,
    score_class: type,
    key_field: str,
    before: datetime,
) -> dict[str, float]:
    """Get the most recent score for each region/sector before given time."""
    subq = (
        select(
            getattr(score_class, key_field),
            func.max(score_class.calculated_at).label("max_calc"),
        )
        .where(score_class.calculated_at < before)
        .group_by(getattr(score_class, key_field))
        .subquery()
    )

    result = await db.execute(
        select(getattr(score_class, key_field), score_class.score).join(
            subq,
            and_(
                getattr(score_class, key_field) == getattr(subq.c, key_field),
                score_class.calculated_at == subq.c.max_calc,
            ),
        )
    )
    return {row[0]: row[1] for row in result.all()}


async def _load_correlation_weights(db: AsyncSession) -> dict[str, float]:
    """
    Average |r| per signal category from stored CorrelationResult records.
    Higher correlation → higher weight for that category's signals.
    Returns {} when no correlations have been computed yet.
    """
    result = await db.execute(
        select(
            CorrelationResult.signal_category,
            func.avg(func.abs(CorrelationResult.correlation_coefficient)),
        ).group_by(CorrelationResult.signal_category)
    )
    return {row[0]: float(row[1]) for row in result.all()}


async def compute_scores(db: AsyncSession) -> None:
    """Main scoring function — called hourly by scheduler."""
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=24)

    result = await db.execute(
        select(Signal).where(Signal.signal_time >= window_start)
    )
    signals = result.scalars().all()

    if not signals:
        logger.info("No signals in 24h window, skipping scoring")
        return

    correlation_weights = await _load_correlation_weights(db)
    if correlation_weights:
        logger.debug("Evidence-based weights loaded for %d categories", len(correlation_weights))
    else:
        logger.debug("No correlation data yet; falling back to config defaults")

    by_region: dict[str, list[Signal]] = defaultdict(list)
    by_sector: dict[str, list[Signal]] = defaultdict(list)

    for sig in signals:
        if sig.region:
            by_region[sig.region].append(sig)
        if sig.sector:
            by_sector[sig.sector].append(sig)

    prev_region = await _get_previous_scores(
        db, RegionScore, "region", now - timedelta(hours=1)
    )
    prev_sector = await _get_previous_scores(
        db, SectorScore, "sector", now - timedelta(hours=1)
    )

    for region, region_signals in by_region.items():
        score = _compute_composite(region_signals, now, correlation_weights)
        trend = _compute_trend(score, prev_region.get(region))
        top = sorted(region_signals, key=lambda s: s.severity, reverse=True)[:5]
        top_json = json.dumps([
            {"id": s.id, "title": s.title, "severity": s.severity} for s in top
        ])
        db.add(RegionScore(
            region=region, score=score, signal_count=len(region_signals),
            top_signals_json=top_json, trend=trend,
            period_start=window_start, period_end=now,
        ))

    for sector, sector_signals in by_sector.items():
        score = _compute_composite(sector_signals, now, correlation_weights)
        trend = _compute_trend(score, prev_sector.get(sector))
        top = sorted(sector_signals, key=lambda s: s.severity, reverse=True)[:5]
        top_json = json.dumps([
            {"id": s.id, "title": s.title, "severity": s.severity} for s in top
        ])
        db.add(SectorScore(
            sector=sector, score=score, signal_count=len(sector_signals),
            top_signals_json=top_json, trend=trend,
            period_start=window_start, period_end=now,
        ))

    await db.commit()
    logger.info(
        "Scoring complete: %d regions, %d sectors",
        len(by_region),
        len(by_sector),
    )


def _compute_composite(
    signals: list[Signal],
    now: datetime,
    correlation_weights: dict[str, float] | None = None,
) -> float:
    """
    Evidence-based composite score:
      weight  = avg|r| from CorrelationResult if available, else CATEGORY_WEIGHTS
      recency = exp(-λ * age_hours)
      base    = sum(severity * weight * recency)
      score   = min(100, base * 10 * convergence_multiplier)
    """
    if not signals:
        return 0.0

    weights = correlation_weights or {}
    base_score = 0.0
    categories_seen: set[str] = set()

    for sig in signals:
        weight = weights.get(sig.category) or CATEGORY_WEIGHTS.get(sig.category, 0.8)
        st = sig.signal_time
        if st.tzinfo is None:
            st = st.replace(tzinfo=timezone.utc)
        age_hours = (now - st).total_seconds() / 3600
        base_score += sig.severity * weight * _recency_decay(age_hours)
        categories_seen.add(sig.category)

    convergence_mult = 1.0 + max(0, len(categories_seen) - 1) * CONVERGENCE_FACTOR
    return min(100.0, max(0.0, base_score * 10.0 * convergence_mult))
