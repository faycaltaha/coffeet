"""
USGS Earthquake collector — significant earthquakes worldwide.
API: https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson
No API key required.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from .base import BaseCollector

USGS_URL = (
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson"
)


def _magnitude_to_severity(mag: float) -> float:
    """Normalize earthquake magnitude to 0-1 severity."""
    if mag >= 8.0:
        return 1.0
    if mag >= 7.0:
        return 0.9
    if mag >= 6.0:
        return 0.7
    if mag >= 5.0:
        return 0.5
    if mag >= 4.0:
        return 0.3
    return 0.1


def _extract_region(place: str) -> str:
    """Extract country/region from USGS place string like '50km S of Tokyo, Japan'."""
    if "," in place:
        return place.rsplit(",", 1)[-1].strip()
    if " of " in place:
        return place.split(" of ", 1)[-1].strip()
    return place


class USGSCollector(BaseCollector):
    name = "usgs"
    category = "seismic"
    interval_minutes = 60

    async def collect(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(USGS_URL)
            resp.raise_for_status()
            data = resp.json()

        signals = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            mag = props.get("mag")
            if mag is None:
                continue

            epoch_ms = props.get("time", 0)
            signal_time = datetime.fromtimestamp(
                epoch_ms / 1000, tz=timezone.utc
            )

            signals.append({
                "title": props.get("title", f"M{mag} earthquake"),
                "description": props.get("place", ""),
                "region": _extract_region(props.get("place", "")),
                "sector": None,
                "severity": _magnitude_to_severity(mag),
                "raw_value": mag,
                "raw_unit": "magnitude",
                "raw_json": props,
                "source_url": props.get("url"),
                "signal_time": signal_time,
            })

        return signals
