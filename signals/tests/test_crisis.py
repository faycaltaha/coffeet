"""
Tests for Crisis, SignalPattern, CrisisSignalLink models and API endpoints.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Crisis, CrisisSignalLink, Signal, SignalPattern

UTC = timezone.utc
NOW = datetime.now(UTC)


@pytest_asyncio.fixture
async def seeded_crises(db: AsyncSession):
    crises = [
        Crisis(
            name="2020 COVID Supply Chain",
            crisis_type="supply_chain",
            region="Global",
            sector="supply_chain",
            impact_description="Pandemic disrupted global logistics",
            start_date=datetime(2020, 1, 23, tzinfo=UTC),
            peak_date=datetime(2020, 4, 15, tzinfo=UTC),
            end_date=datetime(2021, 12, 31, tzinfo=UTC),
            impact_score=10.0,
        ),
        Crisis(
            name="2022 Russia-Ukraine War",
            crisis_type="geopolitical",
            region="Europe",
            sector="energy",
            impact_description="Russian invasion caused energy crisis",
            start_date=datetime(2022, 2, 24, tzinfo=UTC),
            peak_date=datetime(2022, 9, 30, tzinfo=UTC),
            end_date=None,
            impact_score=9.5,
        ),
        Crisis(
            name="2022 Sri Lanka Collapse",
            crisis_type="financial",
            region="South Asia",
            sector="finance",
            impact_description="Sovereign default and economic collapse",
            start_date=datetime(2022, 3, 1, tzinfo=UTC),
            peak_date=datetime(2022, 7, 9, tzinfo=UTC),
            end_date=datetime(2022, 12, 31, tzinfo=UTC),
            impact_score=7.0,
        ),
    ]
    db.add_all(crises)
    await db.commit()

    pattern = SignalPattern(
        name="Yield curve inversion",
        description="10Y-2Y spread turns negative",
        pattern_type="precursor",
        signal_sources_json='["fred"]',
        detection_rules_json='{"threshold": -0.1}',
    )
    db.add(pattern)
    await db.commit()

    link = CrisisSignalLink(
        crisis_id=crises[0].id,
        signal_pattern_id=pattern.id,
        lead_time_days=45,
        correlation_strength=0.72,
        notes="Yield curve inverted 45 days before COVID impact",
    )
    db.add(link)
    await db.commit()
    return db


class TestCrisisModel:
    @pytest.mark.asyncio
    async def test_create_crisis(self, db: AsyncSession):
        crisis = Crisis(
            name="Test Crisis",
            crisis_type="financial",
            region="Global",
            sector="finance",
            impact_description="A test crisis",
            start_date=datetime(2020, 1, 1, tzinfo=UTC),
            impact_score=8.0,
        )
        db.add(crisis)
        await db.commit()
        assert crisis.id is not None
        assert crisis.created_at is not None

    @pytest.mark.asyncio
    async def test_crisis_nullable_fields(self, db: AsyncSession):
        crisis = Crisis(
            name="Minimal Crisis",
            crisis_type="natural_disaster",
            region="Pacific",
            sector=None,
            impact_description="Minimal fields",
            start_date=datetime(2023, 1, 1, tzinfo=UTC),
            peak_date=None,
            end_date=None,
            impact_score=5.0,
        )
        db.add(crisis)
        await db.commit()
        assert crisis.sector is None
        assert crisis.peak_date is None
        assert crisis.end_date is None


class TestSignalPatternModel:
    @pytest.mark.asyncio
    async def test_create_pattern(self, db: AsyncSession):
        pattern = SignalPattern(
            name="Oil price spike",
            description="Crude oil exceeds 2-sigma band",
            pattern_type="coincident",
            signal_sources_json='["yfinance", "eia"]',
            detection_rules_json='{"sigma": 2}',
        )
        db.add(pattern)
        await db.commit()
        assert pattern.id is not None


class TestCrisisSignalLinkModel:
    @pytest.mark.asyncio
    async def test_create_link(self, db: AsyncSession):
        crisis = Crisis(
            name="Link Test Crisis",
            crisis_type="energy",
            region="Middle East",
            impact_description="Test",
            start_date=datetime(2022, 1, 1, tzinfo=UTC),
            impact_score=6.0,
        )
        pattern = SignalPattern(
            name="Link Test Pattern",
            pattern_type="precursor",
        )
        db.add_all([crisis, pattern])
        await db.commit()

        link = CrisisSignalLink(
            crisis_id=crisis.id,
            signal_pattern_id=pattern.id,
            lead_time_days=30,
            correlation_strength=0.65,
            notes="Test link",
        )
        db.add(link)
        await db.commit()
        assert link.id is not None
        assert link.crisis_id == crisis.id

    @pytest.mark.asyncio
    async def test_link_without_pattern(self, db: AsyncSession):
        crisis = Crisis(
            name="No Pattern Crisis",
            crisis_type="financial",
            region="Global",
            impact_description="Test",
            start_date=datetime(2023, 1, 1, tzinfo=UTC),
            impact_score=5.0,
        )
        db.add(crisis)
        await db.commit()

        link = CrisisSignalLink(
            crisis_id=crisis.id,
            signal_pattern_id=None,
            lead_time_days=10,
            notes="Manual observation",
        )
        db.add(link)
        await db.commit()
        assert link.signal_pattern_id is None


class TestIsBackfillFlag:
    @pytest.mark.asyncio
    async def test_default_is_false(self, db: AsyncSession):
        signal = Signal(
            source="test",
            category="test",
            title="Normal signal",
            severity=0.5,
            signal_time=NOW,
        )
        db.add(signal)
        await db.commit()
        assert signal.is_backfill is False

    @pytest.mark.asyncio
    async def test_explicit_backfill(self, db: AsyncSession):
        signal = Signal(
            source="fred",
            category="economic",
            title="Historical data point",
            severity=0.3,
            signal_time=datetime(2019, 1, 1, tzinfo=UTC),
            is_backfill=True,
        )
        db.add(signal)
        await db.commit()
        assert signal.is_backfill is True


class TestCrisesAPI:
    @pytest.mark.asyncio
    async def test_list_crises_empty(self, client: AsyncClient):
        resp = await client.get("/api/crises")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_crises_with_data(self, client: AsyncClient, seeded_crises):
        resp = await client.get("/api/crises")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_filter_crises_by_type(self, client: AsyncClient, seeded_crises):
        resp = await client.get("/api/crises?crisis_type=financial")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["crisis_type"] == "financial"

    @pytest.mark.asyncio
    async def test_filter_crises_by_region(self, client: AsyncClient, seeded_crises):
        resp = await client.get("/api/crises?region=Europe")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["region"] == "Europe"

    @pytest.mark.asyncio
    async def test_get_crisis_detail(self, client: AsyncClient, seeded_crises):
        list_resp = await client.get("/api/crises")
        crisis_id = list_resp.json()[0]["id"]
        resp = await client.get(f"/api/crises/{crisis_id}")
        assert resp.status_code == 200
        detail = resp.json()
        assert "links" in detail

    @pytest.mark.asyncio
    async def test_get_crisis_not_found(self, client: AsyncClient):
        resp = await client.get("/api/crises/9999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_crisis_detail_includes_links(self, client: AsyncClient, seeded_crises):
        list_resp = await client.get("/api/crises")
        crises = list_resp.json()
        covid = next(c for c in crises if "COVID" in c["name"])
        resp = await client.get(f"/api/crises/{covid['id']}")
        assert resp.status_code == 200
        detail = resp.json()
        assert len(detail["links"]) == 1
        assert detail["links"][0]["lead_time_days"] == 45


class TestSignalPatternsAPI:
    @pytest.mark.asyncio
    async def test_list_patterns_empty(self, client: AsyncClient):
        resp = await client.get("/api/signal-patterns")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_patterns_with_data(self, client: AsyncClient, seeded_crises):
        resp = await client.get("/api/signal-patterns")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Yield curve inversion"

    @pytest.mark.asyncio
    async def test_get_pattern_detail(self, client: AsyncClient, seeded_crises):
        list_resp = await client.get("/api/signal-patterns")
        pattern_id = list_resp.json()[0]["id"]
        resp = await client.get(f"/api/signal-patterns/{pattern_id}")
        assert resp.status_code == 200
        assert resp.json()["pattern_type"] == "precursor"

    @pytest.mark.asyncio
    async def test_get_pattern_not_found(self, client: AsyncClient):
        resp = await client.get("/api/signal-patterns/9999")
        assert resp.status_code == 404
