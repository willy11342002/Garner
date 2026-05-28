from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import Date, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WhisperUsage(Base):
    __tablename__ = "whisper_usage"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    used_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
