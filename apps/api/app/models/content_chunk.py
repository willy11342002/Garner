from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user_item import EMBEDDING_DIM


class ContentChunk(Base):
    __tablename__ = "content_chunks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)

    user_item: Mapped["UserItem"] = relationship(back_populates="chunks")
