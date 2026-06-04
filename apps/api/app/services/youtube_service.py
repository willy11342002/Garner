import asyncio
import logging
import re
from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)


def extract_video_id(url: str) -> str | None:
    match = re.search(r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})", url)
    return match.group(1) if match else None


async def _get_video_metadata(video_id: str) -> tuple[str | None, int | None]:
    """Get video title and duration via YouTube Data API v3."""
    import httpx

    if not settings.youtube_api_key:
        logger.warning("YOUTUBE_API_KEY not set, cannot fetch video metadata")
        return None, None

    api_url = (
        "https://www.googleapis.com/youtube/v3/videos"
        f"?part=snippet,contentDetails&id={video_id}&key={settings.youtube_api_key}"
    )
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(api_url)
            r.raise_for_status()
            data = r.json()

        items = data.get("items", [])
        if not items:
            return None, None

        item = items[0]
        title = item["snippet"]["title"]
        duration = _parse_iso8601_duration(item["contentDetails"]["duration"])
        return title, duration

    except Exception:
        logger.exception("YouTube Data API failed for video_id=%s", video_id)
        return None, None


def _parse_iso8601_duration(duration: str) -> int:
    """Convert ISO 8601 duration (PT1H2M3S) to seconds."""
    match = re.fullmatch(
        r"P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration
    )
    if not match:
        return 0
    days, hours, minutes, seconds = (int(x or 0) for x in match.groups())
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


async def _get_transcript(video_id: str) -> str | None:
    """Get transcript via yt-dlp, fallback to youtube-transcript-api."""
    import json
    import os
    import tempfile

    import yt_dlp

    def _fetch_ytdlp():
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["zh-Hant", "zh-TW", "zh-Hans", "zh-CN", "en"],
                "subtitlesformat": "json3",
                "outtmpl": os.path.join(tmpdir, "%(id)s"),
                "quiet": True,
                "no_warnings": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

            files = os.listdir(tmpdir)
            for lang in ["zh-Hant", "zh-TW", "zh-Hans", "zh-CN", "en"]:
                for fname in files:
                    if f".{lang}." in fname and fname.endswith(".json3"):
                        return _parse_json3(os.path.join(tmpdir, fname))
            for fname in files:
                if fname.endswith(".json3"):
                    return _parse_json3(os.path.join(tmpdir, fname))
        return None

    def _parse_json3(path: str) -> str | None:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        texts = [
            seg.get("utf8", "").strip()
            for event in data.get("events", [])
            for seg in event.get("segs", [])
            if seg.get("utf8", "").strip() not in ("", "\n")
        ]
        return " ".join(texts) or None

    try:
        result = await asyncio.to_thread(_fetch_ytdlp)
        if result:
            return result
    except Exception:
        logger.warning("yt-dlp transcript failed for video_id=%s, falling back", video_id)

    from youtube_transcript_api import YouTubeTranscriptApi

    def _fetch_api():
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id)
        return " ".join(s.text for s in transcript)

    try:
        return await asyncio.to_thread(_fetch_api)
    except Exception:
        return None


async def _transcribe_with_whisper(url: str) -> str | None:
    """Transcribe audio by calling the Cloud Run transcriber service."""
    import httpx

    if not settings.transcriber_url:
        logger.warning("TRANSCRIBER_URL not set, skipping Whisper")
        return None

    try:
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(
                f"{settings.transcriber_url.rstrip('/')}/transcribe",
                json={"url": url},
                headers={"x-api-key": settings.transcriber_secret},
            )
            r.raise_for_status()
            return r.json().get("text")
    except Exception:
        logger.exception("Cloud Run transcriber failed for url=%s", url)
        return None


async def _get_whisper_daily_limit(db: AsyncSession, user_id: UUID) -> int:
    from app.models.plan import Plan
    from app.models.subscription import Subscription, SubscriptionStatus

    result = await db.execute(
        select(Plan.whisper_daily_limit_seconds)
        .join(Subscription, Subscription.plan_id == Plan.id)
        .where(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.active,
        )
    )
    limit = result.scalar_one_or_none()
    return limit if limit is not None else settings.free_whisper_daily_seconds


async def _get_today_used_seconds(db: AsyncSession, user_id: UUID) -> int:
    from app.models.whisper_usage import WhisperUsage

    result = await db.execute(
        select(func.coalesce(func.sum(WhisperUsage.used_seconds), 0)).where(
            WhisperUsage.user_id == user_id,
            WhisperUsage.date == date.today(),
        )
    )
    return result.scalar_one()


async def fetch_content(
    db: AsyncSession, user_id: UUID, url: str
) -> tuple[str | None, int | None, int | None, str | None, str | None]:
    """
    Fetch YouTube video content for summarization.

    Returns (text, whisper_seconds_used, duration_sec, title, transcription_source).
    transcription_source is "transcript", "whisper", or None if no content was fetched.
    whisper_seconds_used is None when transcript was used (no Whisper charge).
    """
    video_id = extract_video_id(url)
    if not video_id:
        return None, None, None, None, None

    # Always fetch metadata (title + duration) — these are stored regardless of AI result
    title, duration = await _get_video_metadata(video_id)

    transcript = await _get_transcript(video_id)
    if transcript:
        return transcript, None, duration, title, "transcript"

    # No transcript — try Whisper if quota allows
    logger.info("No transcript for video_id=%s, title=%r, duration=%s", video_id, title, duration)

    if not settings.groq_api_key:
        logger.warning("GROQ_API_KEY not set, skipping Whisper")
        return None, None, duration, title, None

    if duration is None:
        logger.warning("duration is None for video_id=%s, cannot check quota, skipping Whisper", video_id)
        return None, None, None, title, None

    daily_limit = await _get_whisper_daily_limit(db, user_id)
    today_used = await _get_today_used_seconds(db, user_id)
    logger.info("Whisper quota check: used=%s limit=%s duration=%s", today_used, daily_limit, duration)

    if today_used + duration > daily_limit:
        logger.warning("Whisper daily quota exceeded for user_id=%s", user_id)
        return None, None, duration, title, None

    logger.info("Starting Whisper transcription for video_id=%s", video_id)
    text = await _transcribe_with_whisper(url)
    if text is None:
        logger.warning("Whisper transcription returned None for video_id=%s", video_id)
        return None, None, duration, title, None

    return text, duration, duration, title, "whisper"
