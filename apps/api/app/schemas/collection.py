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
