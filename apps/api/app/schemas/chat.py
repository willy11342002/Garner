from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


# ── Folder ──────────────────────────────────────────────────────────────────

class ChatFolderCreate(BaseModel):
    name: str


class ChatFolderUpdate(BaseModel):
    name: str


class ChatFolderRead(BaseModel):
    id: UUID
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Session ──────────────────────────────────────────────────────────────────

class ChatSessionCreate(BaseModel):
    folder_id: UUID | None = None


class ChatSessionUpdate(BaseModel):
    title: str | None = None
    folder_id: UUID | None = None


class ChatSessionRead(BaseModel):
    id: UUID
    folder_id: UUID | None
    title: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Message ──────────────────────────────────────────────────────────────────

class ChatMessageRead(BaseModel):
    id: UUID
    role: str
    content: str
    cited_item_ids: list[UUID] | None
    process_log: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionDetail(ChatSessionRead):
    messages: list[ChatMessageRead] = []


# ── Source card（回傳給前端的引用 item）────────────────────────────────────────

class ChatSource(BaseModel):
    id: UUID
    url: str
    title: str | None
    thumbnail_url: str | None
    source_type: str | None
    distance: float | None = None
    locations: list[str] = []


# ── Send message request ──────────────────────────────────────────────────────

class SendMessageRequest(BaseModel):
    content: str
    item_ids: list[UUID] = []  # 明確指定要注入 context 的知識節點（探索頁跳轉用）
