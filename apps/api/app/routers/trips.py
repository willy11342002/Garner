from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.crud import trips as crud_trips
from app.dependencies import CurrentUser, DbSession
from app.schemas.trip import (
    TripCreate,
    TripInviteLinkUpdate,
    TripItemCreate,
    TripItemRead,
    TripItemReorderRequest,
    TripItemUpdate,
    TripListItem,
    TripMemberCreate,
    TripMemberRead,
    TripMemberUpdate,
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


# AI 修改行程沒有專屬端口 —— 行程頁的 AI 懸浮球直接打 chat 的
# POST /chat/sessions/{id}/messages（帶 scope={"kind":"trip","id":...}），
# 跟首頁 chat 走完全同一條路。

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


# ── Trip Members ──────────────────────────────────────────────────────────────

@router.get("/{trip_id}/members", response_model=list[TripMemberRead])
async def list_members(trip_id: UUID, current_user: CurrentUser, db: DbSession):
    members = await trip_service.list_members(db, UUID(current_user["sub"]), trip_id)
    if members is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return members


@router.post("/{trip_id}/members", response_model=TripMemberRead, status_code=status.HTTP_201_CREATED)
async def invite_member(
    trip_id: UUID, data: TripMemberCreate, current_user: CurrentUser, db: DbSession
):
    member = await trip_service.invite_member_by_email(
        db, UUID(current_user["sub"]), trip_id, data.email, data.role
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Trip or user not found")
    return member


@router.patch("/{trip_id}/members/{member_id}", response_model=TripMemberRead)
async def update_member_role(
    trip_id: UUID, member_id: UUID, data: TripMemberUpdate, current_user: CurrentUser, db: DbSession
):
    member = await trip_service.update_member_role(
        db, UUID(current_user["sub"]), trip_id, member_id, data.role
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Trip or member not found")
    return member


@router.delete("/{trip_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    trip_id: UUID, member_id: UUID, current_user: CurrentUser, db: DbSession
):
    ok = await trip_service.remove_member(
        db, UUID(current_user["sub"]), trip_id, member_id
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Trip or member not found")


@router.post("/{trip_id}/invite-link", response_model=TripRead)
async def generate_invite_link(
    trip_id: UUID, data: TripInviteLinkUpdate, current_user: CurrentUser, db: DbSession
):
    trip = await trip_service.generate_invite_link(
        db, UUID(current_user["sub"]), trip_id, data.role
    )
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@router.delete("/{trip_id}/invite-link", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invite_link(trip_id: UUID, current_user: CurrentUser, db: DbSession):
    ok = await trip_service.revoke_invite_link(db, UUID(current_user["sub"]), trip_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Trip not found")


@router.post("/join/{token}", response_model=TripMemberRead)
async def join_trip_by_token(token: UUID, current_user: CurrentUser, db: DbSession):
    member = await trip_service.join_by_invite_token(db, UUID(current_user["sub"]), token)
    if member is None:
        raise HTTPException(status_code=404, detail="Invite link invalid or already joined as owner")
    return member


