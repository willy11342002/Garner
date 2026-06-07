import asyncio
import logging
import os
import re
from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)

from app.core.exceptions import VideoTooLongError  # noqa: E402  (after logger)


def extract_video_id(url: str) -> str | None:
    match = re.search(r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})", url)
    return match.group(1) if match else None


def normalize_youtube_url(url: str) -> str:
    """Return canonical watch?v= URL; pass non-YouTube URLs through unchanged."""
    video_id = extract_video_id(url)
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return url


async def _get_video_metadata(video_id: str) -> tuple[str | None, int | None, str | None]:
    """Get video title, duration (seconds), and description via YouTube Data API v3."""
    import httpx

    if not settings.youtube_api_key:
        logger.warning("YOUTUBE_API_KEY not set, cannot fetch video metadata")
        return None, None, None

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
            return None, None, None

        item = items[0]
        title = item["snippet"]["title"]
        description = (item["snippet"].get("description") or "").strip()
        duration = _parse_iso8601_duration(item["contentDetails"]["duration"])
        return title, duration, description

    except Exception:
        logger.exception("YouTube Data API failed for video_id=%s", video_id)
        return None, None, None


def _parse_iso8601_duration(duration: str) -> int:
    """Convert ISO 8601 duration (PT1H2M3S) to seconds."""
    match = re.fullmatch(
        r"P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration
    )
    if not match:
        return 0
    days, hours, minutes, seconds = (int(x or 0) for x in match.groups())
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


async def _get_cookies_content(db: AsyncSession) -> str | None:
    from app.models.app_setting import AppSetting
    from sqlalchemy import select

    result = await db.execute(select(AppSetting.value).where(AppSetting.key == "youtube_cookies"))
    content = result.scalar_one_or_none()
    return content if content and content.strip() else None


_MAX_VIDEO_BYTES = 50 * 1024 * 1024  # 50 MB — clips longer than ~12 min at 480p are skipped


async def _download_video_and_audio(
    url: str,
    cookies: str | None,
) -> tuple[bytes | None, bytes | None, int | None, str]:
    """Download YouTube video (≤ 50 MB) and extract a separate audio track.

    Returns (video_bytes, audio_bytes, duration_sec, mime_type).
    video_bytes is None when yt-dlp aborts due to the size cap.
    audio_bytes is None when FFmpeg audio extraction fails.
    """
    import shutil
    import subprocess
    import tempfile

    import yt_dlp

    tmpdir = tempfile.mkdtemp()

    def _run() -> tuple[bytes | None, bytes | None, int | None, str]:
        video_base = os.path.join(tmpdir, "video")
        audio_path = os.path.join(tmpdir, "audio.mp3")

        ydl_opts = {
            # logged-in YouTube returns adaptive streams (separate video+audio);
            # fall back to combined streams for unauthenticated requests
            "format": (
                "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]"
                "/bestvideo[height<=480]+bestaudio"
                "/best[height<=480]/best"
            ),
            "outtmpl": video_base + ".%(ext)s",
            "quiet": True,
            "no_warnings": True,
            "max_filesize": _MAX_VIDEO_BYTES,
        }
        if cookies:
            cookies_path = os.path.join(tmpdir, "cookies.txt")
            with open(cookies_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(cookies.replace("\r\n", "\n").replace("\r", "\n"))
            ydl_opts["cookiefile"] = cookies_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    return None, None, None, "video/mp4"
                duration = info.get("duration")
                ext = info.get("ext", "mp4")
        except Exception as exc:
            logger.info("_download_video_and_audio: skipped (%s)", exc)
            return None, None, None, "video/mp4"

        video_path = video_base + f".{ext}"
        if not os.path.exists(video_path):
            return None, None, None, f"video/{ext}"

        with open(video_path, "rb") as f:
            video_bytes = f.read()

        subprocess.run(
            ["ffmpeg", "-i", video_path, "-vn", "-acodec", "mp3", "-ab", "32k",
             audio_path, "-y", "-loglevel", "error"],
            capture_output=True, timeout=60,
        )
        audio_bytes: bytes | None = None
        if os.path.exists(audio_path):
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()

        return video_bytes, audio_bytes, duration, f"video/{ext}"

    try:
        return await asyncio.to_thread(_run)
    except Exception:
        logger.warning("_download_video_and_audio failed for url=%s", url, exc_info=True)
        return None, None, None, "video/mp4"
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


async def _get_transcript(video_id: str, cookies: str | None) -> str | None:
    """Get transcript via yt-dlp with cookies."""
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
            if cookies:
                cookies_path = os.path.join(tmpdir, "cookies.txt")
                with open(cookies_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(cookies.replace("\r\n", "\n").replace("\r", "\n"))
                ydl_opts["cookiefile"] = cookies_path

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
        result = " ".join(texts).strip()
        return result if len(result) >= 20 else None

    try:
        return await asyncio.to_thread(_fetch_ytdlp)
    except Exception:
        logger.warning("yt-dlp transcript failed for video_id=%s", video_id)
        return None


async def _transcribe_with_whisper(url: str, cookies: str | None) -> str | None:
    import shutil
    import tempfile

    import yt_dlp
    from groq import AsyncGroq

    if not settings.groq_api_key:
        logger.warning("GROQ_API_KEY not set, skipping Whisper")
        return None

    tmpdir = tempfile.mkdtemp()
    audio_base = os.path.join(tmpdir, "audio")

    def _download():
        ydl_opts = {
            # bestaudio[ext=webm/m4a] covers Shorts which have no audio-only stream
            "format": "bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best[height<=480]/best",
            "outtmpl": audio_base,
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "32"}],
            "quiet": True,
            "no_warnings": True,
        }
        if cookies:
            cookies_path = os.path.join(tmpdir, "cookies.txt")
            with open(cookies_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(cookies.replace("\r\n", "\n").replace("\r", "\n"))
            ydl_opts["cookiefile"] = cookies_path

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return info.get("duration") if info else None

    try:
        duration = await asyncio.to_thread(_download)
        audio_path = audio_base + ".mp3"
        if not os.path.exists(audio_path):
            return None

        client = AsyncGroq(api_key=settings.groq_api_key)
        with open(audio_path, "rb") as f:
            result = await client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=f,
            )
        return result.text.strip() or None
    except Exception:
        logger.exception("Whisper transcription failed for url=%s", url)
        return None
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


async def _whisper_from_audio_bytes(audio_bytes: bytes) -> str | None:
    """Transcribe audio bytes with Groq Whisper without touching the filesystem."""
    import io

    from groq import AsyncGroq

    if not settings.groq_api_key or not audio_bytes:
        return None
    try:
        client = AsyncGroq(api_key=settings.groq_api_key)
        result = await client.audio.transcriptions.create(
            model="whisper-large-v3-turbo",
            file=("audio.mp3", io.BytesIO(audio_bytes)),
        )
        return result.text.strip() or None
    except Exception:
        logger.exception("_whisper_from_audio_bytes failed")
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
    db: AsyncSession,
    user_id: UUID,
    url: str,
    stage_cb=None,
    max_duration_sec: int = 1200,
) -> tuple[str | None, int | None, int | None, str | None, str | None]:
    """Fetch YouTube video content for summarisation.

    Sources collected in parallel:
      • YouTube Data API  — title, duration, description
      • yt-dlp subtitles  — CC transcript
      • yt-dlp + Gemini   — native video understanding (visual text + audio)
      • Groq Whisper      — audio fallback when no CC transcript

    Returns (raw_content, whisper_seconds_used, duration_sec, title, transcription_source).
    """
    video_id = extract_video_id(url)
    if not video_id:
        return None, None, None, None, None

    if stage_cb: stage_cb("fetching_info")
    title, duration, description = await _get_video_metadata(video_id)

    if duration is None or duration > max_duration_sec:
        raise VideoTooLongError(duration)

    cookies = await _get_cookies_content(db)

    if stage_cb: stage_cb("fetching_content")

    # Run CC transcript fetch and video download concurrently
    transcript_task = asyncio.create_task(_get_transcript(video_id, cookies))
    video_task = asyncio.create_task(_download_video_and_audio(url, cookies))

    transcript, video_result = await asyncio.gather(transcript_task, video_task)
    video_bytes, audio_bytes, actual_duration, mime_type = video_result
    duration = actual_duration or duration

    from app.services import ai_service

    parts: list[str] = []
    if description:
        parts.append(f"[影片說明]\n{description[:2000]}")

    ts_source: str | None = None
    whisper_seconds: int | None = None

    if transcript:
        parts.append(f"[字幕/逐字稿]\n{transcript}")
        ts_source = "transcript"

    # Gemini native video analysis
    if video_bytes:
        logger.info("Running Gemini video analysis for video_id=%s (%d bytes)", video_id, len(video_bytes))
        gemini_text = await ai_service.describe_video(video_bytes, mime_type)
        if gemini_text:
            parts.append(f"[影片視覺與音訊分析]\n{gemini_text}")

    # Whisper from extracted audio — only when no CC transcript
    if not transcript and audio_bytes and settings.groq_api_key:
        eff_duration = duration or 0
        if eff_duration > 0:
            daily_limit = await _get_whisper_daily_limit(db, user_id)
            today_used  = await _get_today_used_seconds(db, user_id)
            logger.info("Whisper quota: used=%s limit=%s duration=%s", today_used, daily_limit, eff_duration)
            if today_used + eff_duration <= daily_limit:
                whisper_text = await _whisper_from_audio_bytes(audio_bytes)
                if whisper_text:
                    parts.append(f"[音訊逐字稿]\n{whisper_text}")
                    whisper_seconds = eff_duration
                    ts_source = "whisper"

    if parts:
        return "\n\n".join(parts), whisper_seconds, duration, title, ts_source

    # Last-resort fallback: video download failed, no CC, try legacy Whisper download
    logger.info("No content via new pipeline for video_id=%s, trying legacy Whisper", video_id)
    if not settings.groq_api_key:
        return None, None, duration, title, None
    if duration is None:
        return None, None, None, title, None

    daily_limit = await _get_whisper_daily_limit(db, user_id)
    today_used  = await _get_today_used_seconds(db, user_id)
    if today_used + duration > daily_limit:
        logger.warning("Whisper daily quota exceeded for user_id=%s", user_id)
        return None, None, duration, title, None

    text = await _transcribe_with_whisper(url, cookies)
    if text is None:
        return None, None, duration, title, None

    fallback_parts: list[str] = []
    if description:
        fallback_parts.append(f"[影片說明]\n{description[:2000]}")
    fallback_parts.append(f"[音訊逐字稿]\n{text}")
    return "\n\n".join(fallback_parts), duration, duration, title, "whisper"
