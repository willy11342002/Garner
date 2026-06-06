import asyncio
import logging
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_object import ContentObject
from app.providers.base import ContentProvider, FetchResult

logger = logging.getLogger(__name__)

_FETCH_TIMEOUT = 20
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class DefaultProvider(ContentProvider):
    """Fallback provider for any http(s) URL not matched by a specific provider."""

    @classmethod
    def matches(cls, url: str) -> bool:
        return True

    async def fetch(
        self,
        db: AsyncSession,
        user_id: UUID,
        url: str,
        content: ContentObject,
        stage_cb=None,
        max_duration_sec: int = 1200,
    ) -> FetchResult:
        if stage_cb:
            stage_cb("fetching_content")
        raw, title = await _fetch_and_extract(url)
        thumbnail_url = await self.fetch_thumbnail(str(content.id), url)
        return FetchResult(raw_content=raw, title=title, thumbnail_url=thumbnail_url)


async def _fetch_and_extract(url: str) -> tuple[str | None, str | None]:
    """Fetch URL and extract main text + title via trafilatura."""
    import trafilatura

    try:
        async with httpx.AsyncClient(
            timeout=_FETCH_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text
    except Exception as exc:
        logger.warning("DefaultProvider: fetch failed for %s: %s", url, exc)
        return None, None

    try:
        text = await asyncio.to_thread(
            trafilatura.extract,
            html,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            favor_recall=True,
        )
        meta = await asyncio.to_thread(trafilatura.extract_metadata, html)
        title = meta.title if meta else None
        return text or None, title or None
    except Exception as exc:
        logger.warning("DefaultProvider: trafilatura extraction failed for %s: %s", url, exc)
        return None, None
