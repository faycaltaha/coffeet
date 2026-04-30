"""Unit tests for Stage 4 – video_assembler."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.video_pipeline.car_selector import CarOfTheDay
from app.video_pipeline.video_assembler import (
    _group_captions,
    build_shotstack_edit,
    poll_render,
    submit_render,
)
from app.video_pipeline.voice_generator import VoiceResult, WordTimestamp

# ── Fixtures ──────────────────────────────────────────────────────────────────

_CAR = CarOfTheDay(
    make="Toyota", model="Yaris", year=2020, mileage_km=45_000,
    price_eur=9_500, reliability_score=100.0, price_score=80.0,
    overall_score=63.3, image_url="https://example.com/car.jpg",
    ad_url="https://www.leboncoin.fr/voitures/123.htm",
    title="Toyota Yaris 2020", fuel="essence", estimated_profit=3_000,
)

_WORDS = [
    WordTimestamp(word="Bonjour", start=0.0, end=0.6),
    WordTimestamp(word="Marcel", start=0.7, end=1.2),
    WordTimestamp(word="voici", start=1.3, end=1.6),
    WordTimestamp(word="la", start=1.7, end=1.9),
    WordTimestamp(word="voiture", start=2.0, end=2.5),
    WordTimestamp(word="du", start=2.6, end=2.8),
    WordTimestamp(word="jour", start=2.9, end=3.4),
]

_VOICE = VoiceResult(
    audio_path="/tmp/audio.mp3",
    duration_seconds=40.0,
    word_timestamps=_WORDS,
)


# ── _group_captions ───────────────────────────────────────────────────────────

def test_group_captions_correct_count():
    groups = _group_captions(_WORDS, group_size=3)
    # 7 words / 3 per group → ceil(7/3) = 3 groups
    assert len(groups) == 3


def test_group_captions_text_uppercase():
    groups = _group_captions(_WORDS[:3], group_size=3)
    assert groups[0][0] == "BONJOUR MARCEL VOICI"


def test_group_captions_timing():
    groups = _group_captions(_WORDS[:3], group_size=3)
    text, start, duration = groups[0]
    assert start == 0.0
    assert duration == pytest.approx(1.6 - 0.0, abs=0.01)


def test_group_captions_min_duration():
    # Create words with very short spans to exercise the minimum duration guard.
    tiny_words = [
        WordTimestamp(word="A", start=0.0, end=0.05),
        WordTimestamp(word="B", start=0.1, end=0.15),
    ]
    groups = _group_captions(tiny_words, group_size=2)
    _, _, duration = groups[0]
    assert duration >= 0.4


def test_group_captions_single_word():
    groups = _group_captions(_WORDS[:1], group_size=3)
    assert len(groups) == 1
    assert groups[0][0] == "BONJOUR"


def test_group_captions_empty():
    groups = _group_captions([], group_size=3)
    assert groups == []


# ── build_shotstack_edit ──────────────────────────────────────────────────────

def test_build_shotstack_edit_output_dimensions():
    edit = build_shotstack_edit(_CAR, "https://cdn.example.com/audio.mp3", _VOICE)
    assert edit["output"]["size"]["width"] == 1080
    assert edit["output"]["size"]["height"] == 1920
    assert edit["output"]["format"] == "mp4"
    assert edit["output"]["fps"] == 30


def test_build_shotstack_edit_has_tracks():
    edit = build_shotstack_edit(_CAR, "https://cdn.example.com/audio.mp3", _VOICE)
    tracks = edit["timeline"]["tracks"]
    assert len(tracks) >= 4


def test_build_shotstack_edit_image_clip_src():
    edit = build_shotstack_edit(_CAR, "https://cdn.example.com/audio.mp3", _VOICE)
    # First track is background image
    bg_clip = edit["timeline"]["tracks"][0]["clips"][0]
    assert bg_clip["asset"]["src"] == "https://example.com/car.jpg"
    assert bg_clip["effect"] == "zoomIn"


def test_build_shotstack_edit_audio_src():
    audio_url = "https://cdn.example.com/audio.mp3"
    edit = build_shotstack_edit(_CAR, audio_url, _VOICE)
    # Audio clip is in the last track.
    audio_track = edit["timeline"]["tracks"][-1]
    audio_clip = audio_track["clips"][0]
    assert audio_clip["asset"]["src"] == audio_url


def test_build_shotstack_edit_caption_clips_generated():
    edit = build_shotstack_edit(_CAR, "https://cdn.example.com/audio.mp3", _VOICE)
    # Caption track is index 3.
    caption_track = edit["timeline"]["tracks"][3]
    # 7 words / 3 per group = 3 caption clips
    assert len(caption_track["clips"]) == 3


def test_build_shotstack_edit_score_card_contains_scores(monkeypatch):
    monkeypatch.setenv("AUTORADAR_LOGO_URL", "")
    edit = build_shotstack_edit(_CAR, "https://cdn.example.com/audio.mp3", _VOICE)
    # Score card is in track index 4.
    score_clip = edit["timeline"]["tracks"][4]["clips"][0]
    html: str = score_clip["asset"]["html"]
    assert "63" in html   # overall_score ≈ 63
    assert "100" in html  # reliability_score
    assert "80" in html   # price_score


def test_build_shotstack_edit_outro_uses_logo(monkeypatch):
    monkeypatch.setenv("AUTORADAR_LOGO_URL", "https://example.com/logo.png")
    edit = build_shotstack_edit(_CAR, "https://cdn.example.com/audio.mp3", _VOICE)
    outro_track = edit["timeline"]["tracks"][5]
    outro_clip = outro_track["clips"][0]
    assert outro_clip["asset"]["src"] == "https://example.com/logo.png"


def test_build_shotstack_edit_outro_text_fallback(monkeypatch):
    monkeypatch.delenv("AUTORADAR_LOGO_URL", raising=False)
    edit = build_shotstack_edit(_CAR, "https://cdn.example.com/audio.mp3", _VOICE)
    outro_track = edit["timeline"]["tracks"][5]
    outro_clip = outro_track["clips"][0]
    assert "Autoradar" in outro_clip["asset"]["html"]


# ── submit_render ─────────────────────────────────────────────────────────────

def test_submit_render_missing_api_key(monkeypatch):
    monkeypatch.delenv("SHOTSTACK_API_KEY", raising=False)
    with pytest.raises(ValueError, match="SHOTSTACK_API_KEY"):
        submit_render(_CAR, "https://cdn.example.com/audio.mp3", _VOICE)


def test_submit_render_calls_api(monkeypatch):
    monkeypatch.setenv("SHOTSTACK_API_KEY", "ss-test-key")
    monkeypatch.setenv("SHOTSTACK_STAGE", "stage")

    fake_resp = MagicMock()
    fake_resp.raise_for_status = MagicMock()
    fake_resp.json.return_value = {"response": {"id": "render-abc-123"}}

    with patch("app.video_pipeline.video_assembler.httpx.Client") as mock_cls:
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.post.return_value = fake_resp
        mock_cls.return_value = mock_ctx

        render_id = submit_render(_CAR, "https://cdn.example.com/audio.mp3", _VOICE)

    assert render_id == "render-abc-123"
    assert mock_ctx.post.call_args.args[0].endswith("/stage/render")


# ── poll_render ───────────────────────────────────────────────────────────────

def test_poll_render_done(monkeypatch):
    monkeypatch.setenv("SHOTSTACK_API_KEY", "ss-test-key")
    monkeypatch.setenv("SHOTSTACK_STAGE", "stage")

    done_resp = MagicMock()
    done_resp.raise_for_status = MagicMock()
    done_resp.json.return_value = {
        "response": {"status": "done", "url": "https://cdn.shotstack.io/out/video.mp4"}
    }

    with patch("app.video_pipeline.video_assembler.httpx.Client") as mock_cls:
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.get.return_value = done_resp
        mock_cls.return_value = mock_ctx

        with patch("app.video_pipeline.video_assembler.time.sleep"):
            url = poll_render("render-abc-123")

    assert url == "https://cdn.shotstack.io/out/video.mp4"


def test_poll_render_failed(monkeypatch):
    monkeypatch.setenv("SHOTSTACK_API_KEY", "ss-test-key")
    monkeypatch.setenv("SHOTSTACK_STAGE", "stage")

    fail_resp = MagicMock()
    fail_resp.raise_for_status = MagicMock()
    fail_resp.json.return_value = {
        "response": {"status": "failed", "error": "render error"}
    }

    with patch("app.video_pipeline.video_assembler.httpx.Client") as mock_cls:
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.get.return_value = fail_resp
        mock_cls.return_value = mock_ctx

        with patch("app.video_pipeline.video_assembler.time.sleep"):
            with pytest.raises(RuntimeError, match="failed"):
                poll_render("render-abc-123")


def test_poll_render_timeout(monkeypatch):
    monkeypatch.setenv("SHOTSTACK_API_KEY", "ss-test-key")
    monkeypatch.setenv("SHOTSTACK_STAGE", "stage")

    # Always return "rendering" status.
    pending_resp = MagicMock()
    pending_resp.raise_for_status = MagicMock()
    pending_resp.json.return_value = {"response": {"status": "rendering"}}

    with patch("app.video_pipeline.video_assembler.httpx.Client") as mock_cls:
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.get.return_value = pending_resp
        mock_cls.return_value = mock_ctx

        with patch("app.video_pipeline.video_assembler.time.sleep"):
            with patch(
                "app.video_pipeline.video_assembler._MAX_POLL_ATTEMPTS", 2
            ):
                with pytest.raises(TimeoutError):
                    poll_render("render-abc-123")
