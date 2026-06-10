from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, HttpUrl, model_validator

T = TypeVar("T")

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
                raise HTTPException(status_code=422, detail="invalid_url")
        return self


class ItemRead(BaseModel):
    id: UUID
    content_id: UUID | None = None
    url: str
    title: str | None
    notes_md: str | None = None
    thumbnail_url: str | None
    saved_at: datetime
    deleted_at: datetime | None = None
    parsed_at: datetime | None = None
    status: str | None = None
    source_type: str | None = None
    tags: list[TagRead] = []

    model_config = {"from_attributes": True}


class ItemUpdate(BaseModel):
    title: str | None = None
    status: UserItemStatus | None = None


class ArticleUpdate(BaseModel):
    title: str | None = None
    notes_md: str | None = None


class PaginatedResult(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    has_next: bool


class ItemPage(BaseModel):
    items: list[ItemRead]
    total: int
    page: int
    page_size: int


class ItemPendingReviewRead(BaseModel):
    id: UUID
    url: str
    title: str | None
    thumbnail_url: str | None
    saved_at: datetime
    pending_tags: list[TagRead]
