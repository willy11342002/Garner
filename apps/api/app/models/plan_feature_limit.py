from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PlanFeatureLimit(Base):
    """
    (plan_id, feature) 複合 PK。value = NULL 代表無限制。

    feature: 'saves_monthly' | 'chat_daily' | 'synthesis_monthly'
           | 'video_max_sec' | 'search' | 'fork'
    value:   整數上限（NULL = 無限）；boolean feature 用 0/1 表示
    """
    __tablename__ = "plan_feature_limits"

    plan_id: Mapped[UUID] = mapped_column(ForeignKey("plans.id"), primary_key=True)
    feature: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[int | None] = mapped_column(Integer, nullable=True)
