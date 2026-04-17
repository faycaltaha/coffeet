"""
Backfill historical signal data from FRED and Yahoo Finance (2015-present).

Usage:
    cd signals/
    python -m research.backfill_historical

Requires: FRED_API_KEY in .env for FRED data. yfinance for market data.
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import and_, select

from app.config import FRED_API_KEY, YFINANCE_TICKERS
from app.database import SessionLocal, init_db
from app.models import Signal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UTC = timezone.utc
FRED_API = "https://api.stlouisfed.org/fred/series/observations"

FRED_SERIES = [
    {"id": "T10Y2Y", "name": "Yield Curve Spread (10Y-2Y)", "unit": "percent", "sector": "finance"},
    {"id": "DGS10", "name": "10-Year Treasury Yield", "unit": "percent", "sector": "finance"},
    {"id": "UNRATE", "name": "Unemployment Rate", "unit": "percent", "sector": "finance"},
    {"id": "CPIAUCSL", "name": "Consumer Price Index", "unit": "index", "sector": "finance"},
    {"id": "DTWEXBGS", "name": "Trade-Weighted Dollar Index", "unit": "index", "sector": "finance"},
]


def _compute_severity(values: list[float]) -> float:
    if len(values) < 2:
        return 0.1
    avg = sum(values) / len(values)
    if avg == 0:
        return 0.1
    latest = values[-1]
    pct_change = abs(latest - avg) / abs(avg)
    if pct_change >= 0.10:
        return 1.0
    if pct_change >= 0.05:
        return 0.7
    if pct_change >= 0.02:
        return 0.4
    return 0.1


def _price_severity(pct_1d: float, pct_5d: float) -> float:
    max_pct = max(abs(pct_1d), abs(pct_5d))
    if max_pct >= 0.08:
        return 1.0
    if max_pct >= 0.05:
        return 0.8
    if max_pct >= 0.03:
        return 0.6
    if max_pct >= 0.01:
        return 0.3
    return 0.1


async def backfill_fred() -> int:
    if not FRED_API_KEY:
        logger.warning("FRED_API_KEY not set — skipping FRED backfill")
        return 0

    added = 0
    async with httpx.AsyncClient(timeout=60) as client:
        for series in FRED_SERIES:
            logger.info("FRED: fetching %s (%s)...", series["id"], series["name"])
            params = {
                "series_id": series["id"],
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "observation_start": "2015-01-01",
                "sort_order": "asc",
                "limit": "100000",
            }
            try:
                resp = await client.get(FRED_API, params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as e:
                logger.error("FRED %s fetch failed: %s", series["id"], e)
                continue

            observations = [o for o in data.get("observations", []) if o.get("value", ".") != "."]
            if not observations:
                continue

            async with SessionLocal() as session:
                existing = await session.execute(
                    select(Signal.signal_time).where(
                        and_(Signal.source == "fred", Signal.is_backfill == True)
                    ).where(Signal.title.like(f"{series['name']}:%"))
                )
                existing_times = {row[0] for row in existing.all()}

                batch = []
                values_window: list[float] = []
                for obs in observations:
                    val = float(obs["value"])
                    values_window.append(val)
                    if len(values_window) > 30:
                        values_window = values_window[-30:]

                    try:
                        signal_time = datetime.strptime(obs["date"], "%Y-%m-%d").replace(tzinfo=UTC)
                    except ValueError:
                        continue

                    if signal_time in existing_times:
                        continue

                    severity = _compute_severity(values_window)
                    batch.append(Signal(
                        source="fred",
                        category="economic",
                        title=f"{series['name']}: {val:.2f}",
                        description=f"Historical {series['id']} observation: {val}",
                        region="United States",
                        sector=series["sector"],
                        severity=severity,
                        raw_value=val,
                        raw_unit=series["unit"],
                        raw_json=json.dumps({
                            "series_id": series["id"],
                            "date": obs["date"],
                            "value": val,
                        }),
                        source_url=f"https://fred.stlouisfed.org/series/{series['id']}",
                        signal_time=signal_time,
                        is_backfill=True,
                    ))

                if batch:
                    session.add_all(batch)
                    await session.commit()
                    added += len(batch)
                    logger.info("FRED %s: added %d historical observations", series["id"], len(batch))

    return added


async def backfill_yfinance() -> int:
    try:
        import yfinance as yf
    except ImportError:
        logger.warning("yfinance not installed — skipping market data backfill")
        return 0

    added = 0
    for ticker_symbol, info in YFINANCE_TICKERS.items():
        logger.info("YFinance: fetching %s (%s)...", ticker_symbol, info["name"])
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(start="2015-01-01", end="2026-04-17")
        except Exception as e:
            logger.error("YFinance %s failed: %s", ticker_symbol, e)
            continue

        if hist.empty:
            continue

        async with SessionLocal() as session:
            existing = await session.execute(
                select(Signal.signal_time).where(
                    and_(
                        Signal.source == "yfinance",
                        Signal.is_backfill == True,
                        Signal.title.like(f"{info['name']}:%"),
                    )
                )
            )
            existing_times = {row[0] for row in existing.all()}

            batch = []
            closes = list(hist["Close"])
            for i, (date_idx, row) in enumerate(hist.iterrows()):
                signal_time = date_idx.to_pydatetime()
                if signal_time.tzinfo is None:
                    signal_time = signal_time.replace(tzinfo=UTC)

                if signal_time in existing_times:
                    continue

                close_val = float(row["Close"])
                pct_1d = abs(close_val / closes[i - 1] - 1) if i > 0 and closes[i - 1] != 0 else 0
                window = closes[max(0, i - 5):i + 1]
                pct_5d = abs(close_val / window[0] - 1) if len(window) > 1 and window[0] != 0 else 0
                severity = _price_severity(pct_1d, pct_5d)

                batch.append(Signal(
                    source="yfinance",
                    category="financial",
                    title=f"{info['name']}: {close_val:.2f}",
                    description=f"Historical {ticker_symbol} close: {close_val:.2f}",
                    region=None,
                    sector=info["sector"],
                    severity=severity,
                    raw_value=close_val,
                    raw_unit="price",
                    raw_json=json.dumps({
                        "ticker": ticker_symbol,
                        "date": signal_time.strftime("%Y-%m-%d"),
                        "close": close_val,
                        "volume": int(row.get("Volume", 0)),
                    }),
                    signal_time=signal_time,
                    is_backfill=True,
                ))

            if batch:
                session.add_all(batch)
                await session.commit()
                added += len(batch)
                logger.info("YFinance %s: added %d historical data points", ticker_symbol, len(batch))

    return added


async def main() -> None:
    await init_db()
    fred_count = await backfill_fred()
    yf_count = await backfill_yfinance()
    print(f"Backfill complete: {fred_count} FRED + {yf_count} YFinance = {fred_count + yf_count} total signals")


if __name__ == "__main__":
    asyncio.run(main())
