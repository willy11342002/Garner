import re

import httpx
from supabase import AsyncClient, acreate_client

from app.core.config import settings

_supabase: AsyncClient | None = None


async def _get_supabase() -> AsyncClient:
    global _supabase
    if _supabase is None:
        _supabase = await acreate_client(settings.supabase_url, settings.supabase_service_key)
    return _supabase


def _extract_youtube_id(url: str) -> str | None:
    match = re.search(r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})", url)
    return match.group(1) if match else None


async def _fetch_og_image(url: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            match = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', resp.text)
            return match.group(1) if match else None
    except Exception:
        return None


async def _download_bytes(url: str) -> bytes | None:
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content
    except Exception:
        return None


async def cache_thumbnail_bytes(content_id: str, image_bytes: bytes) -> str | None:
    """Upload pre-fetched image bytes to Supabase Storage and return the public URL."""
    import logging
    logger = logging.getLogger(__name__)
    try:
        supabase = await _get_supabase()
        path = f"thumbnails/{content_id}.jpg"
        await supabase.storage.from_(settings.storage_bucket).upload(
            path,
            image_bytes,
            {"content-type": "image/jpeg", "upsert": "true"},
        )
        url = await supabase.storage.from_(settings.storage_bucket).get_public_url(path)
        logger.info("Thumbnail cached: %s", url)
        return url
    except Exception:
        logger.warning("Thumbnail upload failed for content_id=%s", content_id, exc_info=True)
        return None


async def fetch_and_cache_thumbnail(
    content_id: str, source_url: str, fallback_url: str | None = None
) -> str | None:
    """
    Downloads thumbnail and caches to Supabase Storage. Falls back to origin URL on failure.
    Pass fallback_url to skip URL discovery (e.g. when the caller already has the thumbnail URL).
    """
    youtube_id = _extract_youtube_id(source_url)
    if fallback_url:
        origin_url = fallback_url
    elif youtube_id:
        origin_url = f"https://img.youtube.com/vi/{youtube_id}/maxresdefault.jpg"
    else:
        origin_url = await _fetch_og_image(source_url)

    if not origin_url:
        return None

    image_bytes = await _download_bytes(origin_url)
    if not image_bytes:
        return origin_url

    cached = await cache_thumbnail_bytes(content_id, image_bytes)
    return cached or origin_url
