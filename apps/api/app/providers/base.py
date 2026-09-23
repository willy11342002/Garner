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
    # True when thumbnail_url points at our own Storage cache (permanent);
    # False means it is the platform's own URL, which is usually a signed URL
    # that expires within days — callers must not persist it over a cached one.
    thumbnail_cached: bool = False
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

    async def _resolve_thumbnail(
        self, content_id: str, source_url: str | None
    ) -> tuple[str | None, bool]:
        """Download the platform's thumbnail and cache it to Storage.

        Returns (url, cached). The platform URL is only a fallback for when
        caching fails — those are short-lived signed URLs, so `cached` tells
        the caller whether the URL is safe to keep."""
        if not source_url:
            return None, False

        from app.services import apify_service, thumbnail_service

        image_bytes = await apify_service.download_bytes(source_url)
        if image_bytes:
            try:
                return await thumbnail_service.cache(content_id, image_bytes), True
            except Exception:
                logger.warning(
                    "Thumbnail upload failed for content_id=%s", content_id, exc_info=True
                )
        return source_url, False

    async def _download_bytes(self, url: str) -> bytes | None:
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.content
        except Exception:
            return None
