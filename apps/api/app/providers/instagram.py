import re

from app.providers.base import ContentProvider, FetchInfo


def normalize_instagram_url(url: str) -> str:
    """Return canonical /p/ URL; pass non-Instagram URLs through unchanged."""
    match = re.search(r"instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]+)", url)
    if match:
        return f"https://www.instagram.com/p/{match.group(1)}/"
    return url


class InstagramProvider(ContentProvider):
    @classmethod
    def matches(cls, url: str) -> bool:
        return "instagram.com" in url

    async def fetch_info(
        self,
        url: str,
        content_id: str,
        content_md: str | None = None,
    ) -> FetchInfo:
        from app.services import apify_service

        result = await apify_service.fetch_instagram(url)

        # Thumbnail = first image (cover) cached to Storage
        thumbnail_url = None
        if result.thumbnail_url:
            thumb_bytes = await apify_service.download_bytes(result.thumbnail_url)
            if thumb_bytes:
                thumbnail_url = await self._cache_thumbnail(content_id, thumb_bytes)
        if not thumbnail_url:
            thumbnail_url = result.thumbnail_url

        caption = result.raw_data.get("caption") or result.raw_data.get("text") or ""
        first_line = caption.strip().splitlines()[0] if caption.strip() else ""
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
        import asyncio

        from app.services import ai_service, apify_service
        from app.services.apify_service import _extract_ig_media

        if stage_cb:
            stage_cb("fetching_content")

        caption = info.raw_data.get("caption") or info.raw_data.get("text") or ""
        image_urls, video_urls, _ = _extract_ig_media(info.raw_data)

        # Download all media in parallel (memory only, never stored to DB)
        image_results, video_results = await asyncio.gather(
            asyncio.gather(*[apify_service.download_bytes(u) for u in image_urls]),
            asyncio.gather(*[apify_service.download_bytes(u) for u in video_urls]),
        ) if image_urls or video_urls else ([], [])

        image_bytes_list = [b for b in image_results if b]
        video_bytes_list = [b for b in video_results if b]

        if stage_cb:
            stage_cb("understanding")

        return await ai_service.understand(video_bytes_list, image_bytes_list, description=caption)
