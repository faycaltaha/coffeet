"""
ReliefWeb collector — UN humanitarian crisis reports and disaster alerts.
API: https://api.reliefweb.int/v1/reports
No API key required.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from .base import BaseCollector

RELIEFWEB_API = "https://api.reliefweb.int/v1/reports"


def _status_to_severity(status: str, disaster_type: str) -> float:
    """Map ReliefWeb report status and disaster type to severity."""
    status_lower = status.lower()
    if "alert" in status_lower or "emergency" in status_lower:
        return 0.9
    if "ongoing" in status_lower:
        return 0.7

    dtype = disaster_type.lower()
    if any(t in dtype for t in ("earthquake", "tsunami", "cyclone", "flood")):
        return 0.7
    if any(t in dtype for t in ("drought", "epidemic", "conflict")):
        return 0.6
    if any(t in dtype for t in ("volcano", "storm", "fire")):
        return 0.5
    return 0.3


def _extract_country(source: dict) -> str | None:
    """Extract primary country from ReliefWeb report."""
    countries = source.get("country", [])
    if countries and isinstance(countries, list):
        return countries[0].get("name")
    return None


class ReliefWebCollector(BaseCollector):
    name = "reliefweb"
    category = "humanitarian"
    interval_minutes = 60

    async def collect(self) -> list[dict]:
        params = {
            "appname": "coffeet-signal-monitor",
            "limit": "30",
            "sort[]": "date:desc",
            "fields[include][]": [
                "title", "date.created", "status", "country.name",
                "disaster_type.name", "url",
            ],
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(RELIEFWEB_API, params=params)
            resp.raise_for_status()
            data = resp.json()

        signals = []
        for item in data.get("data", []):
            fields = item.get("fields", {})
            title = fields.get("title", "").strip()
            if not title:
                continue

            date_str = fields.get("date", {}).get("created", "")
            try:
                signal_time = datetime.fromisoformat(
                    date_str.replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                signal_time = datetime.now(timezone.utc)

            status = fields.get("status", "")
            disaster_types = fields.get("disaster_type", [])
            dtype_name = disaster_types[0].get("name", "") if disaster_types else ""
            country = _extract_country(fields)

            signals.append({
                "title": title[:500],
                "description": f"Status: {status}. Type: {dtype_name}",
                "region": country,
                "sector": None,
                "severity": _status_to_severity(status, dtype_name),
                "raw_json": {
                    "status": status,
                    "disaster_type": dtype_name,
                    "country": country,
                },
                "source_url": fields.get("url"),
                "signal_time": signal_time,
            })

        return signals
