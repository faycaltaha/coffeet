"""
Scheduler job functions — bridge between APScheduler and collectors/scoring.
"""
from __future__ import annotations

import logging

from .alerts import evaluate_alerts
from .collectors.eia import EIACollector
from .collectors.fred import FREDCollector
from .collectors.gdelt import GDELTCollector
from .collectors.rss_news import RSSCollector
from .collectors.usgs import USGSCollector
from .collectors.yfinance_collector import YFinanceCollector
from .database import SessionLocal
from .scoring import compute_scores

logger = logging.getLogger(__name__)

COLLECTORS = {
    "usgs": USGSCollector,
    "gdelt": GDELTCollector,
    "fred": FREDCollector,
    "eia": EIACollector,
    "rss": RSSCollector,
    "yfinance": YFinanceCollector,
}


async def run_collector(name: str) -> None:
    """Run a single collector by name."""
    collector_cls = COLLECTORS.get(name)
    if not collector_cls:
        logger.error("Unknown collector: %s", name)
        return

    collector = collector_cls()
    try:
        async with SessionLocal() as db:
            count = await collector.run(db)
            logger.info("Collector %s finished: %d signals", name, count)
    except Exception as exc:
        logger.error("Collector %s failed: %s", name, exc)


async def run_scoring_and_alerts() -> None:
    """Run scoring engine then evaluate alerts."""
    try:
        async with SessionLocal() as db:
            await compute_scores(db)
            alert_count = await evaluate_alerts(db)
            logger.info("Scoring complete, %d alerts created", alert_count)
    except Exception as exc:
        logger.error("Scoring/alerts failed: %s", exc)
