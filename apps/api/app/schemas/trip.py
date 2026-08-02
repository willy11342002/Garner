from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel


# ── Tag schemas ───────────────────────────────────────────────────────────────

class TripTagRead(BaseModel):
    id: UUID
    name: str
    color: str | None = None

    model_config = {"from_attributes": True}


class TripTagCreate(BaseModel):
    name: str
    color: str | None = None


class TripTagUpdate(BaseModel):
    name: str | None = None
    color: str | None = None


# ── Item schemas ──────────────────────────────────────────────────────────────

class TripItemTagRead(BaseModel):
    trip_tag_id: UUID
    name: str
    color: str | None = None

    model_config = {"from_attributes": True}


class TripSourceItem(BaseModel):
    """Provenance：trip 或 trip_item 關聯的知識（供前端顯示／點開）。"""
    id: UUID
    title: str | None = None
    thumbnail_url: str | None = None
    source_type: str | None = None

    model_config = {"from_attributes": True}


class TripItemRead(BaseModel):
    id: UUID
    trip_id: UUID
    user_item_id: UUID | None = None
    kind: str
    title: str
    emoji: str | None = None
    note: str | None = None
    category: str | None = None
    booked: bool
    ticket_url: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    order_index: float
    place_name: str | None = None
    lat: float | None = None
    lng: float | None = None
    geocoding_status: str
    tags: list[TripItemTagRead] = []
    sources: list[TripSourceItem] = []   # 關聯的知識（user_items），AI 依地點對應
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TripItemCreate(BaseModel):
    user_item_id: UUID | None = None   # 來源 item；null = 手動新增
    kind: str = "event"
    title: str
    emoji: str | None = None
    note: str | None = None
    category: str | None = None
    booked: bool = False
    ticket_url: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    order_index: float = 0
    place_name: str | None = None
    lat: float | None = None
    lng: float | None = None


class TripItemUpdate(BaseModel):
    kind: str | None = None
    title: str | None = None
    emoji: str | None = None
    note: str | None = None
    category: str | None = None
    booked: bool | None = None
    ticket_url: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    order_index: float | None = None
    place_name: str | None = None
    lat: float | None = None
    lng: float | None = None
    tag_ids: list[UUID] | None = None   # null = 不改；[] = 清空


class TripItemReorderEntry(BaseModel):
    id: UUID
    order_index: float


class TripItemReorderRequest(BaseModel):
    items: list[TripItemReorderEntry]


# ── Member schemas ────────────────────────────────────────────────────────────

class TripMemberRead(BaseModel):
    id: UUID
    member_user_id: UUID
    email: str
    display_name: str | None = None
    role: str  # "editor" | "viewer"
    created_at: datetime

    model_config = {"from_attributes": True}


class TripMemberCreate(BaseModel):
    email: str
    role: str = "viewer"


class TripMemberUpdate(BaseModel):
    role: str


class TripInviteLinkUpdate(BaseModel):
    role: str = "viewer"


# ── Trip schemas ──────────────────────────────────────────────────────────────

class TripRead(BaseModel):
    id: UUID
    title: str
    summary: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    last_edited_by: str | None = None
    sources: list[TripSourceItem] = []
    items: list[TripItemRead] = []
    my_role: str = "owner"              # "owner" | "editor" | "viewer"
    members: list[TripMemberRead] = []  # 非 owner 成員（owner only 可看 invite_token）
    invite_token: UUID | None = None    # 只有 owner 才填入
    invite_role: str = "viewer"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TripListItem(BaseModel):
    """列表用精簡版，不含 items。"""
    id: UUID
    title: str
    summary: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    source_count: int = 0
    item_count: int = 0
    member_count: int = 0
    my_role: str = "owner"              # "owner" | "editor" | "viewer"
    last_edited_by: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TripCreate(BaseModel):
    title: str
    summary: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class TripUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    start_date: date | None = None
    end_date: date | None = None


# AI 修改行程走 chat 的 SendMessageRequest（帶 scope），這裡不再有專屬 schema。
