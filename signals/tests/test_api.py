"""
Integration tests for API endpoints with seeded data.
"""
from __future__ import annotations

import sys
import types
from datetime import datetime, timedelta, timezone

# Stub out optional dependencies that can't install in test env
for mod_name in ("feedparser", "yfinance"):
    if mod_name not in sys.modules:
        sys.modules[mod_name] = types.ModuleType(mod_name)

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app
from app.models import Alert, CollectorStatus, RegionScore, SectorScore, Signal

# ── Test database setup ────────────────────────────────────────────────────

TEST_ENGINE = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestSession = async_sessionmaker(TEST_ENGINE, expire_on_commit=False)


async def override_get_db():
    async with TestSession() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db():
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def seeded_db(db: AsyncSession):
    """Seed the database with test data."""
    now = datetime.now(timezone.utc)

    signals = [
        Signal(
            source="usgs",
            category="seismic",
            title="M6.5 earthquake near Japan",
            severity=0.7,
            region="Japan",
            sector=None,
            signal_time=now - timedelta(hours=2),
        ),
        Signal(
            source="gdelt",
            category="geopolitical",
            title="Trade sanctions announced",
            severity=0.6,
            region="China",
            sector="finance",
            signal_time=now - timedelta(hours=5),
        ),
        Signal(
            source="rss",
            category="news",
            title="Oil pipeline disruption reported",
            severity=0.5,
            region="Middle East",
            sector="energy",
            signal_time=now - timedelta(hours=1),
        ),
    ]
    db.add_all(signals)

    region_score = RegionScore(
        region="Japan",
        score=65.0,
        signal_count=3,
        top_signals_json="[]",
        trend="rising",
        period_start=now - timedelta(hours=24),
        period_end=now,
        calculated_at=now,
    )
    sector_score = SectorScore(
        sector="energy",
        score=45.0,
        signal_count=2,
        top_signals_json="[]",
        trend="stable",
        period_start=now - timedelta(hours=24),
        period_end=now,
        calculated_at=now,
    )
    db.add_all([region_score, sector_score])

    alert = Alert(
        alert_type="region_risk",
        severity="high",
        title="High risk: Japan (score 65)",
        description="Region Japan composite score reached 65.0",
        region="Japan",
        score_value=65.0,
        threshold_value=60.0,
        is_read=False,
        created_at=now,
    )
    db.add(alert)

    collector = CollectorStatus(
        collector_name="usgs",
        last_run_at=now,
        last_success_at=now,
        last_error=None,
        signals_collected=10,
        status="ok",
    )
    db.add(collector)

    await db.commit()
    return db


# ── Signal endpoints ───────────────────────────────────────────────────────


class TestSignalsAPI:
    @pytest.mark.asyncio
    async def test_list_signals_empty(self, client: AsyncClient):
        resp = await client.get("/api/signals")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_signals_with_data(self, client: AsyncClient, seeded_db):
        resp = await client.get("/api/signals")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_filter_signals_by_source(self, client: AsyncClient, seeded_db):
        resp = await client.get("/api/signals?source=usgs")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["source"] == "usgs"

    @pytest.mark.asyncio
    async def test_get_signal_detail(self, client: AsyncClient, seeded_db):
        list_resp = await client.get("/api/signals")
        signal_id = list_resp.json()[0]["id"]
        resp = await client.get(f"/api/signals/{signal_id}")
        assert resp.status_code == 200
        assert "raw_json" in resp.json()

    @pytest.mark.asyncio
    async def test_get_signal_not_found(self, client: AsyncClient):
        resp = await client.get("/api/signals/9999")
        assert resp.status_code == 404


# ── Score endpoints ────────────────────────────────────────────────────────


class TestScoresAPI:
    @pytest.mark.asyncio
    async def test_region_scores_empty(self, client: AsyncClient):
        resp = await client.get("/api/scores/regions")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_region_scores_with_data(self, client: AsyncClient, seeded_db):
        resp = await client.get("/api/scores/regions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["region"] == "Japan"
        assert data[0]["score"] == 65.0

    @pytest.mark.asyncio
    async def test_sector_scores_with_data(self, client: AsyncClient, seeded_db):
        resp = await client.get("/api/scores/sectors")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["sector"] == "energy"


# ── Alert endpoints ────────────────────────────────────────────────────────


class TestAlertsAPI:
    @pytest.mark.asyncio
    async def test_list_alerts_empty(self, client: AsyncClient):
        resp = await client.get("/api/alerts")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_alerts_with_data(self, client: AsyncClient, seeded_db):
        resp = await client.get("/api/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["severity"] == "high"

    @pytest.mark.asyncio
    async def test_filter_alerts_by_severity(self, client: AsyncClient, seeded_db):
        resp = await client.get("/api/alerts?severity=critical")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_mark_alert_read(self, client: AsyncClient, seeded_db):
        list_resp = await client.get("/api/alerts")
        alert_id = list_resp.json()[0]["id"]

        resp = await client.patch(f"/api/alerts/{alert_id}/read")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        verify = await client.get("/api/alerts")
        assert verify.json()[0]["is_read"] is True

    @pytest.mark.asyncio
    async def test_mark_alert_not_found(self, client: AsyncClient):
        resp = await client.patch("/api/alerts/9999/read")
        assert resp.status_code == 404


# ── Status endpoint ────────────────────────────────────────────────────────


class TestStatusAPI:
    @pytest.mark.asyncio
    async def test_collector_status_empty(self, client: AsyncClient):
        resp = await client.get("/api/status")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_collector_status_with_data(self, client: AsyncClient, seeded_db):
        resp = await client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["collector_name"] == "usgs"
        assert data[0]["status"] == "ok"


# ── Overview endpoint ──────────────────────────────────────────────────────


class TestOverviewAPI:
    @pytest.mark.asyncio
    async def test_overview_empty(self, client: AsyncClient):
        resp = await client.get("/api/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_signals_24h"] == 0
        assert data["active_alerts"] == 0

    @pytest.mark.asyncio
    async def test_overview_with_data(self, client: AsyncClient, seeded_db):
        resp = await client.get("/api/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_signals_24h"] == 3
        assert data["active_alerts"] == 1
        assert len(data["top_regions"]) == 1
        assert len(data["top_sectors"]) == 1
        assert len(data["collectors"]) == 1
