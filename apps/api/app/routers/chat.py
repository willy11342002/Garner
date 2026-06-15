from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

from app.dependencies import CurrentUser, DbSession
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
)
from app.services import chat_service

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
    return session


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


# ── Messages（streaming）────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: UUID,
    body: SendMessageRequest,
    current_user: CurrentUser,
    db: DbSession,
    background_tasks: BackgroundTasks,
    _quota: ChatQuota,
):
    if not body.content.strip():
        raise HTTPException(status_code=422, detail="content cannot be empty")

    user_id = UUID(current_user["sub"])
    session = await crud_chat.get_session_with_messages(db, session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return StreamingResponse(
        chat_service.stream_reply(
            db, session_id, user_id, body.content.strip(),
            background_tasks, context_item_ids=body.item_ids or [],
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
