"""
Stage 3 – Voice Generation.

Sends the Marcel script to ElevenLabs TTS and returns:
  • An MP3 audio file saved locally.
  • Word-level timestamps derived from the character alignment data.

Recommended voice: a deep, sophisticated European French male voice.
Set ELEVENLABS_VOICE_ID to the ElevenLabs voice ID of your choice.

Suggested voices (ElevenLabs Voice Library):
  - "Luc"    – deep French male, ID varies by account (use library search)
  - "Xavier" – refined French accent, ID varies
The default fallback ID below is the public ElevenLabs "Adam" multilingual voice;
replace it with a French-specific voice ID for best results.
"""
from __future__ import annotations

import base64
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"
# Fallback voice ID (ElevenLabs "Adam" – multilingual).
# Override with a deep French male voice via ELEVENLABS_VOICE_ID env var.
_DEFAULT_VOICE_ID = "pNInz6obpgDQGcFmaJgB"
_MODEL_ID = "eleven_multilingual_v2"

# Maximum characters per TTS call (ElevenLabs free tier: 10 000 chars/month).
_MAX_CHARS = 2_500


@dataclass
class WordTimestamp:
    word: str
    start: float
    end: float


@dataclass
class VoiceResult:
    audio_path: str
    duration_seconds: float
    word_timestamps: list[WordTimestamp] = field(default_factory=list)


def _extract_word_timestamps(alignment: dict) -> list[WordTimestamp]:
    """
    Convert ElevenLabs character-level alignment data into word-level timestamps.

    The alignment dict contains parallel lists:
      characters, character_start_times_seconds, character_end_times_seconds
    """
    chars: list[str] = alignment.get("characters", [])
    starts: list[float] = alignment.get("character_start_times_seconds", [])
    ends: list[float] = alignment.get("character_end_times_seconds", [])

    if not chars:
        return []

    words: list[WordTimestamp] = []
    current_word: list[str] = []
    word_start: Optional[float] = None
    word_end: float = 0.0

    for char, start, end in zip(chars, starts, ends):
        if char in (" ", "\n", "\t"):
            if current_word and word_start is not None:
                words.append(
                    WordTimestamp(
                        word="".join(current_word),
                        start=round(word_start, 3),
                        end=round(word_end, 3),
                    )
                )
                current_word = []
                word_start = None
        else:
            if not current_word:
                word_start = start
            current_word.append(char)
            word_end = end

    # Flush last word
    if current_word and word_start is not None:
        words.append(
            WordTimestamp(
                word="".join(current_word),
                start=round(word_start, 3),
                end=round(word_end, 3),
            )
        )

    return words


def generate_voice(
    script: str,
    output_dir: str,
    filename: Optional[str] = None,
) -> VoiceResult:
    """
    Call ElevenLabs TTS with timestamp alignment and save the audio locally.

    Args:
        script:     The Marcel script text (French).
        output_dir: Directory where the MP3 will be saved.
        filename:   Optional filename stem (no extension). Defaults to timestamp.

    Returns:
        VoiceResult with the local audio path, duration, and word timestamps.

    Raises:
        ValueError: If ELEVENLABS_API_KEY is missing.
        httpx.HTTPStatusError: On API errors.
    """
    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY environment variable is not set.")

    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", _DEFAULT_VOICE_ID)

    if len(script) > _MAX_CHARS:
        logger.warning(
            "[voice_generator] Script is %d chars, truncating to %d.",
            len(script), _MAX_CHARS,
        )
        script = script[:_MAX_CHARS]

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    stem = filename or f"marcel_{int(time.time())}"
    audio_path = str(Path(output_dir) / f"{stem}.mp3")

    url = f"{_ELEVENLABS_BASE}/text-to-speech/{voice_id}/with-timestamps"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }
    body = {
        "text": script,
        "model_id": _MODEL_ID,
        "voice_settings": {
            "stability": 0.55,
            "similarity_boost": 0.80,
            "style": 0.25,
            "use_speaker_boost": True,
        },
    }

    with httpx.Client(timeout=60) as client:
        resp = client.post(url, headers=headers, json=body)
        resp.raise_for_status()

    data = resp.json()
    audio_bytes = base64.b64decode(data["audio_base64"])

    with open(audio_path, "wb") as f:
        f.write(audio_bytes)

    alignment = data.get("alignment") or data.get("normalized_alignment", {})
    word_timestamps = _extract_word_timestamps(alignment)

    # Estimate duration from last word timestamp; fall back to file size heuristic.
    duration = 0.0
    if word_timestamps:
        duration = word_timestamps[-1].end
    if duration == 0.0 and len(audio_bytes) > 0:
        # ~128 kbps MP3: bytes / (128_000 / 8) ≈ bytes / 16_000
        duration = round(len(audio_bytes) / 16_000, 1)

    logger.info(
        "[voice_generator] Audio saved to %s (%.1fs, %d words with timestamps).",
        audio_path, duration, len(word_timestamps),
    )
    return VoiceResult(
        audio_path=audio_path,
        duration_seconds=duration,
        word_timestamps=word_timestamps,
    )
