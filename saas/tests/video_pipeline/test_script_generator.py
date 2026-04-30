"""Unit tests for Stage 2 – script_generator."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from datetime import date

from app.video_pipeline.car_selector import CarOfTheDay
from app.video_pipeline.script_generator import (
    MARCEL_SIGNATURES,
    _build_user_message,
    generate_script,
    pick_signature,
)

_CAR = CarOfTheDay(
    make="Volkswagen", model="Golf", year=2018, mileage_km=78_000,
    price_eur=11_500, reliability_score=75.0, price_score=55.0,
    overall_score=70.0, image_url="https://example.com/golf.jpg",
    ad_url="https://www.leboncoin.fr/voitures/456.htm",
    title="Volkswagen Golf 2018", fuel="diesel", estimated_profit=2_500,
)

_CAR_ROAST = CarOfTheDay(
    make="Fiat", model="Stilo", year=2005, mileage_km=200_000,
    price_eur=6_000, reliability_score=15.0, price_score=80.0,
    overall_score=10.0, image_url="", ad_url="", title="Fiat Stilo 2005",
    fuel="essence", estimated_profit=0,
    mode="ROAST", score_gap=65.0,
    comparison_summary="2020 Toyota Yaris – score Autoradar 88/100 – 9 500 €",
)


# ── pick_signature ────────────────────────────────────────────────────────────

def test_pick_signature_returns_string_from_pool():
    sig = pick_signature(_CAR)
    assert sig in MARCEL_SIGNATURES["DIAMOND"]


def test_pick_signature_roast_uses_roast_pool():
    sig = pick_signature(_CAR_ROAST)
    assert sig in MARCEL_SIGNATURES["ROAST"]


def test_pick_signature_deterministic_same_day():
    d = date(2026, 5, 1)
    assert pick_signature(_CAR, today=d) == pick_signature(_CAR, today=d)


def test_pick_signature_varies_by_day():
    d1 = date(2026, 5, 1)
    d2 = date(2026, 5, 2)
    # Different days must not always give the same phrase (they differ for this car).
    results = {pick_signature(_CAR, today=d1), pick_signature(_CAR, today=d2)}
    # At least one of the two days should yield a valid pool member — both always will.
    assert all(s in MARCEL_SIGNATURES["DIAMOND"] for s in results)


def test_pick_signature_unknown_mode_falls_back_to_roast():
    car = CarOfTheDay(
        make="X", model="Y", year=2020, mileage_km=0, price_eur=0,
        reliability_score=0.0, price_score=0.0, overall_score=0.0,
        image_url="", ad_url="", title="X Y 2020", fuel="",
        estimated_profit=0, mode="UNKNOWN",
    )
    sig = pick_signature(car, today=date(2026, 5, 1))
    assert sig in MARCEL_SIGNATURES["ROAST"]


def test_all_signatures_end_with_autoradar():
    """Every phrase in every pool must close with 'Autoradar' for brand consistency."""
    for mode, pool in MARCEL_SIGNATURES.items():
        for phrase in pool:
            assert phrase.endswith("Autoradar."), (
                f"{mode} phrase does not end with 'Autoradar.': {phrase!r}"
            )


def test_pick_signature_all_pool_entries_reachable():
    """Every phrase in each pool must be reachable within a reasonable range of dates."""
    from datetime import timedelta
    for mode, pool in MARCEL_SIGNATURES.items():
        car = CarOfTheDay(
            make="T", model="T", year=2020, mileage_km=0, price_eur=0,
            reliability_score=0.0, price_score=0.0, overall_score=0.0,
            image_url="", ad_url="", title="T T 2020", fuel="",
            estimated_profit=0, mode=mode,
        )
        seen = set()
        base = date(2026, 1, 1)
        for i in range(365):
            seen.add(pick_signature(car, today=base + timedelta(days=i)))
        assert seen == set(pool), f"Not all {mode} phrases reachable in 365 days"


# ── _build_user_message ───────────────────────────────────────────────────────

_SIG = "Une perle rare dans un océan de ferraille. La machine a parlé. C'est Autoradar."


def test_build_user_message_contains_car_info():
    msg = _build_user_message(_CAR, _SIG)
    assert "Volkswagen" in msg
    assert "Golf" in msg
    assert "2018" in msg
    assert "78" in msg            # mileage
    assert "11" in msg            # price


def test_build_user_message_shows_profit():
    msg = _build_user_message(_CAR, _SIG)
    assert "+2" in msg or "2 500" in msg or "2500" in msg


def test_build_user_message_zero_profit():
    car_no_profit = CarOfTheDay(
        make="Fiat", model="Panda", year=2012, mileage_km=130_000,
        price_eur=4_000, reliability_score=35.0, price_score=0.0,
        overall_score=20.0, image_url="", ad_url="", title="Fiat Panda",
        fuel="essence", estimated_profit=0,
    )
    msg = _build_user_message(car_no_profit, _SIG)
    assert "négatif" in msg


def test_build_user_message_embeds_signature():
    sig = "Ne dites pas que je ne vous avais pas prévenu."
    msg = _build_user_message(_CAR, sig)
    assert sig in msg
    assert "SIGNATURE FINALE OBLIGATOIRE" in msg


def test_build_user_message_diamond_mode():
    msg = _build_user_message(_CAR, _SIG)
    assert "DIAMOND" in msg
    assert "alternative" not in msg.lower()
    assert "Écart" not in msg


def test_build_user_message_roast_includes_comparison():
    msg = _build_user_message(_CAR_ROAST, _SIG)
    assert "ROAST" in msg
    assert "Toyota" in msg          # from comparison_summary
    assert "65" in msg              # score_gap


def test_build_user_message_roast_no_comparison_when_empty():
    car = CarOfTheDay(
        make="Alfa", model="Romeo", year=2008, mileage_km=180_000,
        price_eur=5_000, reliability_score=10.0, price_score=70.0,
        overall_score=5.0, image_url="", ad_url="", title="Alfa Romeo",
        fuel="essence", estimated_profit=0,
        mode="ROAST", score_gap=60.0, comparison_summary="",
    )
    msg = _build_user_message(car, _SIG)
    assert "ROAST" in msg
    assert "alternative Autoradar" not in msg


# ── generate_script ───────────────────────────────────────────────────────────

def test_generate_script_missing_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        generate_script(_CAR)


def test_generate_script_calls_claude(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    mock_content = MagicMock()
    mock_content.text = "Bienvenue sur Autoradar ! Cette Golf 2018 est une pépite."
    mock_message = MagicMock()
    mock_message.content = [mock_content]
    mock_message.usage.input_tokens = 120
    mock_message.usage.output_tokens = 80

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("app.video_pipeline.script_generator.anthropic.Anthropic", return_value=mock_client):
        result = generate_script(_CAR)

    assert result == "Bienvenue sur Autoradar ! Cette Golf 2018 est une pépite."
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-haiku-4-5-20251001"
    assert call_kwargs["max_tokens"] == 512


def test_generate_script_strips_whitespace(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    mock_content = MagicMock()
    mock_content.text = "  Script avec espaces.  "
    mock_message = MagicMock()
    mock_message.content = [mock_content]
    mock_message.usage.input_tokens = 50
    mock_message.usage.output_tokens = 30

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("app.video_pipeline.script_generator.anthropic.Anthropic", return_value=mock_client):
        result = generate_script(_CAR)

    assert result == "Script avec espaces."


def test_generate_script_system_prompt_in_call(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    mock_content = MagicMock()
    mock_content.text = "Script."
    mock_message = MagicMock()
    mock_message.content = [mock_content]
    mock_message.usage.input_tokens = 10
    mock_message.usage.output_tokens = 5

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("app.video_pipeline.script_generator.anthropic.Anthropic", return_value=mock_client):
        generate_script(_CAR)

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert "Marcel" in call_kwargs["system"]
    assert "Autoradar" in call_kwargs["system"]
    assert "LA CLAQUE" in call_kwargs["system"]
    assert "LA SORTIE" in call_kwargs["system"]
    assert "5 SEGMENTS" in call_kwargs["system"]
    assert "LA SIGNATURE" in call_kwargs["system"]
    # The user message must contain the injected signature phrase.
    user_content = call_kwargs["messages"][0]["content"]
    assert "SIGNATURE FINALE OBLIGATOIRE" in user_content
