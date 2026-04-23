"""
Scheduler job functions — bridge between APScheduler and collectors/scoring.
"""
from __future__ import annotations

import logging

from .alerts import evaluate_alerts
from .correlation import compute_correlations
from .risk_engine import compute_risk_assessments
from .collectors.acled import ACLEDCollector
from .collectors.ais import AISCollector
from .collectors.comtrade import ComtradeCollector
from .collectors.eia import EIACollector
from .collectors.fred import FREDCollector
from .collectors.gdelt import GDELTCollector
from .collectors.imf import IMFCollector
from .collectors.noaa import NOAACollector
from .collectors.opensanctions import OpenSanctionsCollector
from .collectors.reliefweb import ReliefWebCollector
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
    "noaa": NOAACollector,
    "reliefweb": ReliefWebCollector,
    "opensanctions": OpenSanctionsCollector,
    "comtrade": ComtradeCollector,
    "imf": IMFCollector,
    "acled": ACLEDCollector,
    "ais": AISCollector,
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


async def run_correlation_analysis() -> None:
    """Run correlation analysis over all (crisis, signal_category) pairs."""
    try:
        async with SessionLocal() as db:
            count = await compute_correlations(db)
            logger.info("Correlation analysis complete: %d results stored", count)
    except Exception as exc:
        logger.error("Correlation analysis failed: %s", exc)

async def run_risk_assessment() -> None:
    """Run v2 risk assessment pipeline."""
    try:
        async with SessionLocal() as db:
            count = await compute_risk_assessments(db)
            logger.info("Risk assessment complete: %d assessments stored", count)
    except Exception as exc:
        logger.error("Risk assessment failed: %s", exc)

