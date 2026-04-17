"""
Shared pytest fixtures — async SQLite database for test isolation.
"""
from __future__ import annotations

import asyncio
import sys
import types
from datetime import datetime, timezone

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

TEST_ENGINE = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestSession = async_sessionmaker(TEST_ENGINE, expire_on_commit=False)


async def override_get_db():
    async with TestSession() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


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


def make_signal(
    source: str = "test",
    category: str = "geopolitical",
    title: str = "Test signal",
    severity: float = 0.5,
    region: str | None = "TestRegion",
    sector: str | None = "energy",
    signal_time: datetime | None = None,
) -> Signal:
    """Helper to create a Signal instance with defaults."""
    return Signal(
        source=source,
        category=category,
        title=title,
        severity=severity,
        region=region,
        sector=sector,
        signal_time=signal_time or datetime.now(timezone.utc),
    )
