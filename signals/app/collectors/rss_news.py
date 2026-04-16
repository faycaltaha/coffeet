"""
RSS News collector — curated news feeds with keyword classification.
Sources: Reuters, BBC, Al Jazeera, AP News, France 24.
No API key required.
"""
from __future__ import annotations

import calendar
from datetime import datetime, timezone

import feedparser
import httpx

from ..config import GDELT_KEYWORDS, RSS_FEEDS, SECTOR_KEYWORDS
from .base import BaseCollector

CRISIS_TERMS = {
    "crisis", "war", "collapse", "emergency", "catastrophe",
    "explosion", "attack", "shutdown", "default", "crash",
}


def _keyword_severity(title: str, summary: str) -> float:
    """Score severity by keyword density and crisis-level terms."""
    text = f"{title} {summary}".lower()

    crisis_hits = sum(1 for t in CRISIS_TERMS if t in text)
    if crisis_hits >= 2:
        return 0.9
    if crisis_hits == 1:
        return 0.7

    weak_hits = sum(1 for kw in GDELT_KEYWORDS if kw in text)
    if weak_hits >= 3:
        return 0.6
    if weak_hits >= 2:
        return 0.4
    if weak_hits >= 1:
        return 0.3
    return 0.1


def _classify_sector(text: str) -> str | None:
    text_lower = text.lower()
    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return sector
    return None


def _parse_published(entry: dict) -> datetime:
    """Extract publication datetime from feed entry."""
    parsed = entry.get("published_parsed")
    if parsed:
        try:
            ts = calendar.timegm(parsed)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (ValueError, OverflowError):
            pass
    return datetime.now(timezone.utc)


class RSSCollector(BaseCollector):
    name = "rss"
    category = "news"
    interval_minutes = 20

    async def collect(self) -> list[dict]:
        signals = []

        async with httpx.AsyncClient(timeout=15) as client:
            for feed_info in RSS_FEEDS:
                try:
                    resp = await client.get(feed_info["url"])
                    resp.raise_for_status()
                    feed = feedparser.parse(resp.text)
                except (httpx.HTTPError, Exception):
                    continue

                for entry in feed.get("entries", [])[:20]:
                    title = entry.get("title", "").strip()
                    if not title:
                        continue

                    summary = entry.get("summary", "")
                    combined = f"{title} {summary}"

                    has_match = any(
                        kw in combined.lower() for kw in GDELT_KEYWORDS
                    )
                    if not has_match:
                        continue

                    signals.append({
                        "title": title[:500],
                        "description": (
                            f"Source: {feed_info['name']}. "
                            f"{summary[:200]}"
                        ),
                        "region": None,
                        "sector": _classify_sector(combined),
                        "severity": _keyword_severity(title, summary),
                        "raw_value": None,
                        "raw_unit": None,
                        "raw_json": {
                            "feed": feed_info["name"],
                            "link": entry.get("link"),
                        },
                        "source_url": entry.get("link"),
                        "signal_time": _parse_published(entry),
                    })

        return signals
