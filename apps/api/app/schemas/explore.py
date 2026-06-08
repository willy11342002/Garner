import enum
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


# Focus (AI synthesis search)

class FocusQuery(BaseModel):
    query: str


class FocusSource(BaseModel):
    id: UUID
    url: str
    title: str | None
    thumbnail_url: str | None
    source_type: str | None
    saved_at: datetime


class FocusResult(BaseModel):
    synthesis: str
    sources: list[FocusSource]


# Surprise (AI insights)

class InsightType(str, enum.Enum):
    connection = "connection"
    forgotten = "forgotten"
    trend = "trend"


class InsightItem(BaseModel):
    id: UUID
    url: str
    title: str | None
    thumbnail_url: str | None
    source_type: str | None


class TrendBar(BaseModel):
    label: str
    pct: int


class Insight(BaseModel):
    type: InsightType
    badge: str
    title: str
    body: str
    when: str
    items: list[InsightItem] = []
    trend_bars: list[TrendBar] = []


class SurpriseResult(BaseModel):
    insights: list[Insight]


# Chain exploration

class ChainItem(BaseModel):
    id: UUID
    url: str
    title: str | None
    thumbnail_url: str | None
    source_type: str | None
    saved_at: datetime
    is_public: bool = False


class ChainHopAnalysis(BaseModel):
    connection: str
    ideation: str
    question: str


class ChainHopRequest(BaseModel):
    from_item_id: UUID
    to_item_id: UUID


class ChainFullRequest(BaseModel):
    item_ids: list[UUID]


class ChainFullAnalysis(BaseModel):
    analysis: str


# Custom synthesis

class SynthesizeRequest(BaseModel):
    item_ids: list[UUID]
    prompt: str


class SynthesizeResult(BaseModel):
    content: str          # Markdown
    sources: list[FocusSource]
