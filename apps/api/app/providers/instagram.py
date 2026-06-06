from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_object import ContentObject, TranscriptionSource
from app.providers.base import ContentProvider, FetchResult


class InstagramProvider(ContentProvider):
    @classmethod
    def matches(cls, url: str) -> bool:
        return "instagram.com" in url

    async def fetch(
        self,
        db: AsyncSession,
        user_id: UUID,
        url: str,
        content: ContentObject,
        stage_cb=None,
        max_duration_sec: int = 1200,
    ) -> FetchResult:
        from app.services import instagram_service

        raw, whisper_sec, duration, title, thumbnail_bytes = await instagram_service.fetch_content(
            db, user_id, url, stage_cb=stage_cb
        )

        thumbnail_url = None
        if thumbnail_bytes:
            thumbnail_url = await self._cache_thumbnail(str(content.id), thumbnail_bytes)

        return FetchResult(
            raw_content=raw,
            title=title,
            duration_sec=duration,
            transcription_source=TranscriptionSource.whisper if whisper_sec else None,
            whisper_seconds=whisper_sec,
            thumbnail_url=thumbnail_url,
        )
