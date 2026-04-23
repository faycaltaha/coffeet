"""
Unit tests for Sprint 2 collector pure functions.
"""
from __future__ import annotations

import pytest

from app.collectors.noaa import _alert_severity, _classify_sector
from app.collectors.reliefweb import _extract_country, _status_to_severity
from app.collectors.opensanctions import _entity_to_region, _schema_to_severity
from app.collectors.comtrade import _trade_change_severity
from app.collectors.imf import _debt_to_severity
from app.collectors.acled import _event_severity, _extract_region
from app.collectors.ais import _density_to_severity


# ── NOAA ─────────────────────────────────────────────────────────────────────


class TestNOAAAlertSeverity:
    def test_extreme_hurricane(self):
        assert _alert_severity("Extreme", "Hurricane Warning") == 1.0

    def test_extreme_non_supply_chain(self):
        assert _alert_severity("Extreme", "Heat Advisory") == 1.0

    def test_severe_tornado(self):
        assert _alert_severity("Severe", "Tornado Watch") == 0.9

    def test_severe_plain(self):
        assert _alert_severity("Severe", "Wind Advisory") == 0.8

    def test_moderate(self):
        assert _alert_severity("Moderate", "Frost Warning") == 0.5

    def test_minor(self):
        assert _alert_severity("Minor", "Beach Hazard") == 0.3

    def test_unknown(self):
        assert _alert_severity("Unknown", "Something") == 0.2


class TestNOAAClassifySector:
    def test_agriculture_drought(self):
        assert _classify_sector("Drought Warning") == "agriculture"

    def test_agriculture_flood(self):
        assert _classify_sector("Flash Flood Watch") == "agriculture"

    def test_supply_chain_hurricane(self):
        assert _classify_sector("Hurricane Warning") == "supply_chain"

    def test_supply_chain_tornado(self):
        assert _classify_sector("Tornado Warning") == "supply_chain"

    def test_energy_heat(self):
        assert _classify_sector("Extreme Heat Warning") == "energy"

    def test_energy_cold(self):
        assert _classify_sector("Extreme Cold Warning") == "energy"

    def test_none_generic(self):
        assert _classify_sector("Fog Advisory") is None


# ── ReliefWeb ────────────────────────────────────────────────────────────────


class TestReliefWebSeverity:
    def test_alert_status(self):
        assert _status_to_severity("Alert", "Earthquake") == 0.9

    def test_emergency_status(self):
        assert _status_to_severity("Emergency", "Flood") == 0.9

    def test_ongoing_status(self):
        assert _status_to_severity("Ongoing", "Drought") == 0.7

    def test_earthquake_type(self):
        assert _status_to_severity("Past", "Earthquake") == 0.7

    def test_drought_type(self):
        assert _status_to_severity("Past", "Drought") == 0.6

    def test_volcano_type(self):
        assert _status_to_severity("Past", "Volcano") == 0.5

    def test_unknown(self):
        assert _status_to_severity("Past", "Unknown") == 0.3


class TestReliefWebExtractCountry:
    def test_with_country(self):
        assert _extract_country({"country": [{"name": "Nepal"}]}) == "Nepal"

    def test_empty_list(self):
        assert _extract_country({"country": []}) is None

    def test_no_key(self):
        assert _extract_country({}) is None

    def test_non_list(self):
        assert _extract_country({"country": "Nepal"}) is None


# ── OpenSanctions ────────────────────────────────────────────────────────────


class TestOpenSanctionsSeverity:
    def test_sanction_high_score(self):
        result = _schema_to_severity("Sanction", 1.0)
        assert result == 1.0

    def test_sanction_low_score(self):
        result = _schema_to_severity("Sanction", 0.0)
        assert result == 0.6

    def test_company_high_score(self):
        result = _schema_to_severity("Company", 1.0)
        assert result == 0.8

    def test_other_schema(self):
        result = _schema_to_severity("Person", 0.5)
        assert result == 0.4


class TestOpenSanctionsRegion:
    def test_with_country(self):
        assert _entity_to_region({"country": ["Russia"]}) == "Russia"

    def test_empty_countries(self):
        assert _entity_to_region({"country": []}) is None

    def test_no_country_key(self):
        assert _entity_to_region({}) is None


# ── UN Comtrade ──────────────────────────────────────────────────────────────


class TestComtradeSeverity:
    def test_large_change(self):
        assert _trade_change_severity(130, 100) == 1.0

    def test_significant_change(self):
        assert _trade_change_severity(125, 100) == 0.8

    def test_moderate_change(self):
        assert _trade_change_severity(115, 100) == 0.6

    def test_small_change(self):
        assert _trade_change_severity(107, 100) == 0.4

    def test_minimal_change(self):
        assert _trade_change_severity(103, 100) == 0.2

    def test_zero_previous(self):
        assert _trade_change_severity(100, 0) == 0.3

    def test_decrease(self):
        assert _trade_change_severity(70, 100) == 1.0


# ── IMF ──────────────────────────────────────────────────────────────────────


class TestIMFDebtSeverity:
    def test_extreme_debt(self):
        assert _debt_to_severity(160, "DEBT") == 1.0

    def test_high_debt(self):
        assert _debt_to_severity(130, "DEBT") == 0.8

    def test_elevated_debt(self):
        assert _debt_to_severity(95, "DEBT") == 0.6

    def test_moderate_debt(self):
        assert _debt_to_severity(70, "DEBT") == 0.4

    def test_low_debt(self):
        assert _debt_to_severity(40, "DEBT") == 0.2

    def test_hyperinflation(self):
        assert _debt_to_severity(55, "PCPIPCH") == 1.0

    def test_high_inflation(self):
        assert _debt_to_severity(25, "PCPIPCH") == 0.8

    def test_moderate_inflation(self):
        assert _debt_to_severity(12, "PCPIPCH") == 0.6

    def test_low_inflation(self):
        assert _debt_to_severity(3, "PCPIPCH") == 0.2

    def test_deep_recession(self):
        assert _debt_to_severity(-6, "NGDP_RPCH") == 1.0

    def test_recession(self):
        assert _debt_to_severity(-3, "NGDP_RPCH") == 0.8

    def test_stagnation(self):
        assert _debt_to_severity(-0.5, "NGDP_RPCH") == 0.6

    def test_slow_growth(self):
        assert _debt_to_severity(0.5, "NGDP_RPCH") == 0.4

    def test_healthy_growth(self):
        assert _debt_to_severity(3, "NGDP_RPCH") == 0.2

    def test_unknown_indicator(self):
        assert _debt_to_severity(100, "UNKNOWN") == 0.3


# ── ACLED ────────────────────────────────────────────────────────────────────


class TestACLEDSeverity:
    def test_battles_no_fatalities(self):
        assert _event_severity("Battles", 0) == 0.9

    def test_battles_mass_fatalities(self):
        assert _event_severity("Battles", 100) == 1.0

    def test_protests_no_fatalities(self):
        assert _event_severity("Protests", 0) == 0.5

    def test_protests_with_fatalities(self):
        assert _event_severity("Protests", 10) == 0.7

    def test_riots(self):
        assert _event_severity("Riots", 0) == 0.7

    def test_violence_civilians(self):
        assert _event_severity("Violence against civilians", 0) == 0.8

    def test_unknown_type(self):
        assert _event_severity("Unknown", 0) == 0.3

    def test_high_fatalities_override(self):
        assert _event_severity("Protests", 50) == 0.9

    def test_minor_fatalities_boost(self):
        result = _event_severity("Strategic developments", 1)
        assert result == 0.5


class TestACLEDExtractRegion:
    def test_normal_country(self):
        assert _extract_region("Ethiopia") == "Ethiopia"

    def test_whitespace(self):
        assert _extract_region("  Sudan  ") == "Sudan"

    def test_empty(self):
        assert _extract_region("") == "Unknown"


# ── AIS ──────────────────────────────────────────────────────────────────────


class TestAISDensitySeverity:
    def test_very_high_density(self):
        assert _density_to_severity(150, 50) == 1.0

    def test_high_density(self):
        assert _density_to_severity(100, 50) == 0.8

    def test_elevated_density(self):
        assert _density_to_severity(80, 50) == 0.6

    def test_slightly_elevated(self):
        assert _density_to_severity(65, 50) == 0.4

    def test_normal_density(self):
        assert _density_to_severity(50, 50) == 0.2

    def test_low_density_concerning(self):
        assert _density_to_severity(10, 50) == 0.7

    def test_reduced_density(self):
        assert _density_to_severity(20, 50) == 0.5

    def test_zero_baseline(self):
        assert _density_to_severity(10, 0) == 0.3
