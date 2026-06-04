from uuid import UUID

from pydantic import BaseModel


class TagCreate(BaseModel):
    name: str


class TagRead(BaseModel):
    id: UUID
    name: str
    name_i18n: dict[str, str] | None = None
    item_count: int = 0

    model_config = {"from_attributes": True}


class TagUpdate(BaseModel):
    name: str


class TagSingleConfirm(BaseModel):
    tag_id: UUID


class TagBulkConfirm(BaseModel):
    tag_ids: list[UUID]
