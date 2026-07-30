import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.dependencies import CurrentUser, DbSession
from app.models.chat import MessageRole
from app.quota_depends import ChatQuota
from app.crud import chat as crud_chat
from app.schemas.chat import (
    ChatFolderCreate,
    ChatFolderRead,
    ChatFolderUpdate,
    ChatSessionCreate,
    ChatSessionDetail,
    ChatSessionRead,
    ChatSessionUpdate,
    SendMessageRequest,
    SendMessageResponse,
)
from app.services import chat_service
from app.services.stream_registry import drain_entry, stream_registry

router = APIRouter()


# ── Folders ───────────────────────────────────────────────────────────────────

@router.get("/folders", response_model=list[ChatFolderRead])
async def list_folders(current_user: CurrentUser, db: DbSession):
    return await crud_chat.list_folders(db, UUID(current_user["sub"]))


@router.post("/folders", response_model=ChatFolderRead, status_code=201)
async def create_folder(body: ChatFolderCreate, current_user: CurrentUser, db: DbSession):
    return await crud_chat.create_folder(db, UUID(current_user["sub"]), body.name)


@router.patch("/folders/{folder_id}", response_model=ChatFolderRead)
async def update_folder(folder_id: UUID, body: ChatFolderUpdate, current_user: CurrentUser, db: DbSession):
    folder = await crud_chat.update_folder(db, folder_id, UUID(current_user["sub"]), body.name)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    return folder


@router.delete("/folders/{folder_id}", status_code=204)
async def delete_folder(folder_id: UUID, current_user: CurrentUser, db: DbSession):
    ok = await crud_chat.delete_folder(db, folder_id, UUID(current_user["sub"]))
    if not ok:
        raise HTTPException(status_code=404, detail="Folder not found")


# ── Sessions ───────────────────────────────────────────────────────────────────

@router.get("/sessions", response_model=list[ChatSessionRead])
async def list_sessions(current_user: CurrentUser, db: DbSession):
    return await crud_chat.list_sessions(db, UUID(current_user["sub"]))


@router.post("/sessions", response_model=ChatSessionRead, status_code=201)
async def create_session(body: ChatSessionCreate, current_user: CurrentUser, db: DbSession):
    return await crud_chat.create_session(db, UUID(current_user["sub"]), body.folder_id)


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
async def get_session(session_id: UUID, current_user: CurrentUser, db: DbSession):
    session = await crud_chat.get_session_with_messages(db, session_id, UUID(current_user["sub"]))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    # 序列化後過濾，避免直接改 ORM relationship 觸發 delete-orphan cascade
    detail = ChatSessionDetail.model_validate(session)
    detail.messages = [m for m in detail.messages if m.status == "complete"]
    return detail


@router.patch("/sessions/{session_id}", response_model=ChatSessionRead)
async def update_session(session_id: UUID, body: ChatSessionUpdate, current_user: CurrentUser, db: DbSession):
    session = await crud_chat.update_session(
        db, session_id, UUID(current_user["sub"]),
        title=body.title, folder_id=body.folder_id,
        set_folder="folder_id" in body.model_fields_set,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: UUID, current_user: CurrentUser, db: DbSession):
    ok = await crud_chat.delete_session(db, session_id, UUID(current_user["sub"]))
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")


# ── Messages ────────────────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse, status_code=201)
async def send_message(
    session_id: UUID,
    body: SendMessageRequest,
    current_user: CurrentUser,
    db: DbSession,
    _quota: ChatQuota,
):
    if not body.content.strip():
        raise HTTPException(status_code=422, detail="content cannot be empty")

    user_id = UUID(current_user["sub"])
    session = await crud_chat.get_session_with_messages(db, session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    content = body.content.strip()

    # Set session title on first message
    if not session.title:
        title = content[:40] + ("…" if len(content) > 40 else "")
        await crud_chat.update_session(db, session_id, user_id, title=title)

    # Persist user message immediately
    await crud_chat.add_message(
        db, session_id, MessageRole.user, content,
        cited_item_ids=body.item_ids if body.item_ids else None,
    )

    # Create assistant placeholder (status=pending)
    asst_msg = await crud_chat.create_assistant_placeholder(db, session_id)

    # Register stream entry and launch background generation
    stream_registry.create(asst_msg.id)
    asyncio.create_task(
        chat_service.run_reply_background(
            asst_msg.id, session_id, user_id, content, body.item_ids or [],
            scope=body.scope.model_dump(mode="json") if body.scope else None,
        )
    )

    return SendMessageResponse(message_id=asst_msg.id)


@router.get("/sessions/{session_id}/messages/{message_id}/stream")
async def stream_message(
    session_id: UUID,
    message_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    user_id = UUID(current_user["sub"])

    # Auth: verify session belongs to user
    session = await crud_chat.get_session_with_messages(db, session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    entry = stream_registry.get(message_id)
    if entry is not None:
        return StreamingResponse(
            drain_entry(entry),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # Not in registry — check DB
    msg = await crud_chat.get_message(db, message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    if msg.status == "failed":
        raise HTTPException(status_code=500, detail="Generation failed")

    if msg.status == "complete":
        return StreamingResponse(
            _replay_complete_message(msg),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    raise HTTPException(status_code=503, detail="Stream not available")


async def _replay_complete_message(msg):
    """從 DB 重建 SSE 事件，供斷線後重連使用。"""
    if msg.content:
        chunk_size = 200
        for i in range(0, len(msg.content), chunk_size):
            chunk = msg.content[i:i + chunk_size]
            yield f"event: delta\ndata: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"

    if msg.cited_item_ids:
        yield f"event: sources\ndata: {json.dumps({'ids': [str(i) for i in msg.cited_item_ids]}, ensure_ascii=False)}\n\n"

    # 把 process_log 帶進 done，讓前端直接還原 tool calling 顯示
    done_payload: dict = {"message_id": str(msg.id)}
    if msg.process_log:
        done_payload["process_log"] = msg.process_log
    yield f"event: done\ndata: {json.dumps(done_payload, ensure_ascii=False)}\n\n"
