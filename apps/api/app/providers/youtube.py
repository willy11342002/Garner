import re
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_object import ContentObject, TranscriptionSource
from app.providers.base import ContentProvider, FetchResult


class YouTubeProvider(ContentProvider):
    @classmethod
    def matches(cls, url: str) -> bool:
        return "youtube.com" in url or "youtu.be" in url

    async def fetch(
        self,
        db: AsyncSession,
        user_id: UUID,
        url: str,
        content: ContentObject,
        stage_cb=None,
        max_duration_sec: int = 1200,
    ) -> FetchResult:
        from app.services import youtube_service

        raw, whisper_sec, duration, title, ts_str = await youtube_service.fetch_content(
            db, user_id, url, stage_cb=stage_cb, max_duration_sec=max_duration_sec
        )
        thumbnail_url = await self.fetch_thumbnail(str(content.id), url)
        ts = TranscriptionSource(ts_str) if ts_str else None
        return FetchResult(
            raw_content=raw,
            title=title,
            duration_sec=duration,
            transcription_source=ts,
            whisper_seconds=whisper_sec,
            thumbnail_url=thumbnail_url,
        )

    async def fetch_thumbnail(self, content_id: str, url: str) -> str | None:
        match = re.search(r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})", url)
        if not match:
            return await super().fetch_thumbnail(content_id, url)
        yt_url = f"https://img.youtube.com/vi/{match.group(1)}/maxresdefault.jpg"
        image_bytes = await self._download_bytes(yt_url)
        if not image_bytes:
            return yt_url
        return await self._cache_thumbnail(content_id, image_bytes) or yt_url
