import re

from app.providers.base import ContentProvider, FetchInfo


def normalize_youtube_url(url: str) -> str:
    """Return canonical watch?v= URL; pass non-YouTube URLs through unchanged."""
    match = re.search(r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})", url)
    if match:
        return f"https://www.youtube.com/watch?v={match.group(1)}"
    return url


class YouTubeProvider(ContentProvider):
    @classmethod
    def matches(cls, url: str) -> bool:
        return "youtube.com" in url or "youtu.be" in url

    async def fetch_info(
        self,
        url: str,
        content_id: str,
        content_md: str | None = None,
    ) -> FetchInfo:
        from app.services import apify_service

        result = await apify_service.fetch_youtube(url)

        thumbnail_url = None
        if result.thumbnail_url:
            thumb_bytes = await apify_service.download_bytes(result.thumbnail_url)
            if thumb_bytes:
                thumbnail_url = await self._cache_thumbnail(content_id, thumb_bytes)
        if not thumbnail_url:
            thumbnail_url = result.thumbnail_url

        return FetchInfo(
            raw_data=result.raw_data,
            title=result.title,
            duration_sec=result.duration_sec,
            thumbnail_url=thumbnail_url,
        )

    async def fetch_content(
        self,
        url: str,
        info: FetchInfo,
        stage_cb=None,
    ) -> str | None:
        from app.services import ai_service, apify_service

        if stage_cb:
            stage_cb("fetching_content")

        title = info.title or info.raw_data.get("title")
        description = info.raw_data.get("description") or info.raw_data.get("text") or ""

        # Download video to memory (not stored to DB)
        video_bytes: bytes | None = None
        mime_type = "video/mp4"
        video_url = info.raw_data.get("videoUrl") or info.raw_data.get("streamUrl")
        if video_url:
            video_bytes = await apify_service.download_bytes(video_url)

        if stage_cb:
            stage_cb("understanding")

        return await ai_service.understand(video_bytes, mime_type=mime_type, title=title, description=description)
