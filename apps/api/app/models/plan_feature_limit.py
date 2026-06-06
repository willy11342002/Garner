from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PlanFeatureLimit(Base):
    """
    (plan, feature) 複合 PK。value = NULL 代表無限制。

    plan:    'free' | 'pro'
    feature: 'saves_monthly' | 'chat_daily' | 'explore_monthly'
           | 'video_max_sec' | 'search' | 'fork'
    value:   整數上限（NULL = 無限）；boolean feature 用 0/1 表示
    """
    __tablename__ = "plan_feature_limits"

    plan: Mapped[str] = mapped_column(String(20), primary_key=True)
    feature: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[int | None] = mapped_column(Integer, nullable=True)
