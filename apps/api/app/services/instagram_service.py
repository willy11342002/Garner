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


# ── Public helpers ─────────────────────────────────────────────────────────────

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


# ── Internal helpers ───────────────────────────────────────────────────────────

async def _get_cookies_content(db: AsyncSession) -> str | None:
    from app.models.app_setting import AppSetting
    from sqlalchemy import select

    result = await db.execute(
        select(AppSetting.value).where(AppSetting.key == "instagram_cookies")
    )
    content = result.scalar_one_or_none()
    return content if content and content.strip() else None


def _fetch_post_instaloader(url: str, cookies_content: str | None) -> dict:
    """Fetch all media from any Instagram post using instaloader.

    Returns a dict with:
      image_urls      — CDN URLs for all image slides
      video_urls      — CDN URLs for all video slides
      video_durations — duration in seconds per video (same order as video_urls)
      description     — post caption
      thumbnail_bytes — cover image bytes (first frame of video or first image)
      uploader        — owner username

    Works for GraphImage, GraphVideo, and GraphSidecar (mixed carousel).
    Returns {} on any error so the caller can handle gracefully.
    """
    import http.cookiejar
    import urllib.request as _req

    import instaloader

    shortcode = extract_shortcode(url)
    if not shortcode:
        return {}

    tmpdir = tempfile.mkdtemp()
    try:
        L = instaloader.Instaloader(quiet=True, download_pictures=False, download_videos=False)

        # Load cookies so Instagram doesn't serve a login wall
        if cookies_content:
            cookies_path = os.path.join(tmpdir, "cookies.txt")
            with open(cookies_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(cookies_content.replace("\r\n", "\n").replace("\r", "\n"))
            cj = http.cookiejar.MozillaCookieJar(cookies_path)
            cj.load(ignore_discard=True, ignore_expires=True)
            for cookie in cj:
                L.context._session.cookies.set(
                    cookie.name, cookie.value, domain=cookie.domain, path=cookie.path
                )

        post = instaloader.Post.from_shortcode(L.context, shortcode)

        image_urls:      list[str] = []
        video_urls:      list[str] = []
        video_durations: list[int] = []

        if post.typename == "GraphSidecar":
            for node in post.get_sidecar_nodes():
                if node.is_video:
                    video_urls.append(node.video_url)
                    video_durations.append(int(node.video_duration or 0))
                else:
                    image_urls.append(node.display_url)
        elif post.is_video:
            video_urls.append(post.video_url)
            video_durations.append(int(post.video_duration or 0))
        else:
            image_urls.append(post.url)

        logger.info(
            "instaloader: shortcode=%s images=%d videos=%d",
            shortcode, len(image_urls), len(video_urls),
        )

        # Download thumbnail / cover bytes
        thumbnail_bytes: bytes | None = None
        try:
            thumb_url = post.url  # cover image for videos, first image for carousels
            req = _req.Request(thumb_url, headers={"User-Agent": "Mozilla/5.0"})
            with _req.urlopen(req, timeout=10) as resp:
                thumbnail_bytes = resp.read()
        except Exception:
            logger.warning("instaloader: thumbnail download failed", exc_info=True)

        return {
            "description":     post.caption or "",
            "thumbnail_bytes": thumbnail_bytes,
            "uploader":        post.owner_username,
            "image_urls":      image_urls,
            "video_urls":      video_urls,
            "video_durations": video_durations,
        }
    except Exception:
        logger.exception("instaloader failed for url=%s", url)
        return {}
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


async def _fetch_image_bytes(image_urls: list[str]) -> list[bytes]:
    """Fetch image bytes directly from CDN URLs (max 10)."""
    import urllib.request

    images: list[bytes] = []
    for img_url in image_urls[:10]:
        try:
            req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                images.append(resp.read())
        except Exception:
            logger.warning("Failed to fetch image url=%s", img_url, exc_info=True)
    logger.info("IG fetched %d/%d image(s)", len(images), len(image_urls))
    return images


async def _transcribe_with_whisper(video_url: str) -> tuple[str | None, int | None]:
    """Download audio from a CDN video URL and transcribe with Groq Whisper.

    Accepts a direct CDN URL (from instaloader), not an Instagram post URL.
    Returns (transcript_text, duration_sec).
    """
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
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            return info.get("duration") if info else None

    try:
        duration = await asyncio.to_thread(_download)
        audio_path = audio_base + ".mp3"
        if not os.path.exists(audio_path):
            logger.warning("Audio file not found after download for url=%s", video_url)
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
        logger.exception("Whisper transcription failed for url=%s", video_url)
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


# ── Main entry point ───────────────────────────────────────────────────────────

async def fetch_content(
    db: AsyncSession,
    user_id: UUID,
    url: str,
    stage_cb=None,
) -> tuple[str | None, int | None, int | None, str | None, bytes | None]:
    """Fetch Instagram content via instaloader.

    Runs both pipelines concurrently when applicable:
      • Image pipeline — _fetch_image_bytes → vision AI (Claude)
      • Video pipeline — yt-dlp audio extract → Groq Whisper

    Returns (raw_content, whisper_seconds_used, total_duration_sec, title, thumbnail_bytes).
    title is always None so process_item generates it from the summary via LLM.
    raw_content combines [Caption], [Images], and [Audio] sections.
    """
    if stage_cb:
        stage_cb("fetching_info")

    cookies = await _get_cookies_content(db)
    data = await asyncio.to_thread(_fetch_post_instaloader, url, cookies)

    if not data:
        return None, None, None, None, None

    description:     str        = data.get("description") or ""
    thumbnail_bytes: bytes|None = data.get("thumbnail_bytes")
    image_urls:      list[str]  = data.get("image_urls") or []
    video_urls:      list[str]  = data.get("video_urls") or []
    video_durations: list[int]  = data.get("video_durations") or []

    logger.info(
        "IG post: images=%d videos=%d description_len=%s",
        len(image_urls), len(video_urls), len(description),
    )

    if stage_cb:
        stage_cb("fetching_content")

    parts: list[str] = []
    if description.strip():
        parts.append(f"[Caption]\n{description.strip()}")

    # ── Image pipeline ─────────────────────────────────────────────────────────
    if image_urls:
        from app.services import ai_service
        images = await _fetch_image_bytes(image_urls)
        if not thumbnail_bytes and images:
            thumbnail_bytes = images[0]
        if images:
            image_text = await ai_service.describe_images(images)
            if image_text:
                parts.append(f"[Images]\n{image_text}")

    # ── Video pipeline ─────────────────────────────────────────────────────────
    whisper_seconds_total = 0
    total_video_duration  = sum(video_durations) or None

    if video_urls:
        daily_limit = await _get_whisper_daily_limit(db, user_id)
        today_used  = await _get_today_used_seconds(db, user_id)
        logger.info("Whisper quota: used=%s limit=%s", today_used, daily_limit)

        for video_url, duration in zip(video_urls, video_durations):
            if today_used + duration > daily_limit:
                logger.warning("Whisper daily quota exceeded for user_id=%s, skipping remaining videos", user_id)
                break
            transcript, actual_dur = await _transcribe_with_whisper(video_url)
            if transcript:
                parts.append(f"[Audio]\n{transcript}")
                used = actual_dur or duration
                today_used            += used
                whisper_seconds_total += used

    raw_content = "\n\n".join(parts) if parts else None
    whisper_seconds = whisper_seconds_total or None
    return raw_content, whisper_seconds, total_video_duration, None, thumbnail_bytes
