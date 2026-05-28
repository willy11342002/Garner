import asyncio
import os
import re
import shutil
import tempfile
from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


def extract_video_id(url: str) -> str | None:
    match = re.search(r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})", url)
    return match.group(1) if match else None


async def _get_video_metadata(url: str) -> tuple[str | None, int | None]:
    """Get video title and duration via yt-dlp (no download)."""
    import yt_dlp

    def _fetch():
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                return info.get("title"), info.get("duration")
            return None, None

    try:
        return await asyncio.to_thread(_fetch)
    except Exception:
        return None, None


async def _get_transcript(video_id: str) -> str | None:
    """Try to get transcript via youtube-transcript-api. Returns None if unavailable."""
    from youtube_transcript_api import YouTubeTranscriptApi

    def _fetch():
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id)
        return " ".join(s.text for s in transcript)

    try:
        return await asyncio.to_thread(_fetch)
    except Exception:
        return None


async def _transcribe_with_whisper(url: str) -> str | None:
    """Download audio via yt-dlp and transcribe with Groq Whisper."""
    import yt_dlp
    from groq import AsyncGroq

    tmpdir = tempfile.mkdtemp()
    audio_base = os.path.join(tmpdir, "audio")

    def _download():
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": audio_base,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "32",  # 32kbps — speech only, keeps file under 25MB
            }],
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    try:
        await asyncio.to_thread(_download)

        audio_path = audio_base + ".mp3"
        if not os.path.exists(audio_path):
            return None

        client = AsyncGroq(api_key=settings.groq_api_key)
        with open(audio_path, "rb") as f:
            result = await client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=f,
            )
        return result.text

    except Exception:
        return None
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


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
) -> tuple[str | None, int | None, int | None, str | None]:
    """
    Fetch YouTube video content for summarization.

    Returns (text, whisper_seconds_used, duration_sec, title).
    whisper_seconds_used is None when transcript was used (no Whisper charge).
    """
    video_id = extract_video_id(url)
    if not video_id:
        return None, None, None, None

    # Always fetch metadata (title + duration) — these are stored regardless of AI result
    title, duration = await _get_video_metadata(url)

    transcript = await _get_transcript(video_id)
    if transcript:
        return transcript, None, duration, title

    # No transcript — try Whisper if quota allows
    if not settings.groq_api_key:
        return None, None, duration, title

    if duration is None:
        return None, None, None, title

    daily_limit = await _get_whisper_daily_limit(db, user_id)
    today_used = await _get_today_used_seconds(db, user_id)

    if today_used + duration > daily_limit:
        return None, None, duration, title

    text = await _transcribe_with_whisper(url)
    if text is None:
        return None, None, duration, title

    return text, duration, duration, title
