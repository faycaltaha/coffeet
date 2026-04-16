"""
Yahoo Finance collector — commodities, forex, and VIX.
Uses yfinance library (no API key required).
"""
from __future__ import annotations

from datetime import datetime, timezone

import yfinance as yf

from ..config import YFINANCE_TICKERS
from .base import BaseCollector


def _price_severity(pct_1d: float, pct_5d: float) -> float:
    """Score severity from price movements."""
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


class YFinanceCollector(BaseCollector):
    name = "yfinance"
    category = "financial"
    interval_minutes = 120

    async def collect(self) -> list[dict]:
        signals = []
        now = datetime.now(timezone.utc)

        for ticker_symbol, meta in YFINANCE_TICKERS.items():
            try:
                ticker = yf.Ticker(ticker_symbol)
                hist = ticker.history(period="5d")

                if hist.empty or len(hist) < 2:
                    continue

                current = float(hist["Close"].iloc[-1])
                prev_1d = float(hist["Close"].iloc[-2])
                prev_5d = float(hist["Close"].iloc[0])

                pct_1d = (current - prev_1d) / prev_1d if prev_1d else 0
                pct_5d = (current - prev_5d) / prev_5d if prev_5d else 0

                if ticker_symbol == "^VIX":
                    if current >= 35:
                        severity = 1.0
                    elif current >= 25:
                        severity = 0.7
                    elif current >= 20:
                        severity = 0.4
                    else:
                        severity = 0.1
                else:
                    severity = _price_severity(pct_1d, pct_5d)

                direction_1d = "up" if pct_1d > 0 else "down"

                signals.append({
                    "title": (
                        f"{meta['name']}: {current:.2f} "
                        f"({direction_1d} {abs(pct_1d)*100:.1f}%)"
                    ),
                    "description": (
                        f"1d: {pct_1d*100:+.1f}%, "
                        f"5d: {pct_5d*100:+.1f}%"
                    ),
                    "region": None,
                    "sector": meta["sector"],
                    "severity": severity,
                    "raw_value": current,
                    "raw_unit": "USD",
                    "raw_json": {
                        "ticker": ticker_symbol,
                        "current": current,
                        "prev_1d": prev_1d,
                        "prev_5d": prev_5d,
                        "pct_1d": round(pct_1d * 100, 2),
                        "pct_5d": round(pct_5d * 100, 2),
                    },
                    "source_url": (
                        f"https://finance.yahoo.com/quote/{ticker_symbol}"
                    ),
                    "signal_time": now,
                })

            except Exception:
                continue

        return signals
