from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.collection import CollectionVisibility
from app.schemas.item import ItemRead


class CollectionCreate(BaseModel):
    title: str
    visibility: CollectionVisibility = CollectionVisibility.private
    slug: str


class CollectionRead(BaseModel):
    id: UUID
    title: str
    visibility: CollectionVisibility
    slug: str
    fork_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CollectionReadDetail(CollectionRead):
    items: list[ItemRead] = []


class CollectionUpdate(BaseModel):
    title: str | None = None
    visibility: CollectionVisibility | None = None


class CollectionShareItemRead(BaseModel):
    id: UUID
    url: str
    title: str | None
    summary: str | None
    thumbnail_url: str | None
    source_type: str | None

    model_config = {"from_attributes": True}


class CollectionShareRead(BaseModel):
    id: UUID
    title: str
    slug: str
    fork_count: int
    created_at: datetime
    author_username: str
    author_avatar_url: str | None
    items: list[CollectionShareItemRead]


class CollectionForkCreate(BaseModel):
    title: str | None = None
    content_ids: list[UUID] = []
    visibility: CollectionVisibility = CollectionVisibility.link


class PublicCollectionRead(BaseModel):
    id: UUID
    title: str
    slug: str
    fork_count: int
    created_at: datetime
    item_count: int
    author_username: str
    author_avatar_url: str | None
    source_tag_name: str | None
    cover_thumbnails: list[str | None]
