"""
Abstract base collector with template-method pattern for collect → dedup → store.
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import CollectorStatus, Signal

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """All collectors extend this. Implement collect() to return raw dicts."""

    name: str = ""
    category: str = ""
    interval_minutes: int = 60

    @abstractmethod
    async def collect(self) -> list[dict]:
        """
        Fetch data from external API and return normalized signal dicts.

        Each dict must have at minimum:
            title, severity (0-1), signal_time (datetime),
        and optionally:
            description, region, sector, raw_value, raw_unit,
            raw_json, source_url
        """
        ...

    async def run(self, db: AsyncSession) -> int:
        """Template method: collect, dedup, store, update status."""
        now = datetime.now(timezone.utc)
        collected_count = 0

        try:
            raw_signals = await self.collect()
            if not raw_signals:
                await self._update_status(db, now, error=None, count=0)
                return 0

            cutoff = now - timedelta(hours=24)
            result = await db.execute(
                select(Signal.title, Signal.signal_time).where(
                    and_(
                        Signal.source == self.name,
                        Signal.collected_at >= cutoff,
                    )
                )
            )
            existing = {(row.title, row.signal_time) for row in result.all()}

            new_signals = []
            for raw in raw_signals:
                key = (raw["title"], raw["signal_time"])
                if key not in existing:
                    new_signals.append(
                        Signal(
                            source=self.name,
                            category=self.category,
                            title=raw["title"],
                            description=raw.get("description"),
                            region=raw.get("region"),
                            sector=raw.get("sector"),
                            severity=max(0.0, min(1.0, raw["severity"])),
                            raw_value=raw.get("raw_value"),
                            raw_unit=raw.get("raw_unit"),
                            raw_json=json.dumps(raw.get("raw_json"))
                            if raw.get("raw_json")
                            else None,
                            source_url=raw.get("source_url"),
                            signal_time=raw["signal_time"],
                        )
                    )
                    existing.add(key)

            if new_signals:
                db.add_all(new_signals)
                await db.commit()
            collected_count = len(new_signals)

            await self._update_status(db, now, error=None, count=collected_count)
            logger.info(
                "%s: collected %d new signals (%d total fetched)",
                self.name,
                collected_count,
                len(raw_signals),
            )

        except Exception as exc:
            logger.error("%s: collection failed: %s", self.name, exc)
            await self._update_status(db, now, error=str(exc), count=0)
            raise

        return collected_count

    async def _update_status(
        self,
        db: AsyncSession,
        now: datetime,
        error: str | None,
        count: int,
    ) -> None:
        result = await db.execute(
            select(CollectorStatus).where(
                CollectorStatus.collector_name == self.name
            )
        )
        status = result.scalar_one_or_none()

        if status is None:
            status = CollectorStatus(collector_name=self.name)
            db.add(status)

        status.last_run_at = now
        if error:
            status.last_error = error
            status.status = "error"
        else:
            status.last_success_at = now
            status.last_error = None
            status.status = "ok"
            status.signals_collected = (status.signals_collected or 0) + count

        await db.commit()
