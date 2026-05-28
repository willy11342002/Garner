import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TagSource(str, enum.Enum):
    ai = "ai"
    user = "user"


class ItemTag(Base):
    __tablename__ = "item_tags"

    user_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_items.id"), primary_key=True
    )
    tag_id: Mapped[UUID] = mapped_column(ForeignKey("tags.id"), primary_key=True)
    source: Mapped[TagSource] = mapped_column(
        Enum(TagSource, name="tag_source_enum"), nullable=False
    )
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user_item: Mapped["UserItem"] = relationship(back_populates="item_tags")
    tag: Mapped["Tag"] = relationship(back_populates="item_tags")
