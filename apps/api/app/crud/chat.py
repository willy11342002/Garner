from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import ChatFolder, ChatMessage, ChatSession, MessageRole
from app.models.user import User


# ── Folders ───────────────────────────────────────────────────────────────────

async def list_folders(db: AsyncSession, user_id: UUID) -> list[ChatFolder]:
    result = await db.execute(
        select(ChatFolder)
        .where(ChatFolder.user_id == user_id)
        .order_by(ChatFolder.created_at)
    )
    return list(result.scalars().all())


async def create_folder(db: AsyncSession, user_id: UUID, name: str) -> ChatFolder:
    folder = ChatFolder(id=uuid4(), user_id=user_id, name=name)
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return folder


async def update_folder(db: AsyncSession, folder_id: UUID, user_id: UUID, name: str) -> ChatFolder | None:
    result = await db.execute(
        select(ChatFolder).where(ChatFolder.id == folder_id, ChatFolder.user_id == user_id)
    )
    folder = result.scalar_one_or_none()
    if not folder:
        return None
    folder.name = name
    await db.commit()
    await db.refresh(folder)
    return folder


async def delete_folder(db: AsyncSession, folder_id: UUID, user_id: UUID) -> bool:
    result = await db.execute(
        select(ChatFolder).where(ChatFolder.id == folder_id, ChatFolder.user_id == user_id)
    )
    folder = result.scalar_one_or_none()
    if not folder:
        return False
    await db.delete(folder)
    await db.commit()
    return True


# ── Sessions ───────────────────────────────────────────────────────────────────

async def list_sessions(db: AsyncSession, user_id: UUID) -> list[ChatSession]:
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc())
    )
    return list(result.scalars().all())


async def create_session(db: AsyncSession, user_id: UUID, folder_id: UUID | None = None) -> ChatSession:
    session = ChatSession(id=uuid4(), user_id=user_id, folder_id=folder_id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session_with_messages(db: AsyncSession, session_id: UUID, user_id: UUID) -> ChatSession | None:
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def update_session(
    db: AsyncSession,
    session_id: UUID,
    user_id: UUID,
    title: str | None = None,
    folder_id: UUID | None = None,
) -> ChatSession | None:
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        return None
    if title is not None:
        session.title = title
    if folder_id is not None:
        session.folder_id = folder_id
    session.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(session)
    return session


async def delete_session(db: AsyncSession, session_id: UUID, user_id: UUID) -> bool:
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        return False
    await db.delete(session)
    await db.commit()
    return True


async def touch_session(db: AsyncSession, session_id: UUID) -> None:
    await db.execute(
        update(ChatSession)
        .where(ChatSession.id == session_id)
        .values(updated_at=datetime.now(timezone.utc))
    )
    await db.commit()


# ── Messages ───────────────────────────────────────────────────────────────────

async def add_message(
    db: AsyncSession,
    session_id: UUID,
    role: MessageRole,
    content: str,
    cited_item_ids: list[UUID] | None = None,
    process_log: dict | None = None,
) -> ChatMessage:
    msg = ChatMessage(
        id=uuid4(),
        session_id=session_id,
        role=role,
        content=content,
        cited_item_ids=cited_item_ids,
        process_log=process_log,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def count_messages(db: AsyncSession, session_id: UUID) -> int:
    from sqlalchemy import func
    result = await db.execute(
        select(func.count()).where(ChatMessage.session_id == session_id)
    )
    return result.scalar_one()


# ── Memory ────────────────────────────────────────────────────────────────────

async def get_memory_summary(db: AsyncSession, user_id: UUID) -> str | None:
    result = await db.execute(select(User.memory_summary).where(User.id == user_id))
    return result.scalar_one_or_none()


async def set_memory_summary(db: AsyncSession, user_id: UUID, summary: str) -> None:
    await db.execute(
        update(User).where(User.id == user_id).values(memory_summary=summary)
    )
    await db.commit()
