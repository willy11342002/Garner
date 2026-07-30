from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ReportSourceItem(BaseModel):
    """產出的來源知識（provenance），供前端顯示「從 N 則收藏彙整」並可點回原始 item。"""

    id: UUID
    title: str | None = None
    url: str | None = None
    thumbnail_url: str | None = None
    source_type: str | None = None

    model_config = {"from_attributes": True}


class ReportRead(BaseModel):
    id: UUID
    title: str
    body_md: str
    summary: str | None = None
    sources: list[ReportSourceItem] = []
    last_edited_by: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportListItem(BaseModel):
    """列表用精簡版，不含 body_md。"""

    id: UUID
    title: str
    summary: str | None = None
    source_count: int = 0
    last_edited_by: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportUpdate(BaseModel):
    title: str | None = None
    body_md: str | None = None


class ReportReviseRequest(BaseModel):
    instruction: str


# AI 修改報告走 chat 的 SendMessageRequest（帶 scope），這裡不再有專屬 schema。
