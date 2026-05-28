from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, HttpUrl

from app.models.user_item import UserItemStatus
from app.schemas.tag import TagRead


class ItemCreate(BaseModel):
    url: HttpUrl
    title: str | None = None
    raw_content: str | None = None


class ItemRead(BaseModel):
    id: UUID
    url: str
    title: str | None
    summary: str | None
    summary_i18n: dict[str, str] | None = None
    thumbnail_url: str | None
    saved_at: datetime
    deleted_at: datetime | None = None
    parsed_at: datetime | None = None

    model_config = {"from_attributes": True}


class ItemUpdate(BaseModel):
    title: str | None = None
    status: UserItemStatus | None = None


class ItemPendingReviewRead(BaseModel):
    id: UUID
    url: str
    title: str | None
    thumbnail_url: str | None
    saved_at: datetime
    pending_tags: list[TagRead]
