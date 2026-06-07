import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)


@dataclass
class FetchInfo:
    """Result of fetching_info stage — saved to DB immediately after Apify returns."""
    raw_data: dict = field(default_factory=dict)
    title: str | None = None
    duration_sec: int | None = None
    thumbnail_url: str | None = None
    # Set by ArticleProvider only; when present, skips fetch_content()
    raw_content: str | None = None


class ContentProvider(ABC):
    @classmethod
    @abstractmethod
    def matches(cls, url: str) -> bool: ...

    @abstractmethod
    async def fetch_info(
        self,
        url: str,
        content_id: str,
        content_md: str | None = None,
    ) -> FetchInfo:
        """Stage: fetching_info — call Apify, cache thumbnail, return metadata."""
        ...

    @abstractmethod
    async def fetch_content(
        self,
        url: str,
        info: FetchInfo,
        stage_cb: Callable[[str], None] | None = None,
    ) -> str | None:
        """Stages: fetching_content → understanding — download media, call LLM.
        Returns raw_content text, or None on failure."""
        ...

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

    async def _download_bytes(self, url: str) -> bytes | None:
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.content
        except Exception:
            return None
