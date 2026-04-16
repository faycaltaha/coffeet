"""
Alert engine — evaluates scores against thresholds, generates alerts.
Deduplicates to avoid alert fatigue.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import REGION_ALERT_CRITICAL, REGION_ALERT_HIGH, SECTOR_SPIKE_THRESHOLD
from .models import Alert, RegionScore, SectorScore

logger = logging.getLogger(__name__)


async def _has_recent_alert(
    db: AsyncSession,
    alert_type: str,
    region: str | None,
    sector: str | None,
    hours: int = 12,
) -> bool:
    """Check if a similar alert was created within the dedup window."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    conditions = [
        Alert.alert_type == alert_type,
        Alert.created_at >= cutoff,
    ]
    if region:
        conditions.append(Alert.region == region)
    if sector:
        conditions.append(Alert.sector == sector)

    result = await db.execute(
        select(func.count()).select_from(Alert).where(and_(*conditions))
    )
    return (result.scalar() or 0) > 0


async def evaluate_alerts(db: AsyncSession) -> int:
    """Evaluate latest scores and generate alerts. Returns count created."""
    now = datetime.now(timezone.utc)
    created = 0

    latest_calc = await db.execute(
        select(func.max(RegionScore.calculated_at))
    )
    latest_time = latest_calc.scalar()

    if latest_time:
        result = await db.execute(
            select(RegionScore).where(RegionScore.calculated_at == latest_time)
        )
        region_scores = result.scalars().all()

        for rs in region_scores:
            if rs.score >= REGION_ALERT_CRITICAL:
                if not await _has_recent_alert(
                    db, "region_risk", rs.region, None
                ):
                    db.add(Alert(
                        alert_type="region_risk",
                        severity="critical",
                        title=(
                            f"CRITICAL risk: {rs.region} "
                            f"(score {rs.score:.0f})"
                        ),
                        description=(
                            f"Region {rs.region} composite score reached "
                            f"{rs.score:.1f}, exceeding critical threshold "
                            f"of {REGION_ALERT_CRITICAL}. "
                            f"{rs.signal_count} signals contributing."
                        ),
                        region=rs.region,
                        score_value=rs.score,
                        threshold_value=REGION_ALERT_CRITICAL,
                        related_signals_json=rs.top_signals_json,
                    ))
                    created += 1

            elif rs.score >= REGION_ALERT_HIGH:
                if not await _has_recent_alert(
                    db, "region_risk", rs.region, None
                ):
                    db.add(Alert(
                        alert_type="region_risk",
                        severity="high",
                        title=(
                            f"High risk: {rs.region} "
                            f"(score {rs.score:.0f})"
                        ),
                        description=(
                            f"Region {rs.region} composite score reached "
                            f"{rs.score:.1f}, exceeding high threshold "
                            f"of {REGION_ALERT_HIGH}. "
                            f"{rs.signal_count} signals contributing."
                        ),
                        region=rs.region,
                        score_value=rs.score,
                        threshold_value=REGION_ALERT_HIGH,
                        related_signals_json=rs.top_signals_json,
                    ))
                    created += 1

    latest_sector_calc = await db.execute(
        select(func.max(SectorScore.calculated_at))
    )
    latest_sector_time = latest_sector_calc.scalar()

    if latest_sector_time:
        result = await db.execute(
            select(SectorScore).where(
                SectorScore.calculated_at == latest_sector_time
            )
        )
        sector_scores = result.scalars().all()

        prev_cutoff = now - timedelta(hours=25)
        for ss in sector_scores:
            prev_result = await db.execute(
                select(SectorScore.score)
                .where(
                    and_(
                        SectorScore.sector == ss.sector,
                        SectorScore.calculated_at >= prev_cutoff,
                        SectorScore.calculated_at < latest_sector_time,
                    )
                )
                .order_by(SectorScore.calculated_at.asc())
                .limit(1)
            )
            prev_score = prev_result.scalar()

            if prev_score is not None:
                spike = ss.score - prev_score
                if spike >= SECTOR_SPIKE_THRESHOLD:
                    if not await _has_recent_alert(
                        db, "sector_spike", None, ss.sector
                    ):
                        db.add(Alert(
                            alert_type="sector_spike",
                            severity="high",
                            title=(
                                f"Sector spike: {ss.sector} "
                                f"(+{spike:.0f} points)"
                            ),
                            description=(
                                f"Sector {ss.sector} score jumped from "
                                f"{prev_score:.1f} to {ss.score:.1f} "
                                f"({spike:+.1f}) in 24 hours."
                            ),
                            sector=ss.sector,
                            score_value=ss.score,
                            threshold_value=SECTOR_SPIKE_THRESHOLD,
                            related_signals_json=ss.top_signals_json,
                        ))
                        created += 1

    if created:
        await db.commit()
        logger.info("Created %d new alerts", created)

    return created
