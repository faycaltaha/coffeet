"""
Wikipedia collector — edit spike detection on geopolitical pages.
API: MediaWiki action=query (no auth required).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from .base import BaseCollector

MEDIAWIKI_API = "https://en.wikipedia.org/w/api.php"

WATCHED_PAGES: list[str] = [
    "Ukraine", "Taiwan", "Iran", "Israel", "Gaza_Strip",
    "South_China_Sea", "North_Korea", "Syria", "Yemen",
    "Suez_Canal", "Panama_Canal", "Strait_of_Hormuz",
    "Russia", "China", "India", "Pakistan",
    "Venezuela", "Sudan", "Ethiopia", "Myanmar",
    "NATO", "BRICS", "OPEC", "European_Union",
    "Semiconductor_industry",
]


def _edit_count_to_severity(count: int) -> float:
    if count >= 50:
        return 1.0
    if count >= 30:
        return 0.8
    if count >= 20:
        return 0.6
    if count >= 10:
        return 0.4
    if count >= 5:
        return 0.2
    return 0.0


class WikipediaCollector(BaseCollector):
    name = "wikipedia"
    category = "osint"
    interval_minutes = 120

    async def collect(self) -> list[dict]:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)
        cutoff_iso = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

        signals = []
        async with httpx.AsyncClient(timeout=30) as client:
            for page in WATCHED_PAGES:
                params = {
                    "action": "query",
                    "titles": page,
                    "prop": "revisions",
                    "rvlimit": "50",
                    "rvprop": "timestamp",
                    "rvstart": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "rvend": cutoff_iso,
                    "format": "json",
                }

                try:
                    resp = await client.get(
                        MEDIAWIKI_API,
                        params=params,
                        headers={"User-Agent": "coffeet-signal-monitor/1.0"},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPError:
                    continue

                pages_data = data.get("query", {}).get("pages", {})
                for page_data in pages_data.values():
                    revisions = page_data.get("revisions", [])
                    edit_count = len(revisions)
                    severity = _edit_count_to_severity(edit_count)
                    if severity == 0.0:
                        continue

                    title = page_data.get("title", page)
                    signals.append({
                        "title": f"Wikipedia edit spike: {title} ({edit_count} edits/24h)",
                        "description": f"{edit_count} edits detected in the last 24 hours",
                        "region": title.replace("_", " "),
                        "sector": None,
                        "severity": severity,
                        "raw_json": {
                            "page": title,
                            "edit_count_24h": edit_count,
                        },
                        "source_url": f"https://en.wikipedia.org/wiki/{page}",
                        "signal_time": now,
                    })

        return signals
