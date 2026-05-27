from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, HttpUrl


class ItemCreate(BaseModel):
    url: HttpUrl
    title: str | None = None


class ItemRead(BaseModel):
    id: UUID
    url: str
    title: str | None
    summary: str | None
    created_at: datetime
    deleted_at: datetime | None = None

    model_config = {"from_attributes": True}


class ItemUpdate(BaseModel):
    title: str | None = None
