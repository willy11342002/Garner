from datetime import datetime
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


class PlaceReview(BaseModel):
    author: str | None = None
    author_photo: str | None = None
    rating: int | None = None
    text: str | None = None
    relative_time: str | None = None
    publish_time: str | None = None


class PlaceCacheRead(BaseModel):
    place_id: str
    name: str | None = None
    rating: float | None = None
    reviews: list[PlaceReview] | None = None
    photos: list[str] | None = None  # photo reference names
    address: str | None = None
    phone: str | None = None
    opening_hours: dict | None = None
    maps_url: str | None = None
    cached_at: datetime

    model_config = {"from_attributes": True}


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
