from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.crud import trips as crud_trips
from app.dependencies import CurrentUser, DbSession
from app.schemas.trip import TripTagCreate, TripTagRead, TripTagUpdate

router = APIRouter()


@router.get("/", response_model=list[TripTagRead])
async def list_trip_tags(current_user: CurrentUser, db: DbSession):
    return await crud_trips.list_tags(db, UUID(current_user["sub"]))


@router.post("/", response_model=TripTagRead, status_code=status.HTTP_201_CREATED)
async def create_trip_tag(data: TripTagCreate, current_user: CurrentUser, db: DbSession):
    return await crud_trips.get_or_create_tag(
        db, UUID(current_user["sub"]), data.name, data.color
    )


@router.patch("/{tag_id}", response_model=TripTagRead)
async def update_trip_tag(
    tag_id: UUID, data: TripTagUpdate, current_user: CurrentUser, db: DbSession
):
    tag = await crud_trips.get_tag(db, UUID(current_user["sub"]), tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return await crud_trips.update_tag(db, tag, name=data.name, color=data.color)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip_tag(tag_id: UUID, current_user: CurrentUser, db: DbSession):
    tag = await crud_trips.get_tag(db, UUID(current_user["sub"]), tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    await crud_trips.delete_tag(db, tag)
