"""
NOAA collector — US weather alerts and extreme weather events.
API: https://api.weather.gov/alerts/active
No API key required.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from .base import BaseCollector

NOAA_ALERTS_API = "https://api.weather.gov/alerts/active"

SEVERITY_MAP = {
    "extreme": 1.0,
    "severe": 0.8,
    "moderate": 0.5,
    "minor": 0.3,
    "unknown": 0.2,
}

SUPPLY_CHAIN_EVENTS = {
    "hurricane", "typhoon", "tropical storm", "blizzard",
    "ice storm", "tornado", "flood", "wildfire",
}


def _alert_severity(severity: str, event: str) -> float:
    """Map NOAA alert severity + event type to 0-1 score."""
    base = SEVERITY_MAP.get(severity.lower(), 0.2)
    if any(term in event.lower() for term in SUPPLY_CHAIN_EVENTS):
        return min(1.0, base + 0.1)
    return base


def _classify_sector(event: str) -> str | None:
    """Classify weather event into affected sector."""
    event_lower = event.lower()
    if any(t in event_lower for t in ("drought", "frost", "freeze", "flood")):
        return "agriculture"
    if any(t in event_lower for t in ("hurricane", "storm", "tornado", "wind")):
        return "supply_chain"
    if any(t in event_lower for t in ("heat", "cold", "winter", "ice")):
        return "energy"
    return None


class NOAACollector(BaseCollector):
    name = "noaa"
    category = "climate"
    interval_minutes = 60

    async def collect(self) -> list[dict]:
        headers = {
            "User-Agent": "coffeet-signal-monitor/1.0",
            "Accept": "application/geo+json",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                NOAA_ALERTS_API,
                headers=headers,
                params={"status": "actual", "limit": 30},
            )
            resp.raise_for_status()
            data = resp.json()

        signals = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            event = props.get("event", "")
            headline = props.get("headline", event)
            if not headline:
                continue

            severity_str = props.get("severity", "Unknown")
            sent = props.get("sent", "")
            try:
                signal_time = datetime.fromisoformat(sent)
            except (ValueError, TypeError):
                signal_time = datetime.now(timezone.utc)

            area = props.get("areaDesc", "")
            region = area.split(";")[0].strip() if area else "United States"

            signals.append({
                "title": headline[:500],
                "description": props.get("description", "")[:500],
                "region": region[:100],
                "sector": _classify_sector(event),
                "severity": _alert_severity(severity_str, event),
                "raw_json": {
                    "event": event,
                    "severity": severity_str,
                    "certainty": props.get("certainty"),
                    "urgency": props.get("urgency"),
                },
                "source_url": props.get("@id"),
                "signal_time": signal_time,
            })

        return signals
