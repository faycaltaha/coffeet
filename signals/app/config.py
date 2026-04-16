"""
Central configuration — all env vars, scoring weights, and thresholds.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# ── Database ────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://signal:changeme@localhost:5432/marketsignal",
)

# ── External API keys ───────────────────────────────────────────────────────
FRED_API_KEY: str = os.environ.get("FRED_API_KEY", "")
EIA_API_KEY: str = os.environ.get("EIA_API_KEY", "")

# ── Signal API auth ─────────────────────────────────────────────────────────
SIGNAL_API_KEY: str = os.environ.get("SIGNAL_API_KEY", "")

# ── Scoring weights per category ────────────────────────────────────────────
CATEGORY_WEIGHTS: dict[str, float] = {
    "seismic": 1.5,
    "geopolitical": 1.3,
    "energy": 1.2,
    "economic": 1.0,
    "financial": 0.9,
    "news": 0.8,
}

# ── Alert thresholds ────────────────────────────────────────────────────────
REGION_ALERT_HIGH: float = float(os.environ.get("REGION_ALERT_HIGH", "60"))
REGION_ALERT_CRITICAL: float = float(os.environ.get("REGION_ALERT_CRITICAL", "80"))
SECTOR_SPIKE_THRESHOLD: float = float(os.environ.get("SECTOR_SPIKE_THRESHOLD", "20"))

# ── Recency weights (hours, multiplier) ─────────────────────────────────────
RECENCY_BANDS: list[tuple[int, float]] = [
    (4, 1.5),
    (12, 1.2),
    (24, 1.0),
]

# ── GDELT keyword sets ──────────────────────────────────────────────────────
# Weak signals first (precursors), then escalation terms.
GDELT_KEYWORDS: list[str] = [
    "protest", "strike", "demonstration", "unrest", "rally",
    "labor dispute", "walkout", "civil disobedience",
    "regulatory change", "policy shift", "election dispute",
    "migration surge", "refugee", "border tension",
    "supply shortage", "port delay", "shipping disruption",
    "crop failure", "drought", "flood",
    "sanctions", "embargo", "trade war", "tariff",
    "military buildup", "coup", "martial law",
    "currency crisis", "default", "bank run",
    "pipeline attack", "infrastructure sabotage",
]

# ── RSS feed sources ────────────────────────────────────────────────────────
RSS_FEEDS: list[dict[str, str]] = [
    {"name": "Reuters World", "url": "https://feeds.reuters.com/reuters/worldNews"},
    {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"name": "AP News", "url": "https://rsshub.app/apnews/topics/world-news"},
    {"name": "France 24", "url": "https://www.france24.com/en/rss"},
]

# ── Sector keyword mapping for RSS classification ──────────────────────────
SECTOR_KEYWORDS: dict[str, list[str]] = {
    "energy": [
        "oil", "gas", "opec", "pipeline", "refinery", "lng",
        "solar", "wind", "nuclear", "electricity", "blackout",
    ],
    "agriculture": [
        "crop", "harvest", "drought", "wheat", "corn", "soybean",
        "fertilizer", "famine", "food price", "grain",
    ],
    "supply_chain": [
        "shipping", "port", "container", "freight", "logistics",
        "shortage", "semiconductor", "chip", "rare earth",
    ],
    "finance": [
        "interest rate", "inflation", "central bank", "fed",
        "bond", "yield", "recession", "gdp", "unemployment",
    ],
    "defense": [
        "military", "weapon", "missile", "navy", "army",
        "defense contract", "arms deal", "nato",
    ],
    "technology": [
        "cyber", "hack", "data breach", "ai regulation",
        "tech ban", "export control",
    ],
}

# ── Yahoo Finance tickers ───────────────────────────────────────────────────
YFINANCE_TICKERS: dict[str, dict[str, str]] = {
    "GC=F": {"name": "Gold", "sector": "commodities"},
    "SI=F": {"name": "Silver", "sector": "commodities"},
    "HG=F": {"name": "Copper", "sector": "commodities"},
    "ZW=F": {"name": "Wheat", "sector": "agriculture"},
    "ZC=F": {"name": "Corn", "sector": "agriculture"},
    "ZS=F": {"name": "Soybeans", "sector": "agriculture"},
    "CL=F": {"name": "WTI Crude Oil", "sector": "energy"},
    "BZ=F": {"name": "Brent Crude Oil", "sector": "energy"},
    "NG=F": {"name": "Natural Gas", "sector": "energy"},
    "EURUSD=X": {"name": "EUR/USD", "sector": "finance"},
    "USDJPY=X": {"name": "USD/JPY", "sector": "finance"},
    "USDCNY=X": {"name": "USD/CNY", "sector": "finance"},
    "^VIX": {"name": "VIX Fear Index", "sector": "finance"},
}
