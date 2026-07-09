from datetime import date, datetime, time
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Trip(Base):
    """AI 產出層（collection 型）：旅遊行程容器。

    與 Report（document 型）並列為產出層：
    - 不進知識語料（不寫 content_chunks），但有 embedding 供 search_trips chat tool 使用
    - 硬刪除（cascade 至 trip_items）
    - 可由 AI 或人編輯，永不自動回流成知識
    """

    __tablename__ = "trips"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # provenance：來源 user_item id 清單。不設 FK，因 user_items 走軟刪除。
    source_item_ids: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    last_edited_by: Mapped[str | None] = mapped_column(Text, nullable=True)  # "ai" | "user"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    invite_token: Mapped[UUID | None] = mapped_column(nullable=True, unique=True)
    invite_role: Mapped[str] = mapped_column(Text, nullable=False, default="viewer", server_default="viewer")
    # 語意搜尋用（search_trips chat tool）：title + summary + 卡片標題的 embedding，不進知識語料
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    items: Mapped[list["TripItem"]] = relationship(
        back_populates="trip", cascade="all, delete-orphan", lazy="selectin"
    )
    members: Mapped[list["TripMember"]] = relationship(
        back_populates="trip", cascade="all, delete-orphan", lazy="selectin"
    )


class TripItem(Base):
    """行程卡片。kind='event' 可上時間軸；kind='reference' 為參考資料，不上時間軸。"""

    __tablename__ = "trip_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    trip_id: Mapped[UUID] = mapped_column(
        ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 來源知識（可空：手動新增的「去程」「網卡」等無來源 item）。不設 FK，同 source_item_ids 理由。
    user_item_id: Mapped[UUID | None] = mapped_column(nullable=True)

    kind: Mapped[str] = mapped_column(Text, nullable=False, default="event", server_default="event")  # "event" | "reference"
    title: Mapped[str] = mapped_column(Text, nullable=False)
    emoji: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(Text, nullable=True)  # 景點|美食|交通|住宿|null
    booked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    ticket_url: Mapped[str | None] = mapped_column(Text, nullable=True)  # 票券／訂位連結

    # ── 排程 ──────────────────────────────────────────────────────────────────
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)   # 多日 span
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    order_index: Mapped[float] = mapped_column(Float, nullable=False, default=0, server_default="0")

    # ── 地標（預設繼承來源 item 的 content_location，可覆寫）────────────────
    place_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    geocoding_status: Mapped[str] = mapped_column(
        Text, nullable=False, default="done", server_default="done"
    )  # "pending" | "done" | "failed"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    trip: Mapped["Trip"] = relationship(back_populates="items")
    item_tags: Mapped[list["TripItemTag"]] = relationship(
        back_populates="trip_item", cascade="all, delete-orphan", lazy="selectin"
    )
    sources: Mapped[list["TripItemSource"]] = relationship(
        back_populates="trip_item", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_trip_items_trip_id_order", "trip_id", "order_index"),
    )


class TripItemSource(Base):
    """TripItem ↔ 知識（user_items）關聯：一張卡片可關聯多則知識（AI 依地點對應）。

    不對 user_item_id 設 FK，與 Trip.source_item_ids / TripItem.user_item_id 同理由：
    user_items 走軟刪除，硬 FK 會擋住刪除流程。
    """

    __tablename__ = "trip_item_sources"

    trip_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("trip_items.id", ondelete="CASCADE"), primary_key=True
    )
    user_item_id: Mapped[UUID] = mapped_column(primary_key=True)

    trip_item: Mapped["TripItem"] = relationship(back_populates="sources")


class TripTag(Base):
    """行程標籤詞彙（user 層級，跨行程可重用，與 tags 表完全獨立）。"""

    __tablename__ = "trip_tags"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    item_tags: Mapped[list["TripItemTag"]] = relationship(
        back_populates="trip_tag", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_trip_tags_user_name"),
    )


class TripItemTag(Base):
    """TripItem ↔ TripTag 多對多 join。"""

    __tablename__ = "trip_item_tags"

    trip_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("trip_items.id", ondelete="CASCADE"), primary_key=True
    )
    trip_tag_id: Mapped[UUID] = mapped_column(
        ForeignKey("trip_tags.id", ondelete="CASCADE"), primary_key=True
    )

    trip_item: Mapped["TripItem"] = relationship(back_populates="item_tags")
    trip_tag: Mapped["TripTag"] = relationship(back_populates="item_tags")


class TripMember(Base):
    """行程共用成員（非 owner）。role: 'editor' | 'viewer'"""

    __tablename__ = "trip_members"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    trip_id: Mapped[UUID] = mapped_column(
        ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True
    )
    member_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(Text, nullable=False, default="viewer", server_default="viewer")
    invited_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    trip: Mapped["Trip"] = relationship(back_populates="members")

    __table_args__ = (
        UniqueConstraint("trip_id", "member_user_id", name="uq_trip_members_trip_user"),
    )
