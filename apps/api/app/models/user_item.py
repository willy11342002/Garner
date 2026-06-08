import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserItemStatus(str, enum.Enum):
    active = "active"
    archived = "archived"
    deleted = "deleted"


class UserItem(Base):
    __tablename__ = "user_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    content_id: Mapped[UUID] = mapped_column(
        ForeignKey("content_objects.id"), nullable=False, index=True
    )
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
    is_draft: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")
    is_public: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")
    last_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Snapshot 欄位（從 ContentObject 複製，讀取不需 JOIN）─────────────────
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_i18n: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str | None] = mapped_column(
        Enum("youtube", "article", "ig", "note", name="source_type_enum", create_constraint=False),
        nullable=True,
    )
    content_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    transcription_source: Mapped[str | None] = mapped_column(
        Enum("transcript", "whisper", "none", name="transcription_source_enum", create_constraint=False),
        nullable=True,
    )

    user: Mapped["User"] = relationship(back_populates="user_items")
    content: Mapped["ContentObject"] = relationship(back_populates="user_items")
    fork_source: Mapped["UserItem | None"] = relationship(
        "UserItem", remote_side="UserItem.id", foreign_keys=[fork_from_item_id]
    )
    item_tags: Mapped[list["ItemTag"]] = relationship(back_populates="user_item")
