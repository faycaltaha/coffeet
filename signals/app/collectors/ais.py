"""
AIS collector — vessel traffic density at key maritime chokepoints.
API: Finnish Transport Agency Digitraffic AIS (free, no auth).
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from .base import BaseCollector

DIGITRAFFIC_AIS_API = "https://meri.digitraffic.fi/api/ais/v1/locations/latest"

PORT_AREAS: list[dict] = [
    {
        "name": "Baltic Sea (Helsinki)",
        "lat_min": 59.5, "lat_max": 60.5,
        "lon_min": 24.0, "lon_max": 26.0,
        "region": "Northern Europe",
    },
    {
        "name": "Gulf of Finland",
        "lat_min": 59.0, "lat_max": 60.5,
        "lon_min": 26.0, "lon_max": 30.0,
        "region": "Northern Europe",
    },
]

VESSEL_DENSITY_BASELINE = 50


def _density_to_severity(vessel_count: int, baseline: int) -> float:
    if baseline == 0:
        return 0.3
    ratio = vessel_count / baseline
    if ratio >= 3.0:
        return 1.0
    if ratio >= 2.0:
        return 0.8
    if ratio >= 1.5:
        return 0.6
    if ratio >= 1.2:
        return 0.4
    if ratio <= 0.3:
        return 0.7
    if ratio <= 0.5:
        return 0.5
    return 0.2


class AISCollector(BaseCollector):
    name = "ais"
    category = "supply_chain"
    interval_minutes = 240

    async def collect(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(
                    DIGITRAFFIC_AIS_API,
                    headers={"User-Agent": "coffeet-signal-monitor/1.0"},
                )
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError:
                return []

        features = data.get("features", [])
        now = datetime.now(timezone.utc)

        signals = []
        for area in PORT_AREAS:
            vessels_in_area = 0
            for feature in features:
                geom = feature.get("geometry", {})
                coords = geom.get("coordinates", [])
                if len(coords) >= 2:
                    lon, lat = coords[0], coords[1]
                    if (area["lat_min"] <= lat <= area["lat_max"]
                            and area["lon_min"] <= lon <= area["lon_max"]):
                        vessels_in_area += 1

            severity = _density_to_severity(vessels_in_area, VESSEL_DENSITY_BASELINE)
            if severity <= 0.2:
                continue

            signals.append({
                "title": f"Maritime traffic: {area['name']} — {vessels_in_area} vessels",
                "description": f"Vessel density in {area['name']}: {vessels_in_area} (baseline: {VESSEL_DENSITY_BASELINE})",
                "region": area["region"],
                "sector": "supply_chain",
                "severity": severity,
                "raw_json": {
                    "area": area["name"],
                    "vessel_count": vessels_in_area,
                    "baseline": VESSEL_DENSITY_BASELINE,
                    "ratio": round(vessels_in_area / VESSEL_DENSITY_BASELINE, 2) if VESSEL_DENSITY_BASELINE else 0,
                },
                "source_url": "https://www.marinetraffic.com/",
                "signal_time": now,
            })

        return signals
