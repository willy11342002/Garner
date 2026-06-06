from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserFeatureUsage(Base):
    """
    (user_id, feature, period_key) UNIQUE。用 UPSERT 累加計數。

    period_key 格式：
      monthly → "2026-06"
      daily   → "2026-06-06"
    """
    __tablename__ = "user_feature_usage"
    __table_args__ = (UniqueConstraint("user_id", "feature", "period_key"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    feature: Mapped[str] = mapped_column(String(40), nullable=False)
    period_key: Mapped[str] = mapped_column(String(10), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
