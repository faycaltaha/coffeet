"""
Shared pytest fixtures — async SQLite database for test isolation.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models import Alert, CollectorStatus, RegionScore, SectorScore, Signal


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db():
    """Create a fresh in-memory SQLite database for each test."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", echo=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


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
