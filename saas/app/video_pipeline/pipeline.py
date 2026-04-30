"""
Video Pipeline Orchestrator.

Ties all four stages together and persists run state to the VideoRun model.
Called by the APScheduler cron job at 08:00 every day.

Flow:
  Stage 1 – car_selector   → CarOfTheDay
  Stage 2 – script_generator → Marcel script (French text)
  Stage 3 – voice_generator  → MP3 + word timestamps
  Stage 4 – video_assembler  → MP4 URL (Shotstack CDN)
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from .car_selector import get_car_of_the_day
from .script_generator import generate_script
from .video_assembler import assemble_video
from .voice_generator import generate_voice

logger = logging.getLogger(__name__)

# Local directories for generated assets.
_AUDIO_DIR = os.environ.get("VIDEO_AUDIO_DIR", "/tmp/autoradar/audio")
_VIDEO_OUTPUT_DIR = os.environ.get("VIDEO_OUTPUT_DIR", "/tmp/autoradar/video")

# Base URL exposed by the FastAPI server for serving local audio files.
# Must be reachable by Shotstack (i.e., the public domain of the server).
_APP_URL = os.environ.get("APP_URL", "http://localhost:8000")


async def run_video_pipeline(db: AsyncSession) -> None:
    """
    Execute the full pipeline and write results to the VideoRun table.
    Errors at any stage are caught and stored so the scheduler keeps running.
    """
    from ..models import VideoRun
    from ..database import SessionLocal

    run = VideoRun(status="running")
    async with SessionLocal() as session:
        session.add(run)
        await session.commit()
        await session.refresh(run)
        run_id = run.id

    try:
        # ── Stage 1 ──────────────────────────────────────────────────────────
        logger.info("[pipeline] Stage 1 – selecting Car of the Day...")
        async with SessionLocal() as session:
            car = await get_car_of_the_day(session)

        if car is None:
            _fail(run_id, "Stage 1: no car found in the latest scan run.")
            return

        # ── Stage 2 ──────────────────────────────────────────────────────────
        logger.info("[pipeline] Stage 2 – generating Marcel script...")
        script = generate_script(car)

        # ── Stage 3 ──────────────────────────────────────────────────────────
        logger.info("[pipeline] Stage 3 – generating voice (ElevenLabs)...")
        stem = f"marcel_{run_id}_{int(time.time())}"
        voice_result = generate_voice(script, _AUDIO_DIR, filename=stem)

        # Build the public URL for the audio file so Shotstack can fetch it.
        audio_filename = Path(voice_result.audio_path).name
        audio_url = f"{_APP_URL.rstrip('/')}/media/audio/{audio_filename}"

        # ── Stage 4 ──────────────────────────────────────────────────────────
        logger.info("[pipeline] Stage 4 – assembling video (Shotstack)...")
        video_url = assemble_video(car, audio_url, voice_result)

        # ── Persist success ───────────────────────────────────────────────────
        async with SessionLocal() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(VideoRun).where(VideoRun.id == run_id)
            )
            run_record = result.scalar_one()
            run_record.status = "done"
            run_record.car_title = f"{car.year} {car.make} {car.model}"
            run_record.script = script
            run_record.audio_url = audio_url
            run_record.video_url = video_url
            await session.commit()

        logger.info("[pipeline] Pipeline complete. Video: %s", video_url)

    except Exception as exc:  # noqa: BLE001
        logger.exception("[pipeline] Pipeline failed for run %d: %s", run_id, exc)
        _fail(run_id, str(exc))


def _fail(run_id: int, message: str) -> None:
    """Synchronously mark a VideoRun as failed (fire-and-forget, best effort)."""
    import asyncio

    async def _update() -> None:
        from ..database import SessionLocal
        from ..models import VideoRun
        from sqlalchemy import select

        async with SessionLocal() as session:
            result = await session.execute(
                select(VideoRun).where(VideoRun.id == run_id)
            )
            record = result.scalar_one_or_none()
            if record:
                record.status = "failed"
                record.error_message = message
                await session.commit()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_update())
        else:
            loop.run_until_complete(_update())
    except Exception as exc:  # noqa: BLE001
        logger.error("[pipeline] Could not persist failure for run %d: %s", run_id, exc)
