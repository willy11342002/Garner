import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_object import ContentObject, TranscriptionSource

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    raw_content: str | None
    title: str | None = None
    duration_sec: int | None = None
    transcription_source: TranscriptionSource | None = None
    whisper_seconds: int | None = None
    thumbnail_url: str | None = None


class ContentProvider(ABC):
    @classmethod
    @abstractmethod
    def matches(cls, url: str) -> bool: ...

    @abstractmethod
    async def fetch(
        self,
        db: AsyncSession,
        user_id: UUID,
        url: str,
        content: ContentObject,
        stage_cb: Callable[[str], None] | None = None,
        max_duration_sec: int = 1200,
    ) -> FetchResult: ...

    async def fetch_thumbnail(self, content_id: str, url: str) -> str | None:
        """Default: extract og:image from the page, download, and cache to Supabase."""
        og_url = await self._fetch_og_image(url)
        if not og_url:
            return None
        image_bytes = await self._download_bytes(og_url)
        if not image_bytes:
            return og_url
        return await self._cache_thumbnail(content_id, image_bytes) or og_url

    async def _cache_thumbnail(self, content_id: str, image_bytes: bytes) -> str | None:
        from app.core.config import settings
        from app.core.supabase import get_supabase

        try:
            supabase = await get_supabase()
            path = f"thumbnails/{content_id}.jpg"
            await supabase.storage.from_(settings.storage_bucket).upload(
                path, image_bytes, {"content-type": "image/jpeg", "upsert": "true"}
            )
            url = await supabase.storage.from_(settings.storage_bucket).get_public_url(path)
            logger.info("Thumbnail cached: %s", url)
            return url
        except Exception:
            logger.warning("Thumbnail upload failed for content_id=%s", content_id, exc_info=True)
            return None

    async def _fetch_og_image(self, url: str) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                match = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', resp.text)
                return match.group(1) if match else None
        except Exception:
            return None

    async def _download_bytes(self, url: str) -> bytes | None:
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.content
        except Exception:
            return None
