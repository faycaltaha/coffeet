"""
OpenSanctions collector — sanctions list changes and PEP updates.
API: https://api.opensanctions.org/search/default
No API key required.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from .base import BaseCollector

OPENSANCTIONS_API = "https://api.opensanctions.org/search/default"

WATCH_TOPICS: list[str] = [
    "sanctions", "embargo", "trade restriction",
    "arms embargo", "financial sanctions",
    "travel ban", "asset freeze",
]


def _schema_to_severity(schema: str, score: float) -> float:
    schema_lower = schema.lower()
    if "sanction" in schema_lower:
        return min(1.0, 0.6 + score * 0.4)
    if "company" in schema_lower or "organization" in schema_lower:
        return min(1.0, 0.5 + score * 0.3)
    return min(1.0, 0.3 + score * 0.2)


def _entity_to_region(properties: dict) -> str | None:
    countries = properties.get("country", [])
    if countries:
        return countries[0]
    return None


class OpenSanctionsCollector(BaseCollector):
    name = "opensanctions"
    category = "geopolitical"
    interval_minutes = 360

    async def collect(self) -> list[dict]:
        signals = []
        async with httpx.AsyncClient(timeout=30) as client:
            for topic in WATCH_TOPICS:
                params = {"q": topic, "limit": "10"}

                try:
                    resp = await client.get(
                        OPENSANCTIONS_API,
                        params=params,
                        headers={"User-Agent": "coffeet-signal-monitor/1.0"},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPError:
                    continue

                for result in data.get("results", []):
                    caption = result.get("caption", "").strip()
                    if not caption:
                        continue

                    schema = result.get("schema", "")
                    score = result.get("score", 0.0)
                    properties = result.get("properties", {})

                    last_seen = result.get("last_seen", "")
                    try:
                        signal_time = datetime.fromisoformat(
                            last_seen.replace("Z", "+00:00")
                        )
                    except (ValueError, AttributeError):
                        signal_time = datetime.now(timezone.utc)

                    datasets = result.get("datasets", [])
                    signals.append({
                        "title": f"Sanctions entity: {caption}"[:500],
                        "description": f"Schema: {schema}. Datasets: {', '.join(datasets[:3])}",
                        "region": _entity_to_region(properties),
                        "sector": None,
                        "severity": _schema_to_severity(schema, score),
                        "raw_json": {
                            "entity_id": result.get("id"),
                            "schema": schema,
                            "score": score,
                            "datasets": datasets[:5],
                            "topic": topic,
                        },
                        "source_url": result.get("id"),
                        "signal_time": signal_time,
                    })

        return signals
