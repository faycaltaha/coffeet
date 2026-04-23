"""
FastAPI application — routes, scheduler, and static file serving.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import SIGNAL_API_KEY
from .database import get_db, init_db
from .correlation import detect_active_patterns
from .models import (
    Alert,
    CollectorStatus,
    CorrelationResult,
    Crisis,
    CrisisSignalLink,
    RegionScore,
    SectorScore,
    Signal,
    RiskAssessment,
    SignalPattern,
)
from .schemas import (
    AlertOut,
    CollectorStatusOut,
    CorrelationResultOut,
    CrisisDetail,
    CrisisOut,
    CrisisSignalLinkOut,
    OverviewOut,
    PatternMatchOut,
    RegionScoreOut,
    ScoreHistory,
    SectorScoreOut,
    SignalDetail,
    SignalOut,
    RiskAssessmentDetail,
    RiskAssessmentOut,
    SignalPatternOut,
)
from .scheduler import run_collector, run_correlation_analysis, run_risk_assessment, run_scoring_and_alerts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    scheduler.add_job(run_collector, "interval", args=["rss"], minutes=20, id="rss")
    scheduler.add_job(run_collector, "interval", args=["gdelt"], minutes=30, id="gdelt")
    scheduler.add_job(run_collector, "interval", args=["usgs"], minutes=60, id="usgs")
    scheduler.add_job(run_collector, "interval", args=["noaa"], minutes=60, id="noaa")
    scheduler.add_job(run_collector, "interval", args=["reliefweb"], minutes=60, id="reliefweb")
    scheduler.add_job(run_collector, "interval", args=["yfinance"], hours=2, id="yfinance")
    scheduler.add_job(run_collector, "interval", args=["ais"], hours=4, id="ais")
    scheduler.add_job(run_collector, "interval", args=["eia"], hours=4, id="eia")
    scheduler.add_job(run_collector, "interval", args=["fred"], hours=6, id="fred")
    scheduler.add_job(run_collector, "interval", args=["opensanctions"], hours=6, id="opensanctions")
    scheduler.add_job(run_collector, "interval", args=["acled"], hours=6, id="acled")
    scheduler.add_job(run_collector, "interval", args=["comtrade"], hours=12, id="comtrade")
    scheduler.add_job(run_collector, "interval", args=["imf"], hours=12, id="imf")
    scheduler.add_job(run_scoring_and_alerts, "interval", hours=1, id="scoring")
    scheduler.add_job(run_correlation_analysis, "interval", hours=24, id="correlation")
    scheduler.add_job(run_risk_assessment, "interval", hours=4, id="risk_assessment")

    scheduler.start()
    logger.info("Signal Monitor started — 13 collectors + scoring + correlation + risk assessment")
    yield
    scheduler.shutdown()


app = FastAPI(title="Market Signal Monitor", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth ────────────────────────────────────────────────────────────────────


def verify_api_key(request: Request) -> None:
    if not SIGNAL_API_KEY:
        return
    key = request.headers.get("X-API-Key", "")
    if key != SIGNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


# ── Signals ─────────────────────────────────────────────────────────────────


@app.get("/api/signals", response_model=list[SignalOut])
async def list_signals(
    source: str | None = None,
    category: str | None = None,
    region: str | None = None,
    sector: str | None = None,
    since: datetime | None = None,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_api_key),
):
    query = select(Signal).order_by(Signal.signal_time.desc()).limit(limit)
    if source:
        query = query.where(Signal.source == source)
    if category:
        query = query.where(Signal.category == category)
    if region:
        query = query.where(Signal.region == region)
    if sector:
        query = query.where(Signal.sector == sector)
    if since:
        query = query.where(Signal.signal_time >= since)

    result = await db.execute(query)
    return result.scalars().all()


@app.get("/api/signals/{signal_id}", response_model=SignalDetail)
async def get_signal(
    signal_id: int,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_api_key),
):
    result = await db.execute(select(Signal).where(Signal.id == signal_id))
    signal = result.scalar_one_or_none()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal


# ── Scores ──────────────────────────────────────────────────────────────────


@app.get("/api/scores/regions", response_model=list[RegionScoreOut])
async def list_region_scores(
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_api_key),
):
    latest = await db.execute(select(func.max(RegionScore.calculated_at)))
    latest_time = latest.scalar()
    if not latest_time:
        return []
    result = await db.execute(
        select(RegionScore)
        .where(RegionScore.calculated_at == latest_time)
        .order_by(RegionScore.score.desc())
    )
    return result.scalars().all()


@app.get("/api/scores/sectors", response_model=list[SectorScoreOut])
async def list_sector_scores(
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_api_key),
):
    latest = await db.execute(select(func.max(SectorScore.calculated_at)))
    latest_time = latest.scalar()
    if not latest_time:
        return []
    result = await db.execute(
        select(SectorScore)
        .where(SectorScore.calculated_at == latest_time)
        .order_by(SectorScore.score.desc())
    )
    return result.scalars().all()


@app.get(
    "/api/scores/regions/{region}/history",
    response_model=list[ScoreHistory],
)
async def region_score_history(
    region: str,
    days: int = Query(default=30, le=90),
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_api_key),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(RegionScore)
        .where(and_(RegionScore.region == region, RegionScore.calculated_at >= since))
        .order_by(RegionScore.calculated_at.asc())
    )
    rows = result.scalars().all()
    return [
        ScoreHistory(date=r.calculated_at, score=r.score, signal_count=r.signal_count)
        for r in rows
    ]


@app.get(
    "/api/scores/sectors/{sector}/history",
    response_model=list[ScoreHistory],
)
async def sector_score_history(
    sector: str,
    days: int = Query(default=30, le=90),
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_api_key),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(SectorScore)
        .where(and_(SectorScore.sector == sector, SectorScore.calculated_at >= since))
        .order_by(SectorScore.calculated_at.asc())
    )
    rows = result.scalars().all()
    return [
        ScoreHistory(date=r.calculated_at, score=r.score, signal_count=r.signal_count)
        for r in rows
    ]


# ── Alerts ──────────────────────────────────────────────────────────────────


@app.get("/api/alerts", response_model=list[AlertOut])
async def list_alerts(
    severity: str | None = None,
    is_read: bool | None = None,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_api_key),
):
    query = select(Alert).order_by(Alert.created_at.desc()).limit(limit)
    if severity:
        query = query.where(Alert.severity == severity)
    if is_read is not None:
        query = query.where(Alert.is_read == is_read)
    result = await db.execute(query)
    return result.scalars().all()


@app.patch("/api/alerts/{alert_id}/read")
async def mark_alert_read(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_api_key),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_read = True
    await db.commit()
    return {"ok": True}


# ── Status ──────────────────────────────────────────────────────────────────


@app.get("/api/status", response_model=list[CollectorStatusOut])
async def collector_status(
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_api_key),
):
    result = await db.execute(select(CollectorStatus))
    return result.scalars().all()


# ── Overview ────────────────────────────────────────────────────────────────


@app.get("/api/overview", response_model=OverviewOut)
async def overview(
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_api_key),
):
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)

    signal_count = await db.execute(
        select(func.count()).select_from(Signal).where(
            Signal.collected_at >= day_ago
        )
    )

    alert_count = await db.execute(
        select(func.count()).select_from(Alert).where(Alert.is_read == False)
    )

    latest_region = await db.execute(
        select(func.max(RegionScore.calculated_at))
    )
    lt = latest_region.scalar()
    if lt:
        regions_result = await db.execute(
            select(RegionScore)
            .where(RegionScore.calculated_at == lt)
            .order_by(RegionScore.score.desc())
            .limit(5)
        )
        top_regions = regions_result.scalars().all()
    else:
        top_regions = []

    latest_sector = await db.execute(
        select(func.max(SectorScore.calculated_at))
    )
    st = latest_sector.scalar()
    if st:
        sectors_result = await db.execute(
            select(SectorScore)
            .where(SectorScore.calculated_at == st)
            .order_by(SectorScore.score.desc())
            .limit(5)
        )
        top_sectors = sectors_result.scalars().all()
    else:
        top_sectors = []

    alerts_result = await db.execute(
        select(Alert).order_by(Alert.created_at.desc()).limit(5)
    )

    collectors_result = await db.execute(select(CollectorStatus))

    return OverviewOut(
        total_signals_24h=signal_count.scalar() or 0,
        active_alerts=alert_count.scalar() or 0,
        top_regions=top_regions,
        top_sectors=top_sectors,
        recent_alerts=alerts_result.scalars().all(),
        collectors=collectors_result.scalars().all(),
    )


# ── Crises ─────────────────────────────────────────────────────────────────


@app.get("/api/crises", response_model=list[CrisisOut])
async def list_crises(
    crisis_type: str | None = None,
    region: str | None = None,
    sector: str | None = None,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_api_key),
):
    query = select(Crisis).order_by(Crisis.start_date.desc()).limit(limit)
    if crisis_type:
        query = query.where(Crisis.crisis_type == crisis_type)
    if region:
        query = query.where(Crisis.region == region)
    if sector:
        query = query.where(Crisis.sector == sector)
    result = await db.execute(query)
    return result.scalars().all()


@app.get("/api/crises/{crisis_id}", response_model=CrisisDetail)
async def get_crisis(
    crisis_id: int,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_api_key),
):
    result = await db.execute(select(Crisis).where(Crisis.id == crisis_id))
    crisis = result.scalar_one_or_none()
    if not crisis:
        raise HTTPException(status_code=404, detail="Crisis not found")
    links_result = await db.execute(
        select(CrisisSignalLink).where(CrisisSignalLink.crisis_id == crisis_id)
    )
    links = links_result.scalars().all()
    return CrisisDetail.model_validate(crisis, from_attributes=True).model_copy(
        update={"links": [CrisisSignalLinkOut.model_validate(l, from_attributes=True) for l in links]}
    )


# ── Signal Patterns ────────────────────────────────────────────────────────


@app.get("/api/signal-patterns", response_model=list[SignalPatternOut])
async def list_signal_patterns(
    pattern_type: str | None = None,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_api_key),
):
    query = select(SignalPattern).order_by(SignalPattern.created_at.desc()).limit(limit)
    if pattern_type:
        query = query.where(SignalPattern.pattern_type == pattern_type)
    result = await db.execute(query)
    return result.scalars().all()


@app.get("/api/signal-patterns/{pattern_id}", response_model=SignalPatternOut)
async def get_signal_pattern(
    pattern_id: int,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_api_key),
):
    result = await db.execute(
        select(SignalPattern).where(SignalPattern.id == pattern_id)
    )
    pattern = result.scalar_one_or_none()
    if not pattern:
        raise HTTPException(status_code=404, detail="Signal pattern not found")
    return pattern


# ── Correlations ───────────────────────────────────────────────────────────


@app.get("/api/correlations", response_model=list[CorrelationResultOut])
async def list_correlations(
    signal_category: str | None = None,
    crisis_type: str | None = None,
    min_correlation: float = Query(default=0.25, ge=0.0, le=1.0),
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_api_key),
):
    query = (
        select(CorrelationResult)
        .order_by(CorrelationResult.correlation_coefficient.desc())
        .limit(limit)
    )
    if signal_category:
        query = query.where(CorrelationResult.signal_category == signal_category)
    if crisis_type:
        query = query.where(CorrelationResult.crisis_type == crisis_type)
    result = await db.execute(query)
    rows = result.scalars().all()
    return [r for r in rows if abs(r.correlation_coefficient) >= min_correlation]


@app.get("/api/correlations/active-patterns", response_model=list[PatternMatchOut])
async def active_patterns(
    region: str | None = None,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_api_key),
):
    return await detect_active_patterns(db, region=region)


# ── Risk Assessments ───────────────────────────────────────────────────


@app.get("/api/risk-assessments", response_model=list[RiskAssessmentOut])
async def list_risk_assessments(
    region: str | None = None,
    crisis_type: str | None = None,
    min_score: float = Query(default=0.0, ge=0.0, le=100.0),
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_api_key),
):
    query = (
        select(RiskAssessment)
        .order_by(RiskAssessment.risk_score.desc())
        .limit(limit)
    )
    if region:
        query = query.where(RiskAssessment.region == region)
    if crisis_type:
        query = query.where(RiskAssessment.crisis_type == crisis_type)
    result = await db.execute(query)
    rows = result.scalars().all()
    return [r for r in rows if r.risk_score >= min_score]


@app.get("/api/risk-assessments/{region}", response_model=list[RiskAssessmentDetail])
async def get_region_risk(
    region: str,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(verify_api_key),
):
    latest = await db.execute(select(func.max(RiskAssessment.computed_at)))
    latest_time = latest.scalar()
    if not latest_time:
        return []
    result = await db.execute(
        select(RiskAssessment).where(
            and_(
                RiskAssessment.region == region,
                RiskAssessment.computed_at == latest_time,
            )
        ).order_by(RiskAssessment.risk_score.desc())
    )
    rows = result.scalars().all()
    import json as _json
    return [
        RiskAssessmentDetail(
            region=r.region,
            crisis_type=r.crisis_type,
            risk_score=r.risk_score,
            confidence_low=r.confidence_low,
            confidence_high=r.confidence_high,
            p_7d=r.p_7d,
            p_30d=r.p_30d,
            p_90d=r.p_90d,
            alert_tier=r.alert_tier,
            top_drivers=_json.loads(r.top_drivers_json) if r.top_drivers_json else None,
            historical_analogs=_json.loads(r.historical_analog_json) if r.historical_analog_json else None,
            description=(
                f"{r.region}: {r.risk_score:.0f}/100 risk of {r.crisis_type} "
                f"(P30d={r.p_30d:.0%}, P90d={r.p_90d:.0%}). "
                f"Alert tier: {r.alert_tier}."
            ),
        )
        for r in rows
    ]


# ── Static files ────────────────────────────────────────────────────────────

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")
