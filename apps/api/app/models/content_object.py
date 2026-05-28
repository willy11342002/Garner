import enum
from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

EMBEDDING_DIM = 1536


class SourceType(str, enum.Enum):
    youtube = "youtube"
    article = "article"
    ig = "ig"


def detect_source_type(url: str) -> "SourceType":
    if "youtube.com" in url or "youtu.be" in url:
        return SourceType.youtube
    if "instagram.com" in url:
        return SourceType.ig
    return SourceType.article


class ContentObject(Base):
    __tablename__ = "content_objects"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type_enum"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user_items: Mapped[list["UserItem"]] = relationship(back_populates="content")
    collection_items: Mapped[list["CollectionItem"]] = relationship(back_populates="content")
