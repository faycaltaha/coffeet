"""
FRED collector — Federal Reserve economic indicators.
API: https://api.stlouisfed.org/fred/series/observations
Requires free API key from fred.stlouisfed.org.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from ..config import FRED_API_KEY
from .base import BaseCollector

FRED_API = "https://api.stlouisfed.org/fred/series/observations"

FRED_SERIES: list[dict[str, str]] = [
    {
        "id": "T10Y2Y",
        "name": "Yield Curve Spread (10Y-2Y)",
        "unit": "percent",
        "sector": "finance",
    },
    {
        "id": "DGS10",
        "name": "10-Year Treasury Yield",
        "unit": "percent",
        "sector": "finance",
    },
    {
        "id": "UNRATE",
        "name": "Unemployment Rate",
        "unit": "percent",
        "sector": "finance",
    },
    {
        "id": "CPIAUCSL",
        "name": "Consumer Price Index",
        "unit": "index",
        "sector": "finance",
    },
    {
        "id": "DTWEXBGS",
        "name": "Trade-Weighted Dollar Index",
        "unit": "index",
        "sector": "finance",
    },
]


def _compute_severity(values: list[float]) -> float:
    """Severity based on recent deviation from 30-observation average."""
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


class FREDCollector(BaseCollector):
    name = "fred"
    category = "economic"
    interval_minutes = 360

    async def collect(self) -> list[dict]:
        if not FRED_API_KEY:
            return []

        signals = []
        async with httpx.AsyncClient(timeout=30) as client:
            for series in FRED_SERIES:
                params = {
                    "series_id": series["id"],
                    "api_key": FRED_API_KEY,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": "30",
                }

                try:
                    resp = await client.get(FRED_API, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPError:
                    continue

                observations = data.get("observations", [])
                valid_obs = [
                    o for o in observations if o.get("value", ".") != "."
                ]
                if not valid_obs:
                    continue

                values = [float(o["value"]) for o in valid_obs]
                latest = valid_obs[0]
                latest_value = float(latest["value"])

                date_str = latest.get("date", "")
                try:
                    signal_time = datetime.strptime(
                        date_str, "%Y-%m-%d"
                    ).replace(tzinfo=timezone.utc)
                except ValueError:
                    signal_time = datetime.now(timezone.utc)

                severity = _compute_severity(list(reversed(values)))

                signals.append({
                    "title": f"{series['name']}: {latest_value:.2f}",
                    "description": (
                        f"Latest {series['id']} observation: {latest_value}. "
                        f"30-obs avg: {sum(values)/len(values):.2f}"
                    ),
                    "region": "United States",
                    "sector": series["sector"],
                    "severity": severity,
                    "raw_value": latest_value,
                    "raw_unit": series["unit"],
                    "raw_json": {
                        "series_id": series["id"],
                        "latest_date": date_str,
                        "latest_value": latest_value,
                        "observation_count": len(values),
                    },
                    "source_url": (
                        f"https://fred.stlouisfed.org/series/{series['id']}"
                    ),
                    "signal_time": signal_time,
                })

        return signals
