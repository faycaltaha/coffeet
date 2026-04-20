"""
UN Comtrade collector — international trade flow anomalies.
API: https://comtradeapi.un.org/data/v1/get/C/A/HS
Requires free API key (subscription key).
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from ..config import COMTRADE_API_KEY
from .base import BaseCollector

COMTRADE_API = "https://comtradeapi.un.org/data/v1/get/C/A/HS"

TRACKED_COMMODITIES: list[dict[str, str]] = [
    {"code": "0901", "name": "Coffee", "sector": "agriculture"},
    {"code": "2709", "name": "Crude petroleum", "sector": "energy"},
    {"code": "1001", "name": "Wheat", "sector": "agriculture"},
    {"code": "2711", "name": "Natural gas", "sector": "energy"},
    {"code": "7108", "name": "Gold", "sector": "commodities"},
    {"code": "8542", "name": "Electronic integrated circuits", "sector": "technology"},
]


def _trade_change_severity(current: float, previous: float) -> float:
    if previous == 0:
        return 0.3
    pct = abs(current - previous) / previous
    if pct >= 0.30:
        return 1.0
    if pct >= 0.20:
        return 0.8
    if pct >= 0.10:
        return 0.6
    if pct >= 0.05:
        return 0.4
    return 0.2


class ComtradeCollector(BaseCollector):
    name = "comtrade"
    category = "trade"
    interval_minutes = 720

    async def collect(self) -> list[dict]:
        if not COMTRADE_API_KEY:
            return []

        signals = []
        now = datetime.now(timezone.utc)
        prev_year = now.year - 1

        async with httpx.AsyncClient(timeout=60) as client:
            for commodity in TRACKED_COMMODITIES:
                params = {
                    "cmdCode": commodity["code"],
                    "flowCode": "M",
                    "partnerCode": "0",
                    "reporterCode": "842",
                    "period": str(prev_year),
                    "motCode": "0",
                    "subscription-key": COMTRADE_API_KEY,
                }

                try:
                    resp = await client.get(COMTRADE_API, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPError:
                    continue

                records = data.get("data", [])
                if not records:
                    continue

                latest = records[0]
                trade_value = latest.get("primaryValue", 0)
                prev_value = trade_value
                if len(records) > 1:
                    prev_value = records[1].get("primaryValue", trade_value)

                severity = _trade_change_severity(trade_value, prev_value)

                signals.append({
                    "title": f"Trade flow: {commodity['name']} — ${trade_value:,.0f}",
                    "description": f"US import value for {commodity['name']} (HS {commodity['code']})",
                    "region": "United States",
                    "sector": commodity["sector"],
                    "severity": severity,
                    "raw_value": trade_value,
                    "raw_unit": "USD",
                    "raw_json": {
                        "commodity_code": commodity["code"],
                        "commodity_name": commodity["name"],
                        "trade_value": trade_value,
                        "period": str(prev_year),
                    },
                    "source_url": "https://comtradeplus.un.org/",
                    "signal_time": now,
                })

        return signals
