"""
Pydantic schemas for API request/response validation.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SignalOut(BaseModel):
    id: int
    source: str
    category: str
    title: str
    description: str | None
    region: str | None
    sector: str | None
    severity: float
    raw_value: float | None
    raw_unit: str | None
    source_url: str | None
    signal_time: datetime
    collected_at: datetime
    is_backfill: bool

    model_config = {"from_attributes": True}


class SignalDetail(SignalOut):
    raw_json: str | None

    model_config = {"from_attributes": True}


class RegionScoreOut(BaseModel):
    id: int
    region: str
    score: float
    signal_count: int
    trend: str
    calculated_at: datetime

    model_config = {"from_attributes": True}


class SectorScoreOut(BaseModel):
    id: int
    sector: str
    score: float
    signal_count: int
    trend: str
    calculated_at: datetime

    model_config = {"from_attributes": True}


class ScoreHistory(BaseModel):
    date: datetime
    score: float
    signal_count: int


class AlertOut(BaseModel):
    id: int
    alert_type: str
    severity: str
    title: str
    description: str | None
    region: str | None
    sector: str | None
    score_value: float | None
    threshold_value: float | None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CollectorStatusOut(BaseModel):
    collector_name: str
    last_run_at: datetime | None
    last_success_at: datetime | None
    last_error: str | None
    signals_collected: int
    status: str

    model_config = {"from_attributes": True}


class OverviewOut(BaseModel):
    total_signals_24h: int
    active_alerts: int
    top_regions: list[RegionScoreOut]
    top_sectors: list[SectorScoreOut]
    recent_alerts: list[AlertOut]
    collectors: list[CollectorStatusOut]


class CrisisOut(BaseModel):
    id: int
    name: str
    crisis_type: str
    region: str
    sector: str | None
    impact_description: str
    start_date: datetime
    peak_date: datetime | None
    end_date: datetime | None
    impact_score: float
    created_at: datetime

    model_config = {"from_attributes": True}


class SignalPatternOut(BaseModel):
    id: int
    name: str
    description: str | None
    pattern_type: str
    signal_sources_json: str | None
    detection_rules_json: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CrisisSignalLinkOut(BaseModel):
    id: int
    crisis_id: int
    signal_pattern_id: int | None
    lead_time_days: int | None
    correlation_strength: float | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CrisisDetail(CrisisOut):
    links: list[CrisisSignalLinkOut] = []

    model_config = {"from_attributes": True}


class CorrelationResultOut(BaseModel):
    id: int
    signal_category: str
    crisis_type: str
    region: str | None
    lag_days: int
    correlation_coefficient: float
    p_value: float
    sample_size: int
    computed_at: datetime

    model_config = {"from_attributes": True}


class PatternMatchOut(BaseModel):
    signal_category: str
    crisis_type: str
    region: str | None
    lag_days: int
    correlation: float
    z_score: float
    risk_level: str
    description: str

class RiskAssessmentOut(BaseModel):
    id: int
    region: str
    crisis_type: str
    risk_score: float
    confidence_low: float
    confidence_high: float
    p_7d: float
    p_30d: float
    p_90d: float
    alert_tier: str
    top_drivers_json: str | None
    historical_analog_json: str | None
    computed_at: datetime
    model_config = {"from_attributes": True}


class AlertAuditLogOut(BaseModel):
    id: int
    alert_id: int | None
    alert_type: str
    severity: str
    region: str | None
    sector: str | None
    score_value: float
    threshold_value: float
    categories_active: int
    decision: str
    outcome: str | None
    outcome_notes: str | None
    outcome_updated_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertStatsOut(BaseModel):
    total_evaluated: int
    total_fired: int
    total_suppressed_dedup: int
    total_below_threshold: int
    pending_outcome: int
    true_positives: int
    false_positives: int
    precision: float | None
    fire_rate: float | None
    avg_score_fired: float | None
    avg_score_below: float | None
    by_severity: dict[str, dict[str, int]]
    by_region: dict[str, dict[str, int]]


class OutcomeUpdate(BaseModel):
    outcome: str
    notes: str | None = None


class RiskAssessmentDetail(BaseModel):
    region: str
    crisis_type: str
    risk_score: float
    confidence_low: float
    confidence_high: float
    p_7d: float
    p_30d: float
    p_90d: float
    alert_tier: str
    top_drivers: list[dict] | None = None
    historical_analogs: list[dict] | None = None
    description: str

