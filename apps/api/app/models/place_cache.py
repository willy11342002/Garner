from datetime import datetime

from sqlalchemy import DateTime, Float, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PlaceCache(Base):
    __tablename__ = "place_cache"

    place_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    reviews: Mapped[list | None] = mapped_column(JSON, nullable=True)
    photos: Mapped[list | None] = mapped_column(JSON, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    opening_hours: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    maps_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    cached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
