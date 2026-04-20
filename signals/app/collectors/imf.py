"""
IMF collector — sovereign debt levels and economic indicators.
API: https://www.imf.org/external/datamapper/api/v1
No API key required.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from .base import BaseCollector

IMF_API = "https://www.imf.org/external/datamapper/api/v1"

WATCHED_INDICATORS: list[dict[str, str]] = [
    {"code": "DEBT", "name": "Government Debt (% GDP)", "unit": "percent_gdp"},
    {"code": "NGDP_RPCH", "name": "Real GDP Growth", "unit": "percent"},
    {"code": "PCPIPCH", "name": "Inflation Rate (CPI)", "unit": "percent"},
]

HIGH_RISK_COUNTRIES: list[str] = [
    "ARG", "TUR", "EGY", "PAK", "NGA", "GHA",
    "ETH", "KEN", "LKA", "UKR", "LBN", "VEN",
]

IMF_COUNTRY_NAMES: dict[str, str] = {
    "ARG": "Argentina", "TUR": "Turkey", "EGY": "Egypt",
    "PAK": "Pakistan", "NGA": "Nigeria", "GHA": "Ghana",
    "ETH": "Ethiopia", "KEN": "Kenya", "LKA": "Sri Lanka",
    "UKR": "Ukraine", "LBN": "Lebanon", "VEN": "Venezuela",
}


def _debt_to_severity(value: float, indicator: str) -> float:
    if indicator == "DEBT":
        if value >= 150:
            return 1.0
        if value >= 120:
            return 0.8
        if value >= 90:
            return 0.6
        if value >= 60:
            return 0.4
        return 0.2
    if indicator == "PCPIPCH":
        if value >= 50:
            return 1.0
        if value >= 20:
            return 0.8
        if value >= 10:
            return 0.6
        if value >= 5:
            return 0.4
        return 0.2
    if indicator == "NGDP_RPCH":
        if value <= -5:
            return 1.0
        if value <= -2:
            return 0.8
        if value <= 0:
            return 0.6
        if value <= 1:
            return 0.4
        return 0.2
    return 0.3


class IMFCollector(BaseCollector):
    name = "imf"
    category = "economic"
    interval_minutes = 720

    async def collect(self) -> list[dict]:
        signals = []
        now = datetime.now(timezone.utc)
        current_year = str(now.year)

        async with httpx.AsyncClient(timeout=30) as client:
            for indicator in WATCHED_INDICATORS:
                url = f"{IMF_API}/{indicator['code']}"

                try:
                    resp = await client.get(
                        url,
                        headers={"User-Agent": "coffeet-signal-monitor/1.0"},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPError:
                    continue

                values = data.get("values", {}).get(indicator["code"], {})

                for country_code in HIGH_RISK_COUNTRIES:
                    country_data = values.get(country_code, {})
                    value = country_data.get(current_year)
                    if value is None:
                        value = country_data.get(str(now.year - 1))
                    if value is None:
                        continue

                    value = float(value)
                    severity = _debt_to_severity(value, indicator["code"])
                    country_name = IMF_COUNTRY_NAMES.get(country_code, country_code)

                    signals.append({
                        "title": f"{indicator['name']}: {country_name} — {value:.1f}",
                        "description": f"{indicator['name']} for {country_name}",
                        "region": country_name,
                        "sector": "finance",
                        "severity": severity,
                        "raw_value": value,
                        "raw_unit": indicator["unit"],
                        "raw_json": {
                            "indicator": indicator["code"],
                            "country": country_code,
                            "value": value,
                        },
                        "source_url": f"https://www.imf.org/external/datamapper/{indicator['code']}",
                        "signal_time": now,
                    })

        return signals
