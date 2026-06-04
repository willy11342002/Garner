from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_object import ContentObject, TranscriptionSource


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
    ) -> FetchResult: ...
