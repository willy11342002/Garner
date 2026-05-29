from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ExploreStats(BaseModel):
    total_items: int
    public_collections: int
    weekly_new: int


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
