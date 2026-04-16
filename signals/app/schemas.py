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
