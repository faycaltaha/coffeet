"""
Composite scoring engine — aggregates weak signals into risk scores.

The key insight: one signal is noise, multiple signals from different
categories pointing at the same region/sector = convergence = something
is brewing. This is how intelligence analysts think.
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import CATEGORY_WEIGHTS, RECENCY_BANDS
from .models import RegionScore, SectorScore, Signal

logger = logging.getLogger(__name__)


def _recency_multiplier(signal_time: datetime, now: datetime) -> float:
    """More recent signals get higher weight."""
    age_hours = (now - signal_time).total_seconds() / 3600
    for max_hours, multiplier in RECENCY_BANDS:
        if age_hours <= max_hours:
            return multiplier
    return 0.5


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
        score = _compute_composite(region_signals, now)
        trend = _compute_trend(score, prev_region.get(region))

        top = sorted(region_signals, key=lambda s: s.severity, reverse=True)[:5]
        top_json = json.dumps([
            {"id": s.id, "title": s.title, "severity": s.severity}
            for s in top
        ])

        db.add(RegionScore(
            region=region,
            score=score,
            signal_count=len(region_signals),
            top_signals_json=top_json,
            trend=trend,
            period_start=window_start,
            period_end=now,
        ))

    for sector, sector_signals in by_sector.items():
        score = _compute_composite(sector_signals, now)
        trend = _compute_trend(score, prev_sector.get(sector))

        top = sorted(sector_signals, key=lambda s: s.severity, reverse=True)[:5]
        top_json = json.dumps([
            {"id": s.id, "title": s.title, "severity": s.severity}
            for s in top
        ])

        db.add(SectorScore(
            sector=sector,
            score=score,
            signal_count=len(sector_signals),
            top_signals_json=top_json,
            trend=trend,
            period_start=window_start,
            period_end=now,
        ))

    await db.commit()
    logger.info(
        "Scoring complete: %d regions, %d sectors",
        len(by_region),
        len(by_sector),
    )


def _compute_composite(signals: list[Signal], now: datetime) -> float:
    """
    Composite score formula:
      base = sum(severity * category_weight * recency_multiplier)
      convergence_bonus = min(20, signal_count * 3)
      diversity_bonus = unique_categories * 5
      final = min(100, normalized)
    """
    base_score = 0.0
    categories_seen: set[str] = set()

    for sig in signals:
        weight = CATEGORY_WEIGHTS.get(sig.category, 0.8)
        recency = _recency_multiplier(sig.signal_time, now)
        base_score += sig.severity * weight * recency
        categories_seen.add(sig.category)

    convergence_bonus = min(20, len(signals) * 3)
    diversity_bonus = len(categories_seen) * 5

    raw = base_score * 10 + convergence_bonus + diversity_bonus
    return min(100.0, max(0.0, raw))
