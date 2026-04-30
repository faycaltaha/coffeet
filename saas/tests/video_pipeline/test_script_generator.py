"""Unit tests for Stage 2 – script_generator."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.video_pipeline.car_selector import CarOfTheDay
from app.video_pipeline.script_generator import _build_user_message, generate_script

_CAR = CarOfTheDay(
    make="Volkswagen", model="Golf", year=2018, mileage_km=78_000,
    price_eur=11_500, reliability_score=75.0, price_score=55.0,
    overall_score=70.0, image_url="https://example.com/golf.jpg",
    ad_url="https://www.leboncoin.fr/voitures/456.htm",
    title="Volkswagen Golf 2018", fuel="diesel", estimated_profit=2_500,
)


# ── _build_user_message ───────────────────────────────────────────────────────

def test_build_user_message_contains_car_info():
    msg = _build_user_message(_CAR)
    assert "Volkswagen" in msg
    assert "Golf" in msg
    assert "2018" in msg
    assert "78" in msg            # mileage
    assert "11" in msg            # price


def test_build_user_message_shows_profit():
    msg = _build_user_message(_CAR)
    assert "+2" in msg or "2 500" in msg or "2500" in msg


def test_build_user_message_zero_profit():
    car_no_profit = CarOfTheDay(
        make="Fiat", model="Panda", year=2012, mileage_km=130_000,
        price_eur=4_000, reliability_score=35.0, price_score=0.0,
        overall_score=20.0, image_url="", ad_url="", title="Fiat Panda",
        fuel="essence", estimated_profit=0,
    )
    msg = _build_user_message(car_no_profit)
    assert "inconnu" in msg


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
