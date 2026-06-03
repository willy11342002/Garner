from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, HttpUrl, model_validator

from app.models.user_item import UserItemStatus
from app.schemas.tag import TagRead


class ItemCreate(BaseModel):
    url: str | None = None          # None → create an in-app note
    title: str | None = None
    raw_content: str | None = None

    @model_validator(mode="after")
    def validate_url(self) -> "ItemCreate":
        if self.url is not None:
            # external URLs must be http(s)
            if not self.url.startswith("http://") and not self.url.startswith("https://"):
                raise ValueError("url must start with http:// or https://")
        return self


class ItemRead(BaseModel):
    id: UUID
    content_id: UUID | None = None
    url: str
    title: str | None
    summary: str | None
    summary_i18n: dict[str, Any] | None = None
    thumbnail_url: str | None
    saved_at: datetime
    deleted_at: datetime | None = None
    parsed_at: datetime | None = None
    status: str | None = None
    source_type: str | None = None
    transcription_source: str | None = None
    is_owner: bool = False
    content_md: str | None = None
    is_draft: bool = True
    is_public: bool = False

    model_config = {"from_attributes": True}


class ItemUpdate(BaseModel):
    title: str | None = None
    status: UserItemStatus | None = None


class ArticleUpdate(BaseModel):
    title: str | None = None
    content_md: str | None = None
    is_draft: bool | None = None
    is_public: bool | None = None


class ItemSummaryUpdate(BaseModel):
    summary_i18n: dict[str, Any]   # full Tiptap JSON doc per locale, e.g. {"zh-TW": {...}}


class ItemPendingReviewRead(BaseModel):
    id: UUID
    url: str
    title: str | None
    thumbnail_url: str | None
    saved_at: datetime
    pending_tags: list[TagRead]
