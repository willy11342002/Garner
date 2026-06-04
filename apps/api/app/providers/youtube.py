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
    ) -> FetchResult:
        from app.services import thumbnail_service, youtube_service

        raw, whisper_sec, duration, title, ts_str = await youtube_service.fetch_content(
            db, user_id, url, stage_cb=stage_cb
        )
        thumbnail_url = await thumbnail_service.fetch_and_cache_thumbnail(str(content.id), url)
        ts = TranscriptionSource(ts_str) if ts_str else None
        return FetchResult(
            raw_content=raw,
            title=title,
            duration_sec=duration,
            transcription_source=ts,
            whisper_seconds=whisper_sec,
            thumbnail_url=thumbnail_url,
        )
