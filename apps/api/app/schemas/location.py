from uuid import UUID

from pydantic import BaseModel


class ContentLocationRead(BaseModel):
    id: UUID
    name: str
    lat: float | None
    lng: float | None
    source: str
    confirmed: bool
    order_index: int

    model_config = {"from_attributes": True}


class ContentLocationUpdate(BaseModel):
    name: str | None = None
    confirmed: bool | None = None


class LocationMapPoint(BaseModel):
    """Used in bounding box map queries."""
    id: UUID
    name: str
    lat: float
    lng: float
    source: str
    confirmed: bool
    content_id: UUID
    item_id: UUID
    item_title: str | None = None
    item_thumbnail: str | None = None
    item_source_type: str | None = None
