"""
ACLED collector — armed conflict and protest events.
API: https://api.acleddata.com/acled/read
Requires free academic API key + email.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from ..config import ACLED_API_KEY, ACLED_EMAIL
from .base import BaseCollector

ACLED_API = "https://api.acleddata.com/acled/read"

EVENT_SEVERITY: dict[str, float] = {
    "battles": 0.9,
    "explosions/remote violence": 0.9,
    "violence against civilians": 0.8,
    "riots": 0.7,
    "protests": 0.5,
    "strategic developments": 0.4,
}


def _event_severity(event_type: str, fatalities: int) -> float:
    base = EVENT_SEVERITY.get(event_type.lower(), 0.3)
    if fatalities >= 100:
        return 1.0
    if fatalities >= 50:
        return max(base, 0.9)
    if fatalities >= 10:
        return max(base, 0.7)
    if fatalities >= 1:
        return max(base, base + 0.1)
    return base


def _extract_region(country: str) -> str:
    return country.strip() if country else "Unknown"


class ACLEDCollector(BaseCollector):
    name = "acled"
    category = "conflict"
    interval_minutes = 360

    async def collect(self) -> list[dict]:
        if not ACLED_API_KEY or not ACLED_EMAIL:
            return []

        params = {
            "key": ACLED_API_KEY,
            "email": ACLED_EMAIL,
            "limit": "50",
            "fields": "event_id_cnty|event_date|event_type|sub_event_type|country|admin1|location|fatalities|notes|source_url",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(ACLED_API, params=params)
            resp.raise_for_status()
            data = resp.json()

        signals = []
        for event in data.get("data", []):
            event_type = event.get("event_type", "")
            notes = event.get("notes", "")
            country = event.get("country", "")
            location = event.get("location", "")
            fatalities = int(event.get("fatalities", 0) or 0)

            date_str = event.get("event_date", "")
            try:
                signal_time = datetime.strptime(
                    date_str, "%Y-%m-%d"
                ).replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                signal_time = datetime.now(timezone.utc)

            title = f"{event_type}: {location}, {country}"
            if fatalities > 0:
                title += f" ({fatalities} fatalities)"

            signals.append({
                "title": title[:500],
                "description": notes[:500] if notes else f"{event_type} in {location}",
                "region": _extract_region(country),
                "sector": None,
                "severity": _event_severity(event_type, fatalities),
                "raw_json": {
                    "event_id": event.get("event_id_cnty"),
                    "event_type": event_type,
                    "sub_event_type": event.get("sub_event_type"),
                    "fatalities": fatalities,
                    "admin1": event.get("admin1"),
                },
                "source_url": event.get("source_url"),
                "signal_time": signal_time,
            })

        return signals
