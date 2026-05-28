import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SSOProvider(str, enum.Enum):
    google = "google"
    github = "github"
    apple = "apple"


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    monthly_saves: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sso_provider: Mapped[SSOProvider | None] = mapped_column(
        Enum(SSOProvider, name="sso_provider_enum"), nullable=True
    )
    sso_subject: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="user")
    user_items: Mapped[list["UserItem"]] = relationship(back_populates="user")
    tags: Mapped[list["Tag"]] = relationship(back_populates="user")
    collections: Mapped[list["Collection"]] = relationship(back_populates="user")
