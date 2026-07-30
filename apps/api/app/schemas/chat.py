from datetime import datetime
from typing import Literal
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
    status: str = "complete"
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

class MessageScope(BaseModel):
    """使用者「正在編輯的東西」。

    行程頁／報告頁的 AI 懸浮球就是帶著這個欄位的 chat —— 沒有專屬端口。
    只帶 kind + id，實際內容（卡片清單／報告全文）與權限一律由後端自己查，
    不信任前端送來的任何狀態。
    """
    kind: Literal["trip", "report"]
    id: UUID


class SendMessageRequest(BaseModel):
    content: str
    item_ids: list[UUID] = []  # 明確指定要注入 context 的知識節點（探索頁跳轉用）
    scope: MessageScope | None = None  # 懸浮球：使用者當前正在編輯的行程／報告


class SendMessageResponse(BaseModel):
    message_id: UUID
