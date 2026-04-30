"""
Stage 4 – Programmatic Video Assembly via Shotstack.

Produces a 9:16 (1080 × 1920) vertical video with:
  • Background: car image with Ken Burns slow-zoom effect.
  • Gradient overlay: bottom-to-top dark fade for caption readability.
  • Opening banner: car make/model/year slides in from the top.
  • Caption track: bold, animated word-group captions synced to the voiceover.
  • Score card: Autoradar reliability / price / overall scores pop up mid-video.
  • Outro: Autoradar logo / title for the last 4 seconds.

API: Shotstack v1  (https://api.shotstack.io/v1)
Pricing: ~$0.05–0.10 per render on the Developer plan ($49/month / 250 renders).
Sandbox renders are free but watermarked.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional

import httpx

from .car_selector import CarOfTheDay
from .voice_generator import VoiceResult, WordTimestamp

logger = logging.getLogger(__name__)

_SHOTSTACK_BASE = "https://api.shotstack.io"
# Captions: group this many words per caption frame.
_WORDS_PER_CAPTION = 3
# Minimum caption display time in seconds.
_MIN_CAPTION_DURATION = 0.4
# Poll interval and max wait when querying render status.
_POLL_INTERVAL_S = 5
_MAX_POLL_ATTEMPTS = 60  # 5 min total

# ── HTML / CSS constants ──────────────────────────────────────────────────────

_CAPTION_CSS = (
    "font-family:'Arial Black',Impact,sans-serif;"
    "font-size:80px;"
    "font-weight:900;"
    "color:#FFD700;"
    "-webkit-text-stroke:4px #000000;"
    "text-shadow:4px 4px 12px rgba(0,0,0,0.9);"
    "text-align:center;"
    "text-transform:uppercase;"
    "line-height:1.1;"
    "padding:0 40px;"
)

_SCORE_CARD_HTML = """<div style="
    background:linear-gradient(135deg,rgba(0,0,0,0.92) 0%,rgba(20,20,20,0.95) 100%);
    border:3px solid #FFD700;
    border-radius:24px;
    padding:40px 50px;
    font-family:'Arial Black',Impact,sans-serif;
    color:#FFFFFF;
    text-align:center;
    width:880px;
">
  <div style="font-size:28px;letter-spacing:4px;color:#FFD700;margin-bottom:16px;">AUTORADAR SCORE</div>
  <div style="font-size:120px;font-weight:900;color:#FFD700;line-height:1;">{{overall}}</div>
  <div style="font-size:24px;margin-bottom:24px;color:#AAAAAA;">/ 100</div>
  <div style="display:flex;justify-content:space-around;margin-top:10px;">
    <div>
      <div style="font-size:22px;color:#AAA;">FIABILITÉ</div>
      <div style="font-size:52px;font-weight:900;color:#4CAF50;">{{reliability}}</div>
    </div>
    <div style="border-left:2px solid #333;"></div>
    <div>
      <div style="font-size:22px;color:#AAA;">PRIX</div>
      <div style="font-size:52px;font-weight:900;color:#2196F3;">{{price_score}}</div>
    </div>
  </div>
</div>"""

_OUTRO_HTML = """<div style="
    font-family:'Arial Black',Impact,sans-serif;
    text-align:center;
    color:#FFFFFF;
">
  <div style="font-size:96px;font-weight:900;color:#FFD700;letter-spacing:-2px;">Autoradar</div>
  <div style="font-size:34px;margin-top:12px;color:#DDDDDD;letter-spacing:2px;">TROUVE LE MEILLEUR DEAL</div>
  <div style="font-size:28px;margin-top:24px;background:#FFD700;color:#000;padding:12px 40px;border-radius:50px;display:inline-block;">
    Abonne-toi maintenant ↓
  </div>
</div>"""


# ── Caption helpers ───────────────────────────────────────────────────────────

def _group_captions(
    words: list[WordTimestamp],
    group_size: int = _WORDS_PER_CAPTION,
) -> list[tuple[str, float, float]]:
    """
    Group word timestamps into (text, start, end) caption segments.
    Each segment holds `group_size` consecutive words.
    """
    groups: list[tuple[str, float, float]] = []
    for i in range(0, len(words), group_size):
        chunk = words[i : i + group_size]
        text = " ".join(w.word for w in chunk).upper()
        start = chunk[0].start
        end = chunk[-1].end
        duration = max(_MIN_CAPTION_DURATION, end - start)
        groups.append((text, start, duration))
    return groups


# ── Shotstack clip builders ───────────────────────────────────────────────────

def _html_asset(html: str, width: int, height: int) -> dict:
    return {"type": "html", "html": html, "width": width, "height": height}


def _image_clip(src: str, start: float, length: float) -> dict:
    return {
        "asset": {"type": "image", "src": src},
        "start": start,
        "length": length,
        "effect": "zoomIn",
        "fit": "cover",
        "position": "center",
    }


def _audio_clip(src: str, length: float) -> dict:
    return {
        "asset": {"type": "audio", "src": src, "effect": "fadeOut", "volume": 1.0},
        "start": 0.0,
        "length": length,
    }


def _caption_clip(text: str, start: float, duration: float) -> dict:
    html = f'<p style="{_CAPTION_CSS}">{text}</p>'
    return {
        "asset": _html_asset(html, 1000, 240),
        "start": start,
        "length": duration,
        "position": "bottom",
        "offset": {"x": 0.0, "y": 0.12},
        "transition": {"in": "fade", "out": "fade"},
    }


def _opening_banner_clip(car: CarOfTheDay, duration: float = 5.0) -> dict:
    html = (
        f'<div style="'
        f"background:rgba(0,0,0,0.75);border-radius:16px;padding:20px 40px;"
        f"font-family:'Arial Black',Impact,sans-serif;color:#FFD700;"
        f'text-align:center;">'
        f'<div style="font-size:52px;font-weight:900;">'
        f"{car.year} {car.make.upper()} {car.model.upper()}"
        f"</div>"
        f'<div style="font-size:34px;color:#FFFFFF;margin-top:8px;">'
        f"{car.mileage_km:,} km &nbsp;•&nbsp; {car.price_eur:,} €"
        f"</div>"
        f"</div>"
    )
    return {
        "asset": _html_asset(html, 1000, 200),
        "start": 0.5,
        "length": duration,
        "position": "top",
        "offset": {"x": 0.0, "y": -0.08},
        "transition": {"in": "slideDown", "out": "fade"},
    }


def _score_card_clip(
    car: CarOfTheDay,
    start: float,
    duration: float = 6.0,
) -> dict:
    html = (
        _SCORE_CARD_HTML
        .replace("{{overall}}", str(int(car.overall_score)))
        .replace("{{reliability}}", str(int(car.reliability_score)))
        .replace("{{price_score}}", str(int(car.price_score)))
    )
    return {
        "asset": _html_asset(html, 980, 560),
        "start": start,
        "length": duration,
        "position": "center",
        "transition": {"in": "slideUp", "out": "slideDown"},
    }


def _gradient_overlay_clip(length: float) -> dict:
    html = (
        '<div style="'
        "width:1080px;height:1920px;"
        "background:linear-gradient("
        "to top,"
        "rgba(0,0,0,0.75) 0%,"
        "rgba(0,0,0,0.25) 35%,"
        "rgba(0,0,0,0.0) 60%,"
        "rgba(0,0,0,0.35) 100%"
        ");"
        '"></div>'
    )
    return {
        "asset": _html_asset(html, 1080, 1920),
        "start": 0.0,
        "length": length,
        "position": "center",
    }


def _outro_clip(start: float, duration: float = 4.0) -> dict:
    logo_url = os.environ.get("AUTORADAR_LOGO_URL", "")
    if logo_url:
        return {
            "asset": {"type": "image", "src": logo_url},
            "start": start,
            "length": duration,
            "position": "center",
            "fit": "contain",
            "transition": {"in": "fade", "out": "fade"},
        }
    return {
        "asset": _html_asset(_OUTRO_HTML, 960, 400),
        "start": start,
        "length": duration,
        "position": "center",
        "transition": {"in": "fade", "out": "fade"},
    }


# ── Shotstack edit builder ────────────────────────────────────────────────────

def build_shotstack_edit(
    car: CarOfTheDay,
    audio_url: str,
    voice_result: VoiceResult,
) -> dict:
    """
    Compose the full Shotstack edit JSON payload for a 9:16 vertical video.
    """
    total = voice_result.duration_seconds
    # Give a 4-second outro at the end.
    outro_start = max(total - 0.5, total - 4.0) if total > 5 else total
    total_with_outro = outro_start + 4.0

    # Score card appears after the first 30% of the voiceover.
    score_start = round(total * 0.30, 1)
    score_duration = min(6.0, total * 0.25)

    # Caption clips
    caption_clips: list[dict] = []
    if voice_result.word_timestamps:
        for text, start, duration in _group_captions(voice_result.word_timestamps):
            caption_clips.append(_caption_clip(text, start, duration))
    else:
        # No timestamps: single static caption with the first 60 chars.
        preview_text = voice_result.audio_path  # will be replaced; just a fallback.
        caption_clips.append(_caption_clip("AUTORADAR", 0.0, total))

    tracks = [
        # Track order in Shotstack = bottom layer first.
        {"clips": [_image_clip(car.image_url, 0.0, total_with_outro)]},
        {"clips": [_gradient_overlay_clip(total_with_outro)]},
        {"clips": [_opening_banner_clip(car)]},
        {"clips": caption_clips},
        {"clips": [_score_card_clip(car, score_start, score_duration)]},
        {"clips": [_outro_clip(outro_start)]},
        {"clips": [_audio_clip(audio_url, total_with_outro)]},
    ]

    return {
        "timeline": {"tracks": tracks},
        "output": {
            "format": "mp4",
            "size": {"width": 1080, "height": 1920},
            "fps": 30,
            "quality": "high",
        },
    }


# ── Shotstack API calls ───────────────────────────────────────────────────────

def _shotstack_headers(api_key: str) -> dict:
    return {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _ingest_audio(api_key: str, audio_url: str, stage: str) -> str:
    """
    Submit an audio URL to Shotstack Ingest so it becomes a Shotstack CDN URL.
    Returns the Shotstack source ID (used as the audio src in the edit).
    """
    ingest_url = f"https://api.shotstack.io/ingest/{stage}/sources"
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            ingest_url,
            headers=_shotstack_headers(api_key),
            json={"url": audio_url},
        )
        resp.raise_for_status()
    source_id = resp.json()["data"]["id"]
    # Poll until ingest is ready.
    status_url = f"{ingest_url}/{source_id}"
    for _ in range(30):
        time.sleep(3)
        with httpx.Client(timeout=15) as client:
            r = client.get(status_url, headers=_shotstack_headers(api_key))
            r.raise_for_status()
        info = r.json()["data"]["attributes"]
        if info.get("status") == "ready":
            return info["source"]
        if info.get("status") == "failed":
            raise RuntimeError(f"Shotstack ingest failed: {info}")
    raise TimeoutError("Shotstack ingest did not complete in time.")


def submit_render(
    car: CarOfTheDay,
    audio_url: str,
    voice_result: VoiceResult,
) -> str:
    """
    Submit a render job to Shotstack and return the render ID.
    """
    api_key = os.environ.get("SHOTSTACK_API_KEY", "")
    if not api_key:
        raise ValueError("SHOTSTACK_API_KEY environment variable is not set.")

    stage = os.environ.get("SHOTSTACK_STAGE", "v1")  # "v1" or "stage"
    render_url = f"{_SHOTSTACK_BASE}/{stage}/render"

    edit = build_shotstack_edit(car, audio_url, voice_result)

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            render_url,
            headers=_shotstack_headers(api_key),
            json={"timeline": edit["timeline"], "output": edit["output"]},
        )
        resp.raise_for_status()

    render_id: str = resp.json()["response"]["id"]
    logger.info("[video_assembler] Render submitted: %s", render_id)
    return render_id


def poll_render(render_id: str) -> str:
    """
    Poll Shotstack until the render is done.  Returns the final video URL.
    Raises RuntimeError if the render fails; TimeoutError if it takes too long.
    """
    api_key = os.environ.get("SHOTSTACK_API_KEY", "")
    stage = os.environ.get("SHOTSTACK_STAGE", "v1")
    status_url = f"{_SHOTSTACK_BASE}/{stage}/render/{render_id}"
    headers = _shotstack_headers(api_key)

    for attempt in range(_MAX_POLL_ATTEMPTS):
        time.sleep(_POLL_INTERVAL_S)
        with httpx.Client(timeout=15) as client:
            resp = client.get(status_url, headers=headers)
            resp.raise_for_status()

        data = resp.json()["response"]
        status = data.get("status", "")
        logger.debug("[video_assembler] Render %s – attempt %d – status: %s", render_id, attempt + 1, status)

        if status == "done":
            url: str = data["url"]
            logger.info("[video_assembler] Render complete: %s", url)
            return url
        if status == "failed":
            raise RuntimeError(
                f"Shotstack render {render_id} failed: {data.get('error', 'unknown error')}"
            )

    raise TimeoutError(f"Shotstack render {render_id} did not complete within {_MAX_POLL_ATTEMPTS * _POLL_INTERVAL_S}s.")


def assemble_video(
    car: CarOfTheDay,
    audio_url: str,
    voice_result: VoiceResult,
) -> str:
    """
    Full Stage 4 entry point.  Submits and polls a Shotstack render.

    Args:
        car:          CarOfTheDay payload (images, scores).
        audio_url:    Publicly accessible URL to the ElevenLabs MP3.
        voice_result: Word timestamps and duration from Stage 3.

    Returns:
        The Shotstack CDN URL of the completed MP4 video.
    """
    render_id = submit_render(car, audio_url, voice_result)
    return poll_render(render_id)
