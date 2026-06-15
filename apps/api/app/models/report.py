from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Report(Base):
    """AI 產出層：由 chat 生成的報告/規劃/指南。

    與「知識」(user_items) 嚴格分離：
    - 不進語意搜尋語料（無 embedding、不寫 content_chunks）
    - 不走擷取管線（無 url / thumbnail / pipeline 欄位）
    - 可由 AI 或人編輯，但永不自動回流成知識（無 promote）
    """

    __tablename__ = "reports"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body_md: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # provenance：產出來源的 user_item id 清單（字串）。不設 FK，因 user_items 走軟刪除。
    source_item_ids: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    # "ai" | "user"：最後一次修改 body 的來源
    last_edited_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    # 註：報告為產出層、可重生，採直接硬刪除，不設 deleted_at 軟刪除欄位
