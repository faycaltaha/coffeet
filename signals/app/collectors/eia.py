"""
EIA collector — energy prices (oil, gas, gasoline).
API: https://api.eia.gov/v2/petroleum/pri/spt/data/
Requires free API key from eia.gov.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from ..config import EIA_API_KEY
from .base import BaseCollector

EIA_API = "https://api.eia.gov/v2/petroleum/pri/spt/data/"

EIA_PRODUCTS: list[dict[str, str]] = [
    {"code": "EPCBRENT", "name": "Brent Crude Oil", "unit": "USD/barrel"},
    {"code": "EPCWTI", "name": "WTI Crude Oil", "unit": "USD/barrel"},
    {"code": "EPJK", "name": "Kerosene-Type Jet Fuel", "unit": "USD/barrel"},
    {"code": "EPMRU", "name": "Regular Gasoline", "unit": "USD/gallon"},
]


def _price_change_severity(current: float, previous: float) -> float:
    """Severity based on day-over-day percentage change."""
    if previous == 0:
        return 0.1
    pct = abs(current - previous) / previous
    if pct >= 0.10:
        return 1.0
    if pct >= 0.05:
        return 0.8
    if pct >= 0.03:
        return 0.6
    if pct >= 0.01:
        return 0.3
    return 0.1


class EIACollector(BaseCollector):
    name = "eia"
    category = "energy"
    interval_minutes = 240

    async def collect(self) -> list[dict]:
        if not EIA_API_KEY:
            return []

        signals = []
        async with httpx.AsyncClient(timeout=30) as client:
            for product in EIA_PRODUCTS:
                params = {
                    "api_key": EIA_API_KEY,
                    "frequency": "daily",
                    "data[0]": "value",
                    "facets[product][]": product["code"],
                    "sort[0][column]": "period",
                    "sort[0][direction]": "desc",
                    "length": "5",
                }

                try:
                    resp = await client.get(EIA_API, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPError:
                    continue

                rows = data.get("response", {}).get("data", [])
                if not rows:
                    continue

                latest = rows[0]
                current_val = float(latest.get("value", 0))
                period = latest.get("period", "")

                try:
                    signal_time = datetime.strptime(
                        period, "%Y-%m-%d"
                    ).replace(tzinfo=timezone.utc)
                except ValueError:
                    signal_time = datetime.now(timezone.utc)

                previous_val = (
                    float(rows[1]["value"]) if len(rows) > 1 else current_val
                )
                severity = _price_change_severity(current_val, previous_val)
                direction = "up" if current_val > previous_val else "down"
                pct = (
                    ((current_val - previous_val) / previous_val * 100)
                    if previous_val
                    else 0
                )

                signals.append({
                    "title": (
                        f"{product['name']}: ${current_val:.2f} "
                        f"({direction} {abs(pct):.1f}%)"
                    ),
                    "description": (
                        f"Previous: ${previous_val:.2f}. "
                        f"Change: {pct:+.1f}%"
                    ),
                    "region": None,
                    "sector": "energy",
                    "severity": severity,
                    "raw_value": current_val,
                    "raw_unit": product["unit"],
                    "raw_json": {
                        "product": product["code"],
                        "current": current_val,
                        "previous": previous_val,
                        "pct_change": round(pct, 2),
                    },
                    "source_url": "https://www.eia.gov/petroleum/",
                    "signal_time": signal_time,
                })

        return signals
