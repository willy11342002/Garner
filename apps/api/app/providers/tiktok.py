import re

from app.providers.base import ContentProvider, FetchInfo


def normalize_tiktok_url(url: str) -> str:
    """Return canonical TikTok video URL; pass non-TikTok URLs through unchanged."""
    match = re.search(r"tiktok\.com/@[\w.-]+/video/(\d+)", url)
    if match:
        return f"https://www.tiktok.com/@user/video/{match.group(1)}"
    return url


class TikTokProvider(ContentProvider):
    @classmethod
    def matches(cls, url: str) -> bool:
        return "tiktok.com" in url or "vt.tiktok.com" in url

    async def fetch_info(
        self,
        url: str,
        content_id: str,
        content_md: str | None = None,
    ) -> FetchInfo:
        from app.services import apify_service

        result = await apify_service.fetch_tiktok(url)

        thumbnail_url = None
        if result.thumbnail_url:
            thumb_bytes = await apify_service.download_bytes(result.thumbnail_url)
            if thumb_bytes:
                thumbnail_url = await self._cache_thumbnail(content_id, thumb_bytes)
        if not thumbnail_url:
            thumbnail_url = result.thumbnail_url

        description = result.raw_data.get("text") or ""
        first_line = description.strip().splitlines()[0] if description.strip() else ""
        title = first_line[:20] or None

        return FetchInfo(
            raw_data=result.raw_data,
            title=title,
            duration_sec=result.duration_sec,
            thumbnail_url=thumbnail_url,
        )

    async def fetch_content(
        self,
        url: str,
        info: FetchInfo,
        stage_cb=None,
    ) -> str | None:
        import logging
        from pathlib import Path
        from app.services import ai_service, apify_service

        logger = logging.getLogger(__name__)

        if stage_cb:
            stage_cb("fetching_content")

        description = info.raw_data.get("text") or ""

        # Download all videos to memory (not stored to DB)
        video_bytes_list: list[bytes] = []
        mime_type = "video/mp4"
        media_urls = info.raw_data.get("mediaUrls") or []

        for idx, video_url in enumerate(media_urls):
            if not video_url:
                continue
            video_bytes = await apify_service.download_bytes(video_url)
            if video_bytes:
                video_bytes_list.append(video_bytes)

        if stage_cb:
            stage_cb("understanding")

        # Pass all videos for LLM analysis
        return await ai_service.understand(video_bytes_list if video_bytes_list else None, mime_type=mime_type, description=description)
