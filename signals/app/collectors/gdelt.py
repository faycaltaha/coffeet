"""
GDELT collector — geopolitical news events and weak signals.
API: https://api.gdeltproject.org/api/v2/doc/doc
No API key required.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from ..config import GDELT_KEYWORDS, SECTOR_KEYWORDS
from .base import BaseCollector

GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"


def _tone_to_severity(tone: float) -> float:
    """Map GDELT tone (negative = bad) to 0-1 severity."""
    if tone <= -15:
        return 1.0
    if tone <= -10:
        return 0.8
    if tone <= -5:
        return 0.6
    if tone <= -2:
        return 0.4
    if tone <= 0:
        return 0.2
    return 0.1


def _parse_gdelt_date(date_str: str) -> datetime:
    """Parse GDELT date format '20260416T143000Z' to datetime."""
    try:
        return datetime.strptime(date_str, "%Y%m%dT%H%M%SZ").replace(
            tzinfo=timezone.utc
        )
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


def _classify_sector(title: str) -> str | None:
    """Match article title against sector keywords."""
    title_lower = title.lower()
    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(kw in title_lower for kw in keywords):
            return sector
    return None


class GDELTCollector(BaseCollector):
    name = "gdelt"
    category = "geopolitical"
    interval_minutes = 30

    async def collect(self) -> list[dict]:
        query = " OR ".join(f'"{kw}"' for kw in GDELT_KEYWORDS[:10])

        params = {
            "query": query,
            "mode": "artlist",
            "maxrecords": "50",
            "format": "json",
            "sort": "datedesc",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(GDELT_API, params=params)
            resp.raise_for_status()
            data = resp.json()

        articles = data.get("articles", [])
        signals = []

        for article in articles:
            title = article.get("title", "").strip()
            if not title:
                continue

            tone = float(article.get("tone", 0) or 0)
            country = article.get("sourcecountry", "")
            seen_date = article.get("seendate", "")

            signals.append({
                "title": title[:500],
                "description": article.get("domain", ""),
                "region": country if country else None,
                "sector": _classify_sector(title),
                "severity": _tone_to_severity(tone),
                "raw_value": tone,
                "raw_unit": "tone",
                "raw_json": {
                    "domain": article.get("domain"),
                    "language": article.get("language"),
                    "sourcecountry": country,
                    "tone": tone,
                },
                "source_url": article.get("url"),
                "signal_time": _parse_gdelt_date(seen_date),
            })

        return signals
