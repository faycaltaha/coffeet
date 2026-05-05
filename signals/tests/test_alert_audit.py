"""
Tests for the alert audit log — tracks every alert decision for precision/recall.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts import evaluate_alerts
from app.models import AlertAuditLog, RegionScore, SectorScore


UTC = timezone.utc


class TestAlertAuditLogging:
    @pytest.mark.asyncio
    async def test_fired_alert_creates_audit_log(self, db: AsyncSession):
        now = datetime.now(UTC)
        db.add(RegionScore(
            region="TestRegion", score=85.0, signal_count=5,
            trend="rising", period_start=now - timedelta(hours=24),
            period_end=now, calculated_at=now,
        ))
        await db.commit()

        created = await evaluate_alerts(db)
        assert created == 1

        from sqlalchemy import select
        result = await db.execute(select(AlertAuditLog))
        logs = result.scalars().all()

        fired = [l for l in logs if l.decision == "fired"]
        assert len(fired) == 1
        assert fired[0].alert_type == "region_risk"
        assert fired[0].severity == "critical"
        assert fired[0].region == "TestRegion"
        assert fired[0].outcome == "pending"
        assert fired[0].alert_id is not None

    @pytest.mark.asyncio
    async def test_below_threshold_logged(self, db: AsyncSession):
        now = datetime.now(UTC)
        db.add(RegionScore(
            region="SafeRegion", score=30.0, signal_count=2,
            trend="stable", period_start=now - timedelta(hours=24),
            period_end=now, calculated_at=now,
        ))
        await db.commit()

        await evaluate_alerts(db)

        from sqlalchemy import select
        result = await db.execute(select(AlertAuditLog))
        logs = result.scalars().all()

        below = [l for l in logs if l.decision == "below_threshold"]
        assert len(below) == 1
        assert below[0].region == "SafeRegion"
        assert below[0].score_value == 30.0

    @pytest.mark.asyncio
    async def test_dedup_suppression_logged(self, db: AsyncSession):
        now = datetime.now(UTC)
        db.add(RegionScore(
            region="HotRegion", score=90.0, signal_count=8,
            trend="rising", period_start=now - timedelta(hours=24),
            period_end=now, calculated_at=now,
        ))
        await db.commit()

        await evaluate_alerts(db)
        await evaluate_alerts(db)

        from sqlalchemy import select
        result = await db.execute(select(AlertAuditLog))
        logs = result.scalars().all()

        fired = [l for l in logs if l.decision == "fired"]
        suppressed = [l for l in logs if l.decision == "suppressed_dedup"]
        assert len(fired) == 1
        assert len(suppressed) == 1

    @pytest.mark.asyncio
    async def test_high_severity_alert_logged(self, db: AsyncSession):
        now = datetime.now(UTC)
        db.add(RegionScore(
            region="MedRegion", score=65.0, signal_count=3,
            trend="stable", period_start=now - timedelta(hours=24),
            period_end=now, calculated_at=now,
        ))
        await db.commit()

        await evaluate_alerts(db)

        from sqlalchemy import select
        result = await db.execute(select(AlertAuditLog))
        logs = result.scalars().all()

        fired = [l for l in logs if l.decision == "fired"]
        assert len(fired) == 1
        assert fired[0].severity == "high"


class TestAlertStatsEndpoint:
    @pytest.mark.asyncio
    async def test_empty_stats(self, client):
        resp = await client.get("/api/alert-log/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_evaluated"] == 0
        assert data["precision"] is None

    @pytest.mark.asyncio
    async def test_stats_with_data(self, db: AsyncSession, client):
        now = datetime.now(UTC)
        db.add(AlertAuditLog(
            alert_type="region_risk", severity="critical",
            region="Europe", score_value=85.0, threshold_value=80.0,
            decision="fired", outcome="true_positive",
        ))
        db.add(AlertAuditLog(
            alert_type="region_risk", severity="high",
            region="Asia", score_value=70.0, threshold_value=60.0,
            decision="fired", outcome="false_positive",
        ))
        db.add(AlertAuditLog(
            alert_type="region_risk", severity="low",
            region="Africa", score_value=30.0, threshold_value=60.0,
            decision="below_threshold",
        ))
        await db.commit()

        resp = await client.get("/api/alert-log/stats")
        data = resp.json()
        assert data["total_evaluated"] == 3
        assert data["total_fired"] == 2
        assert data["total_below_threshold"] == 1
        assert data["true_positives"] == 1
        assert data["false_positives"] == 1
        assert data["precision"] == 0.5


class TestOutcomeUpdate:
    @pytest.mark.asyncio
    async def test_update_outcome(self, db: AsyncSession, client):
        db.add(AlertAuditLog(
            alert_type="region_risk", severity="critical",
            region="Europe", score_value=85.0, threshold_value=80.0,
            decision="fired", outcome="pending",
        ))
        await db.commit()

        from sqlalchemy import select
        result = await db.execute(select(AlertAuditLog))
        log = result.scalars().first()

        resp = await client.patch(
            f"/api/alert-log/{log.id}/outcome",
            json={"outcome": "true_positive", "notes": "Crisis confirmed 14 days later"},
        )
        assert resp.status_code == 200
        assert resp.json()["outcome"] == "true_positive"

        await db.refresh(log)
        assert log.outcome == "true_positive"
        assert log.outcome_notes == "Crisis confirmed 14 days later"
        assert log.outcome_updated_at is not None

    @pytest.mark.asyncio
    async def test_invalid_outcome_rejected(self, db: AsyncSession, client):
        db.add(AlertAuditLog(
            alert_type="region_risk", severity="critical",
            region="Europe", score_value=85.0, threshold_value=80.0,
            decision="fired", outcome="pending",
        ))
        await db.commit()

        from sqlalchemy import select
        result = await db.execute(select(AlertAuditLog))
        log = result.scalars().first()

        resp = await client.patch(
            f"/api/alert-log/{log.id}/outcome",
            json={"outcome": "maybe"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_nonexistent_log_404(self, client):
        resp = await client.patch(
            "/api/alert-log/9999/outcome",
            json={"outcome": "true_positive"},
        )
        assert resp.status_code == 404


class TestAlertLogEndpoint:
    @pytest.mark.asyncio
    async def test_filter_by_decision(self, db: AsyncSession, client):
        db.add(AlertAuditLog(
            alert_type="region_risk", severity="critical",
            region="Europe", score_value=85.0, threshold_value=80.0,
            decision="fired", outcome="pending",
        ))
        db.add(AlertAuditLog(
            alert_type="region_risk", severity="low",
            region="Asia", score_value=30.0, threshold_value=60.0,
            decision="below_threshold",
        ))
        await db.commit()

        resp = await client.get("/api/alert-log?decision=fired")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["decision"] == "fired"
