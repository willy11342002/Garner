from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ContentLocation(Base):
    __tablename__ = "content_locations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    content_id: Mapped[UUID] = mapped_column(
        ForeignKey("content_objects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)  # "metadata" | "ai"
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_content_locations_lat_lng", "lat", "lng"),
    )
