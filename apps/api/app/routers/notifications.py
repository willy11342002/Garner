from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import notifications as crud_notifications
from app.dependencies import get_current_user, get_db
from app.schemas.notification import NotificationMarkRead, NotificationRead

router = APIRouter()


@router.get("", response_model=list[NotificationRead])
async def list_notifications(
    unread_only: bool = False,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await crud_notifications.list_for_user(
        db, UUID(current_user["sub"]), unread_only=unread_only, limit=min(limit, 100)
    )


@router.patch("/read")
async def mark_read(
    payload: NotificationMarkRead,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await crud_notifications.mark_read(db, UUID(current_user["sub"]), payload.ids)
    await db.commit()
    return {"ok": True}


@router.patch("/read-all")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await crud_notifications.mark_all_read(db, UUID(current_user["sub"]))
    await db.commit()
    return {"ok": True}
