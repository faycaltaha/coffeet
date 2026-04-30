"""Unit tests for Stage 3 – voice_generator."""
from __future__ import annotations

import base64
import json
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from app.video_pipeline.voice_generator import (
    VoiceResult,
    WordTimestamp,
    _extract_word_timestamps,
    generate_voice,
)

# ── _extract_word_timestamps ──────────────────────────────────────────────────

def test_extract_empty_alignment():
    result = _extract_word_timestamps({})
    assert result == []


def test_extract_single_word():
    alignment = {
        "characters": ["H", "i"],
        "character_start_times_seconds": [0.0, 0.1],
        "character_end_times_seconds": [0.1, 0.2],
    }
    words = _extract_word_timestamps(alignment)
    assert len(words) == 1
    assert words[0].word == "Hi"
    assert words[0].start == 0.0
    assert words[0].end == 0.2


def test_extract_two_words():
    alignment = {
        "characters": ["H", "i", " ", "M", "a", "r", "c", "e", "l"],
        "character_start_times_seconds": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
        "character_end_times_seconds":   [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
    }
    words = _extract_word_timestamps(alignment)
    assert len(words) == 2
    assert words[0].word == "Hi"
    assert words[1].word == "Marcel"
    assert words[1].start == 0.3
    assert words[1].end == 0.9


def test_extract_newline_separator():
    alignment = {
        "characters": ["A", "\n", "B"],
        "character_start_times_seconds": [0.0, 0.1, 0.2],
        "character_end_times_seconds":   [0.1, 0.2, 0.3],
    }
    words = _extract_word_timestamps(alignment)
    assert len(words) == 2
    assert words[0].word == "A"
    assert words[1].word == "B"


def test_extract_multiple_spaces():
    alignment = {
        "characters": ["A", " ", " ", "B"],
        "character_start_times_seconds": [0.0, 0.1, 0.2, 0.3],
        "character_end_times_seconds":   [0.1, 0.2, 0.3, 0.4],
    }
    words = _extract_word_timestamps(alignment)
    # Two consecutive spaces → still 2 words
    assert len(words) == 2


def test_extract_word_timestamp_rounding():
    alignment = {
        "characters": ["A", "B"],
        "character_start_times_seconds": [0.0001, 0.1001],
        "character_end_times_seconds":   [0.1001, 0.2001],
    }
    words = _extract_word_timestamps(alignment)
    assert words[0].start == round(0.0001, 3)
    assert words[0].end == round(0.2001, 3)


# ── generate_voice ────────────────────────────────────────────────────────────

def _fake_elevenlabs_response(script: str = "Bonjour.") -> bytes:
    """Build a minimal fake ElevenLabs with-timestamps JSON response."""
    chars = list(script)
    starts = [i * 0.1 for i in range(len(chars))]
    ends = [s + 0.1 for s in starts]
    payload = {
        "audio_base64": base64.b64encode(b"FAKE_MP3_DATA").decode(),
        "alignment": {
            "characters": chars,
            "character_start_times_seconds": starts,
            "character_end_times_seconds": ends,
        },
    }
    return json.dumps(payload).encode()


def test_generate_voice_missing_api_key(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ELEVENLABS_API_KEY"):
        generate_voice("Test", "/tmp")


def test_generate_voice_saves_file(monkeypatch, tmp_path):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el-test-key")

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = json.loads(_fake_elevenlabs_response("Bonjour Marcel."))
    fake_resp.raise_for_status = MagicMock()

    with patch("app.video_pipeline.voice_generator.httpx.Client") as mock_client_cls:
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.post.return_value = fake_resp
        mock_client_cls.return_value = mock_ctx

        result = generate_voice("Bonjour Marcel.", str(tmp_path), filename="test_audio")

    assert result.audio_path.endswith("test_audio.mp3")
    assert (tmp_path / "test_audio.mp3").exists()


def test_generate_voice_returns_word_timestamps(monkeypatch, tmp_path):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el-test-key")

    fake_resp = MagicMock()
    fake_resp.json.return_value = json.loads(_fake_elevenlabs_response("Hi Marcel"))
    fake_resp.raise_for_status = MagicMock()

    with patch("app.video_pipeline.voice_generator.httpx.Client") as mock_client_cls:
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.post.return_value = fake_resp
        mock_client_cls.return_value = mock_ctx

        result = generate_voice("Hi Marcel", str(tmp_path), filename="ts_test")

    assert len(result.word_timestamps) == 2
    assert result.word_timestamps[0].word == "Hi"
    assert result.word_timestamps[1].word == "Marcel"


def test_generate_voice_duration_from_timestamps(monkeypatch, tmp_path):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el-test-key")

    chars = ["A", " ", "B"]
    starts = [0.0, 0.5, 1.0]
    ends =   [0.5, 1.0, 1.8]
    payload = {
        "audio_base64": base64.b64encode(b"DATA").decode(),
        "alignment": {
            "characters": chars,
            "character_start_times_seconds": starts,
            "character_end_times_seconds": ends,
        },
    }
    fake_resp = MagicMock()
    fake_resp.json.return_value = payload
    fake_resp.raise_for_status = MagicMock()

    with patch("app.video_pipeline.voice_generator.httpx.Client") as mock_client_cls:
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.post.return_value = fake_resp
        mock_client_cls.return_value = mock_ctx

        result = generate_voice("A B", str(tmp_path), filename="dur_test")

    assert result.duration_seconds == 1.8


def test_generate_voice_truncates_long_script(monkeypatch, tmp_path):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el-test-key")

    long_script = "X" * 5_000

    fake_resp = MagicMock()
    fake_resp.json.return_value = json.loads(_fake_elevenlabs_response("X"))
    fake_resp.raise_for_status = MagicMock()

    captured = {}

    def fake_post(url, headers, json):  # noqa: A002
        captured["body"] = json
        return fake_resp

    with patch("app.video_pipeline.voice_generator.httpx.Client") as mock_client_cls:
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.post.side_effect = fake_post
        mock_client_cls.return_value = mock_ctx

        generate_voice(long_script, str(tmp_path), filename="trunc_test")

    assert len(captured["body"]["text"]) <= 2_500
