import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CollectionVisibility(str, enum.Enum):
    private = "private"
    link = "link"
    public = "public"


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    source_tag_id: Mapped[UUID | None] = mapped_column(ForeignKey("tags.id"), nullable=True)
    fork_from_collection_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("collections.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[CollectionVisibility] = mapped_column(
        Enum(CollectionVisibility, name="collection_visibility_enum"),
        nullable=False,
        default=CollectionVisibility.private,
    )
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    fork_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="collections")
    source_tag: Mapped["Tag | None"] = relationship(back_populates="collections")
    fork_source: Mapped["Collection | None"] = relationship(
        "Collection", remote_side="Collection.id", foreign_keys=[fork_from_collection_id]
    )
    collection_items: Mapped[list["CollectionItem"]] = relationship(back_populates="collection")
