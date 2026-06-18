import enum
from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

EMBEDDING_DIM = 1536


class UserItemStatus(str, enum.Enum):
    active = "active"
    archived = "archived"
    deleted = "deleted"


class UserItem(Base):
    __tablename__ = "user_items"
    __table_args__ = (
        UniqueConstraint("user_id", "url", name="uq_user_items_user_id_url"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    fork_from_item_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_items.id"), nullable=True
    )
    status: Mapped[UserItemStatus] = mapped_column(
        Enum(UserItemStatus, name="user_item_status_enum"),
        nullable=False,
        default=UserItemStatus.active,
    )
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_public: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")
    last_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Snapshot / content fields ────────────────────────────────────────────
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str | None] = mapped_column(
        Enum("youtube", "article", "ig", "tiktok", "note", "facebook_reel", "facebook_post", name="source_type_enum", create_constraint=False),
        nullable=True,
    )
    notes_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── AI fields ────────────────────────────────────────────────────────────
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extract: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Pipeline stage tracking ──────────────────────────────────────────────
    fetch_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetch_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fetch_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    assets_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    assets_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assets_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    note_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    note_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    landmarks_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    landmarks_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    landmarks_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    embedding_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="user_items")
    fork_source: Mapped["UserItem | None"] = relationship(
        "UserItem", remote_side="UserItem.id", foreign_keys=[fork_from_item_id]
    )
    item_tags: Mapped[list["ItemTag"]] = relationship(back_populates="user_item")
    chunks: Mapped[list["ContentChunk"]] = relationship(
        back_populates="user_item", cascade="all, delete-orphan"
    )
    locations: Mapped[list["ContentLocation"]] = relationship(
        back_populates="user_item", cascade="all, delete-orphan"
    )
