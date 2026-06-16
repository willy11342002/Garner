from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.crud import trips as crud_trips
from app.dependencies import CurrentUser, DbSession
from app.quota_depends import ChatQuota
from app.schemas.trip import (
    TripAIEditRequest,
    TripCreate,
    TripItemCreate,
    TripItemRead,
    TripItemReorderRequest,
    TripItemUpdate,
    TripListItem,
    TripRead,
    TripTagCreate,
    TripTagRead,
    TripTagUpdate,
    TripUpdate,
)
from app.services import trip_service

router = APIRouter()


# ── Trips ─────────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[TripListItem])
async def list_trips(current_user: CurrentUser, db: DbSession):
    return await trip_service.list_trips(db, UUID(current_user["sub"]))


@router.post("/", response_model=TripRead, status_code=status.HTTP_201_CREATED)
async def create_trip(data: TripCreate, current_user: CurrentUser, db: DbSession):
    return await trip_service.create_trip(db, UUID(current_user["sub"]), data)


@router.get("/{trip_id}", response_model=TripRead)
async def get_trip(trip_id: UUID, current_user: CurrentUser, db: DbSession):
    trip = await trip_service.get_trip(db, UUID(current_user["sub"]), trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@router.patch("/{trip_id}", response_model=TripRead)
async def update_trip(
    trip_id: UUID, data: TripUpdate, current_user: CurrentUser, db: DbSession
):
    trip = await trip_service.update_trip(db, UUID(current_user["sub"]), trip_id, data)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip(trip_id: UUID, current_user: CurrentUser, db: DbSession):
    ok = await trip_service.delete_trip(db, UUID(current_user["sub"]), trip_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Trip not found")


@router.post("/{trip_id}/ai-edit")
async def ai_edit_trip(
    trip_id: UUID,
    data: TripAIEditRequest,
    current_user: CurrentUser,
    db: DbSession,
    _quota: ChatQuota,
):
    """AI 修改既有行程（SSE 串流，逐動作回傳卡片變更）。"""
    if not data.instruction.strip():
        raise HTTPException(status_code=422, detail="instruction cannot be empty")

    from app.services import ai_service

    history = [t.model_dump() for t in data.history] if data.history else None
    agen = trip_service.ai_edit_trip_stream(
        db, UUID(current_user["sub"]), trip_id, data.instruction.strip(), history=history
    )
    return StreamingResponse(
        ai_service.with_heartbeat(agen),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Trip Items ────────────────────────────────────────────────────────────────

@router.post("/{trip_id}/items", response_model=TripItemRead, status_code=status.HTTP_201_CREATED)
async def add_item(
    trip_id: UUID, data: TripItemCreate, current_user: CurrentUser, db: DbSession
):
    item = await trip_service.add_item(db, UUID(current_user["sub"]), trip_id, data)
    if item is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return item


@router.patch("/{trip_id}/items/{item_id}", response_model=TripItemRead)
async def update_item(
    trip_id: UUID,
    item_id: UUID,
    data: TripItemUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    item = await trip_service.update_item(
        db, UUID(current_user["sub"]), trip_id, item_id, data
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Trip or item not found")
    return item


@router.delete("/{trip_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    trip_id: UUID, item_id: UUID, current_user: CurrentUser, db: DbSession
):
    ok = await trip_service.delete_item(
        db, UUID(current_user["sub"]), trip_id, item_id
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Trip or item not found")


@router.patch("/{trip_id}/items/reorder", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def reorder_items(
    trip_id: UUID,
    data: TripItemReorderRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    ok = await trip_service.reorder_items(
        db, UUID(current_user["sub"]), trip_id, data.items
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Trip not found")


