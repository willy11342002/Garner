import asyncio
import logging
import os
import re
import shutil
import tempfile
from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_instagram_url(url: str) -> bool:
    return "instagram.com" in url


def extract_shortcode(url: str) -> str | None:
    match = re.search(r"instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]+)", url)
    return match.group(1) if match else None


def normalize_instagram_url(url: str) -> str:
    """Return canonical /p/ URL; pass non-Instagram URLs through unchanged."""
    shortcode = extract_shortcode(url)
    if shortcode:
        return f"https://www.instagram.com/p/{shortcode}/"
    return url


def extract_hashtags(text: str) -> list[str]:
    return re.findall(r"#(\w+)", text)


async def _get_cookies_content(db: AsyncSession) -> str | None:
    from app.models.app_setting import AppSetting
    from sqlalchemy import select

    result = await db.execute(
        select(AppSetting.value).where(AppSetting.key == "instagram_cookies")
    )
    content = result.scalar_one_or_none()
    return content if content and content.strip() else None


def _derive_title(raw_title: str | None, description: str | None, uploader: str | None) -> str | None:
    """Generate a meaningful title from available metadata."""
    # yt-dlp generates "Video by {username}" when Instagram has no explicit title
    if raw_title and not re.match(r"^Video by ", raw_title):
        return raw_title
    # Fall back to first non-empty, non-hashtag line of description
    if description:
        for line in description.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line[:100]
    if uploader:
        return f"@{uploader}"
    return raw_title


async def _get_metadata(url: str, cookies: str | None) -> dict:
    """Extract metadata and thumbnail bytes without downloading the video."""
    import urllib.request

    import yt_dlp

    def _fetch():
        tmpdir = tempfile.mkdtemp()
        try:
            opts = {
                "skip_download": True,
                "quiet": True,
                "no_warnings": True,
            }
            if cookies:
                cookies_path = os.path.join(tmpdir, "cookies.txt")
                with open(cookies_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(cookies.replace("\r\n", "\n").replace("\r", "\n"))
                opts["cookiefile"] = cookies_path

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)

            # Download thumbnail bytes immediately while the CDN URL is still fresh
            thumbnail_bytes: bytes | None = None
            thumbnail_url: str | None = info.get("thumbnail")
            if thumbnail_url:
                try:
                    req = urllib.request.Request(
                        thumbnail_url,
                        headers={"User-Agent": "Mozilla/5.0"},
                    )
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        thumbnail_bytes = resp.read()
                    logger.info("IG thumbnail downloaded: %d bytes", len(thumbnail_bytes))
                except Exception:
                    logger.warning("IG thumbnail download failed for url=%s", thumbnail_url, exc_info=True)

            raw_title = info.get("title")
            description = info.get("description")
            uploader = info.get("uploader")

            return {
                "title": _derive_title(raw_title, description, uploader),
                "description": description,
                "duration": info.get("duration"),
                "thumbnail_bytes": thumbnail_bytes,
                "uploader": uploader,
            }
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    try:
        return await asyncio.to_thread(_fetch)
    except Exception:
        logger.exception("yt-dlp metadata failed for url=%s", url)
        return {}


async def _transcribe_with_whisper(url: str, cookies: str | None) -> tuple[str | None, int | None]:
    """Download audio and transcribe with Whisper. Returns (text, duration_sec)."""
    import yt_dlp
    from groq import AsyncGroq

    if not settings.groq_api_key:
        logger.warning("GROQ_API_KEY not set, skipping Whisper")
        return None, None

    tmpdir = tempfile.mkdtemp()
    audio_base = os.path.join(tmpdir, "audio")

    def _download():
        opts = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl": audio_base,
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "32"}
            ],
            "quiet": True,
            "no_warnings": True,
        }
        if cookies:
            cookies_path = os.path.join(tmpdir, "cookies.txt")
            with open(cookies_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(cookies.replace("\r\n", "\n").replace("\r", "\n"))
            opts["cookiefile"] = cookies_path

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return info.get("duration") if info else None

    try:
        duration = await asyncio.to_thread(_download)
        audio_path = audio_base + ".mp3"
        if not os.path.exists(audio_path):
            logger.warning("Audio file not found after download for url=%s", url)
            return None, duration

        client = AsyncGroq(api_key=settings.groq_api_key)
        with open(audio_path, "rb") as f:
            result = await client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=f,
            )
        text = result.text.strip() or None
        return text, duration
    except Exception:
        logger.exception("Whisper transcription failed for url=%s", url)
        return None, None
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


async def _get_whisper_daily_limit(db: AsyncSession, user_id: UUID) -> int:
    from sqlalchemy import select

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
    from sqlalchemy import func, select

    from app.models.whisper_usage import WhisperUsage

    result = await db.execute(
        select(func.coalesce(func.sum(WhisperUsage.used_seconds), 0)).where(
            WhisperUsage.user_id == user_id,
            WhisperUsage.date == date.today(),
        )
    )
    return result.scalar_one()


async def fetch_content(
    db: AsyncSession,
    user_id: UUID,
    url: str,
    stage_cb=None,
) -> tuple[str | None, int | None, int | None, str | None, bytes | None]:
    """
    Fetch Instagram Reel content.

    Returns (text, whisper_seconds_used, duration_sec, title, thumbnail_bytes).
    text combines [Caption] + [Audio] sections when both are available.
    """
    if stage_cb:
        stage_cb("fetching_info")

    cookies = await _get_cookies_content(db)
    metadata = await _get_metadata(url, cookies)

    title = metadata.get("title")
    description = metadata.get("description")
    thumbnail_bytes = metadata.get("thumbnail_bytes")
    duration = metadata.get("duration")
    logger.info("IG metadata: title=%r description_len=%s duration=%s", title, len(description or ""), duration)

    if stage_cb:
        stage_cb("fetching_content")

    # Check Whisper quota before downloading
    if duration is not None:
        daily_limit = await _get_whisper_daily_limit(db, user_id)
        today_used = await _get_today_used_seconds(db, user_id)
        logger.info("Whisper quota check: used=%s limit=%s duration=%s", today_used, daily_limit, duration)

        if today_used + duration > daily_limit:
            logger.warning("Whisper daily quota exceeded for user_id=%s", user_id)
            if description and description.strip():
                return description.strip(), None, duration, title, thumbnail_bytes
            return None, None, duration, title, thumbnail_bytes

    transcript, whisper_duration = await _transcribe_with_whisper(url, cookies)
    logger.info("IG whisper: transcript_len=%s whisper_duration=%s", len(transcript or ""), whisper_duration)
    actual_duration = whisper_duration or duration

    parts: list[str] = []
    if description and description.strip():
        parts.append(f"[Caption]\n{description.strip()}")
    if transcript:
        parts.append(f"[Audio]\n{transcript}")

    raw_content = "\n\n".join(parts) if parts else None

    whisper_seconds = actual_duration if transcript else None
    return raw_content, whisper_seconds, actual_duration, title, thumbnail_bytes
