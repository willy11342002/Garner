from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CollectionItem(Base):
    __tablename__ = "collection_items"

    collection_id: Mapped[UUID] = mapped_column(
        ForeignKey("collections.id"), primary_key=True
    )
    content_id: Mapped[UUID] = mapped_column(
        ForeignKey("content_objects.id"), primary_key=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    collection: Mapped["Collection"] = relationship(back_populates="collection_items")
    content: Mapped["ContentObject"] = relationship(back_populates="collection_items")
