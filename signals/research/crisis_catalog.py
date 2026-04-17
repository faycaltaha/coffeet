"""
Seed the database with 30 historical crises for correlation analysis.

Usage:
    cd signals/
    python -m research.crisis_catalog
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.database import SessionLocal, init_db
from app.models import Crisis

UTC = timezone.utc


CRISES: list[dict] = [
    {
        "name": "2007-2009 Global Financial Crisis",
        "crisis_type": "financial",
        "region": "Global",
        "sector": "finance",
        "impact_description": (
            "Subprime mortgage collapse triggered worldwide banking crisis, "
            "credit freeze, and the deepest recession since the 1930s."
        ),
        "start_date": datetime(2007, 8, 9, tzinfo=UTC),
        "peak_date": datetime(2008, 9, 15, tzinfo=UTC),
        "end_date": datetime(2009, 3, 9, tzinfo=UTC),
        "impact_score": 10.0,
    },
    {
        "name": "2010-2012 Arab Spring",
        "crisis_type": "geopolitical",
        "region": "Middle East",
        "sector": "energy",
        "impact_description": (
            "Wave of protests and revolutions across MENA region. "
            "Governments toppled in Tunisia, Egypt, Libya, Yemen. "
            "Oil supply disruptions and regional instability."
        ),
        "start_date": datetime(2010, 12, 17, tzinfo=UTC),
        "peak_date": datetime(2011, 2, 11, tzinfo=UTC),
        "end_date": datetime(2012, 12, 31, tzinfo=UTC),
        "impact_score": 8.5,
    },
    {
        "name": "2011 Fukushima Nuclear Disaster",
        "crisis_type": "natural_disaster",
        "region": "Japan",
        "sector": "energy",
        "impact_description": (
            "Magnitude 9.0 earthquake and tsunami caused nuclear meltdown "
            "at Fukushima Daiichi. Global supply chain disruption in "
            "automotive and electronics sectors."
        ),
        "start_date": datetime(2011, 3, 11, tzinfo=UTC),
        "peak_date": datetime(2011, 3, 15, tzinfo=UTC),
        "end_date": datetime(2011, 12, 16, tzinfo=UTC),
        "impact_score": 9.0,
    },
    {
        "name": "2011 Thailand Floods",
        "crisis_type": "supply_chain",
        "region": "Southeast Asia",
        "sector": "technology",
        "impact_description": (
            "Severe flooding in Thailand disrupted global hard drive "
            "manufacturing. HDD prices doubled, affecting PC industry worldwide."
        ),
        "start_date": datetime(2011, 7, 25, tzinfo=UTC),
        "peak_date": datetime(2011, 10, 25, tzinfo=UTC),
        "end_date": datetime(2012, 1, 16, tzinfo=UTC),
        "impact_score": 6.5,
    },
    {
        "name": "2014-2015 Oil Price Collapse",
        "crisis_type": "energy",
        "region": "Global",
        "sector": "energy",
        "impact_description": (
            "Oil prices fell from $115 to $28 per barrel due to OPEC "
            "overproduction and US shale boom. Energy sector layoffs, "
            "sovereign debt stress in oil-dependent nations."
        ),
        "start_date": datetime(2014, 6, 20, tzinfo=UTC),
        "peak_date": datetime(2016, 1, 20, tzinfo=UTC),
        "end_date": datetime(2016, 6, 30, tzinfo=UTC),
        "impact_score": 7.5,
    },
    {
        "name": "2014-2016 Ebola Outbreak",
        "crisis_type": "natural_disaster",
        "region": "West Africa",
        "sector": None,
        "impact_description": (
            "Largest Ebola epidemic in history. Over 11,000 deaths in "
            "Guinea, Liberia, Sierra Leone. Trade disruption, travel bans, "
            "mining sector impact."
        ),
        "start_date": datetime(2014, 3, 23, tzinfo=UTC),
        "peak_date": datetime(2014, 10, 1, tzinfo=UTC),
        "end_date": datetime(2016, 3, 29, tzinfo=UTC),
        "impact_score": 7.0,
    },
    {
        "name": "2015 Chinese Stock Market Crash",
        "crisis_type": "financial",
        "region": "China",
        "sector": "finance",
        "impact_description": (
            "Shanghai Composite lost 43% in two months. Capital flight, "
            "yuan devaluation, global contagion fears. Circuit breakers "
            "triggered repeatedly."
        ),
        "start_date": datetime(2015, 6, 12, tzinfo=UTC),
        "peak_date": datetime(2015, 8, 24, tzinfo=UTC),
        "end_date": datetime(2016, 2, 29, tzinfo=UTC),
        "impact_score": 7.0,
    },
    {
        "name": "2016 Brexit Referendum",
        "crisis_type": "geopolitical",
        "region": "Europe",
        "sector": "finance",
        "impact_description": (
            "UK voted to leave the EU. GBP crashed 10%, global markets "
            "lost $2 trillion in two days. Years of trade uncertainty."
        ),
        "start_date": datetime(2016, 6, 23, tzinfo=UTC),
        "peak_date": datetime(2016, 6, 24, tzinfo=UTC),
        "end_date": datetime(2020, 1, 31, tzinfo=UTC),
        "impact_score": 6.5,
    },
    {
        "name": "2018-2020 US-China Trade War",
        "crisis_type": "geopolitical",
        "region": "Global",
        "sector": "supply_chain",
        "impact_description": (
            "Escalating tariffs between US and China disrupted global "
            "supply chains. Technology decoupling, semiconductor "
            "restrictions, agricultural trade disruption."
        ),
        "start_date": datetime(2018, 3, 22, tzinfo=UTC),
        "peak_date": datetime(2019, 8, 23, tzinfo=UTC),
        "end_date": datetime(2020, 1, 15, tzinfo=UTC),
        "impact_score": 7.5,
    },
    {
        "name": "2019-2020 Australian Bushfires",
        "crisis_type": "natural_disaster",
        "region": "Australia",
        "sector": "agriculture",
        "impact_description": (
            "Unprecedented bushfire season burned 46 million acres. "
            "Smoke disrupted agriculture, tourism, and air quality across "
            "the continent."
        ),
        "start_date": datetime(2019, 9, 1, tzinfo=UTC),
        "peak_date": datetime(2020, 1, 4, tzinfo=UTC),
        "end_date": datetime(2020, 3, 4, tzinfo=UTC),
        "impact_score": 6.0,
    },
    {
        "name": "2020 COVID-19 Supply Chain Disruption",
        "crisis_type": "supply_chain",
        "region": "Global",
        "sector": "supply_chain",
        "impact_description": (
            "Pandemic caused unprecedented global supply chain breakdown. "
            "Factory shutdowns, shipping delays, semiconductor shortage, "
            "commodity price spikes."
        ),
        "start_date": datetime(2020, 1, 23, tzinfo=UTC),
        "peak_date": datetime(2020, 4, 15, tzinfo=UTC),
        "end_date": datetime(2021, 12, 31, tzinfo=UTC),
        "impact_score": 10.0,
    },
    {
        "name": "2020 Beirut Port Explosion",
        "crisis_type": "natural_disaster",
        "region": "Middle East",
        "sector": "supply_chain",
        "impact_description": (
            "2,750 tonnes of ammonium nitrate exploded at Beirut port. "
            "300,000 displaced, $15B damage, Lebanon's main trade hub destroyed."
        ),
        "start_date": datetime(2020, 8, 4, tzinfo=UTC),
        "peak_date": datetime(2020, 8, 4, tzinfo=UTC),
        "end_date": datetime(2020, 12, 31, tzinfo=UTC),
        "impact_score": 6.0,
    },
    {
        "name": "2020 Nagorno-Karabakh Conflict",
        "crisis_type": "geopolitical",
        "region": "Caucasus",
        "sector": "energy",
        "impact_description": (
            "Six-week war between Armenia and Azerbaijan near critical "
            "Caspian oil and gas pipelines. Regional energy transit risk."
        ),
        "start_date": datetime(2020, 9, 27, tzinfo=UTC),
        "peak_date": datetime(2020, 10, 15, tzinfo=UTC),
        "end_date": datetime(2020, 11, 10, tzinfo=UTC),
        "impact_score": 5.0,
    },
    {
        "name": "2020-2023 Global Semiconductor Shortage",
        "crisis_type": "supply_chain",
        "region": "Global",
        "sector": "technology",
        "impact_description": (
            "COVID demand surge plus fab capacity constraints caused "
            "multi-year chip shortage. Auto production cut by millions, "
            "consumer electronics delayed."
        ),
        "start_date": datetime(2020, 10, 1, tzinfo=UTC),
        "peak_date": datetime(2021, 9, 1, tzinfo=UTC),
        "end_date": datetime(2023, 6, 30, tzinfo=UTC),
        "impact_score": 8.5,
    },
    {
        "name": "2021 Suez Canal Blockage",
        "crisis_type": "supply_chain",
        "region": "Middle East",
        "sector": "supply_chain",
        "impact_description": (
            "Ever Given container ship blocked the Suez Canal for 6 days. "
            "Held up $9.6B of daily trade, 400+ vessels queued."
        ),
        "start_date": datetime(2021, 3, 23, tzinfo=UTC),
        "peak_date": datetime(2021, 3, 26, tzinfo=UTC),
        "end_date": datetime(2021, 3, 29, tzinfo=UTC),
        "impact_score": 5.5,
    },
    {
        "name": "2021 Texas Power Crisis",
        "crisis_type": "energy",
        "region": "United States",
        "sector": "energy",
        "impact_description": (
            "Winter storm Uri caused mass power outages across Texas. "
            "4.5 million lost power, natural gas supply froze, "
            "petrochemical plants shut down."
        ),
        "start_date": datetime(2021, 2, 13, tzinfo=UTC),
        "peak_date": datetime(2021, 2, 16, tzinfo=UTC),
        "end_date": datetime(2021, 2, 20, tzinfo=UTC),
        "impact_score": 6.0,
    },
    {
        "name": "2021 Myanmar Military Coup",
        "crisis_type": "geopolitical",
        "region": "Southeast Asia",
        "sector": None,
        "impact_description": (
            "Military seized power, detained Aung San Suu Kyi. "
            "Mass protests, internet shutdowns, disruption to garment "
            "and natural resource exports."
        ),
        "start_date": datetime(2021, 2, 1, tzinfo=UTC),
        "peak_date": datetime(2021, 3, 27, tzinfo=UTC),
        "end_date": None,
        "impact_score": 6.0,
    },
    {
        "name": "2022 Russia-Ukraine War",
        "crisis_type": "geopolitical",
        "region": "Europe",
        "sector": "energy",
        "impact_description": (
            "Russian invasion of Ukraine. Energy crisis in Europe, "
            "grain export blockade, fertilizer shortage, sanctions regime, "
            "global inflation spike."
        ),
        "start_date": datetime(2022, 2, 24, tzinfo=UTC),
        "peak_date": datetime(2022, 9, 30, tzinfo=UTC),
        "end_date": None,
        "impact_score": 9.5,
    },
    {
        "name": "2022 Sri Lanka Economic Collapse",
        "crisis_type": "financial",
        "region": "South Asia",
        "sector": "finance",
        "impact_description": (
            "Sri Lanka defaulted on foreign debt. Fuel and food shortages, "
            "mass protests, president fled. Currency collapsed 80%."
        ),
        "start_date": datetime(2022, 3, 1, tzinfo=UTC),
        "peak_date": datetime(2022, 7, 9, tzinfo=UTC),
        "end_date": datetime(2022, 12, 31, tzinfo=UTC),
        "impact_score": 7.0,
    },
    {
        "name": "2022 European Energy Crisis",
        "crisis_type": "energy",
        "region": "Europe",
        "sector": "energy",
        "impact_description": (
            "Russia cut gas supplies via Nord Stream. European gas prices "
            "surged 10x. Industrial shutdowns, energy rationing fears, "
            "accelerated green transition."
        ),
        "start_date": datetime(2022, 2, 24, tzinfo=UTC),
        "peak_date": datetime(2022, 8, 26, tzinfo=UTC),
        "end_date": datetime(2023, 3, 31, tzinfo=UTC),
        "impact_score": 8.5,
    },
    {
        "name": "2022 UK Gilt Crisis",
        "crisis_type": "financial",
        "region": "United Kingdom",
        "sector": "finance",
        "impact_description": (
            "Truss mini-budget triggered gilt market crash. Bank of England "
            "emergency intervention, pension fund near-collapse, PM resigned "
            "after 45 days."
        ),
        "start_date": datetime(2022, 9, 23, tzinfo=UTC),
        "peak_date": datetime(2022, 9, 28, tzinfo=UTC),
        "end_date": datetime(2022, 10, 25, tzinfo=UTC),
        "impact_score": 6.5,
    },
    {
        "name": "2022 Pakistan Floods",
        "crisis_type": "natural_disaster",
        "region": "South Asia",
        "sector": "agriculture",
        "impact_description": (
            "Unprecedented monsoon flooding submerged one-third of Pakistan. "
            "1,700+ deaths, $30B damage, massive crop destruction, "
            "cotton supply disruption."
        ),
        "start_date": datetime(2022, 6, 14, tzinfo=UTC),
        "peak_date": datetime(2022, 8, 30, tzinfo=UTC),
        "end_date": datetime(2022, 10, 31, tzinfo=UTC),
        "impact_score": 7.0,
    },
    {
        "name": "2023 Turkey-Syria Earthquake",
        "crisis_type": "natural_disaster",
        "region": "Middle East",
        "sector": None,
        "impact_description": (
            "Magnitude 7.8 earthquake killed 60,000+. Massive humanitarian "
            "crisis, infrastructure destruction, regional trade disruption."
        ),
        "start_date": datetime(2023, 2, 6, tzinfo=UTC),
        "peak_date": datetime(2023, 2, 6, tzinfo=UTC),
        "end_date": datetime(2023, 6, 30, tzinfo=UTC),
        "impact_score": 8.0,
    },
    {
        "name": "2023 Niger Coup",
        "crisis_type": "geopolitical",
        "region": "West Africa",
        "sector": "energy",
        "impact_description": (
            "Military coup in Niger threatened uranium supply to France "
            "and EU. ECOWAS sanctions, regional instability across Sahel."
        ),
        "start_date": datetime(2023, 7, 26, tzinfo=UTC),
        "peak_date": datetime(2023, 8, 10, tzinfo=UTC),
        "end_date": datetime(2023, 12, 31, tzinfo=UTC),
        "impact_score": 5.5,
    },
    {
        "name": "2023 Israel-Hamas War",
        "crisis_type": "geopolitical",
        "region": "Middle East",
        "sector": "energy",
        "impact_description": (
            "Hamas attack on Oct 7 triggered Israeli military operation. "
            "Oil price spike, shipping rerouting, regional escalation risk "
            "involving Iran and Hezbollah."
        ),
        "start_date": datetime(2023, 10, 7, tzinfo=UTC),
        "peak_date": datetime(2023, 10, 27, tzinfo=UTC),
        "end_date": None,
        "impact_score": 8.0,
    },
    {
        "name": "2023-2024 Red Sea / Houthi Shipping Crisis",
        "crisis_type": "supply_chain",
        "region": "Middle East",
        "sector": "supply_chain",
        "impact_description": (
            "Houthi attacks on commercial shipping in Red Sea forced "
            "rerouting around Cape of Good Hope. Shipping costs surged 300%, "
            "delivery delays of 10-14 days."
        ),
        "start_date": datetime(2023, 11, 19, tzinfo=UTC),
        "peak_date": datetime(2024, 1, 15, tzinfo=UTC),
        "end_date": None,
        "impact_score": 7.0,
    },
    {
        "name": "2023 Panama Canal Drought",
        "crisis_type": "supply_chain",
        "region": "Central America",
        "sector": "supply_chain",
        "impact_description": (
            "Severe drought reduced Panama Canal daily transits from 36 to 24. "
            "Shipping delays and surcharges for global trade route handling "
            "5% of world trade."
        ),
        "start_date": datetime(2023, 7, 1, tzinfo=UTC),
        "peak_date": datetime(2024, 2, 1, tzinfo=UTC),
        "end_date": datetime(2024, 6, 30, tzinfo=UTC),
        "impact_score": 5.5,
    },
    {
        "name": "2024 Baltimore Bridge Collapse",
        "crisis_type": "supply_chain",
        "region": "United States",
        "sector": "supply_chain",
        "impact_description": (
            "Container ship struck Francis Scott Key Bridge, closing "
            "Port of Baltimore for weeks. Auto and coal exports disrupted, "
            "East Coast shipping rerouted."
        ),
        "start_date": datetime(2024, 3, 26, tzinfo=UTC),
        "peak_date": datetime(2024, 3, 26, tzinfo=UTC),
        "end_date": datetime(2024, 6, 10, tzinfo=UTC),
        "impact_score": 4.5,
    },
    {
        "name": "2024 Iran-Israel Tensions",
        "crisis_type": "geopolitical",
        "region": "Middle East",
        "sector": "energy",
        "impact_description": (
            "Direct military exchanges between Iran and Israel in April 2024. "
            "Oil price spike, regional war fears, Strait of Hormuz risk."
        ),
        "start_date": datetime(2024, 4, 1, tzinfo=UTC),
        "peak_date": datetime(2024, 4, 14, tzinfo=UTC),
        "end_date": datetime(2024, 4, 30, tzinfo=UTC),
        "impact_score": 6.5,
    },
    {
        "name": "2025 US Tariff Escalation",
        "crisis_type": "geopolitical",
        "region": "Global",
        "sector": "supply_chain",
        "impact_description": (
            "Broad US tariff increases on imports from multiple trading partners. "
            "Supply chain restructuring, retaliatory tariffs, market volatility."
        ),
        "start_date": datetime(2025, 2, 1, tzinfo=UTC),
        "peak_date": datetime(2025, 4, 9, tzinfo=UTC),
        "end_date": None,
        "impact_score": 7.5,
    },
]


async def seed_crises() -> int:
    await init_db()
    added = 0
    async with SessionLocal() as session:
        for crisis_data in CRISES:
            result = await session.execute(
                select(Crisis).where(Crisis.name == crisis_data["name"])
            )
            if result.scalar_one_or_none() is not None:
                continue
            session.add(Crisis(**crisis_data))
            added += 1
        await session.commit()
    return added


def main() -> None:
    count = asyncio.run(seed_crises())
    total = len(CRISES)
    print(f"Crisis catalog: {count} new crises added ({total} total in catalog)")


if __name__ == "__main__":
    main()
