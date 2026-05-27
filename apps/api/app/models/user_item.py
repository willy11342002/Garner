import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, func
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
    last_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="user_items")
    content: Mapped["ContentObject"] = relationship(back_populates="user_items")
    fork_source: Mapped["UserItem | None"] = relationship(
        "UserItem", remote_side="UserItem.id", foreign_keys=[fork_from_item_id]
    )
    item_tags: Mapped[list["ItemTag"]] = relationship(back_populates="user_item")
