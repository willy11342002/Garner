from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.crud import tags as crud_tags
from app.dependencies import CurrentUser, DbSession
from app.schemas.item import ItemRead
from app.schemas.tag import TagCreate, TagRead, TagUpdate
from app.services import item_service

router = APIRouter()


@router.get("/", response_model=list[TagRead])
async def list_tags(current_user: CurrentUser, db: DbSession):
    return await crud_tags.get_all(db, UUID(current_user["sub"]))


@router.post("/", response_model=TagRead, status_code=status.HTTP_201_CREATED)
async def create_tag(data: TagCreate, current_user: CurrentUser, db: DbSession):
    tag = await crud_tags.get_or_create(db, UUID(current_user["sub"]), data.name)
    await db.commit()
    return tag


@router.get("/{tag_id}", response_model=TagRead)
async def get_tag(tag_id: UUID, current_user: CurrentUser, db: DbSession):
    tag = await crud_tags.get_one(db, UUID(current_user["sub"]), tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.patch("/{tag_id}", response_model=TagRead)
async def update_tag(tag_id: UUID, data: TagUpdate, current_user: CurrentUser, db: DbSession):
    tag = await crud_tags.get_one(db, UUID(current_user["sub"]), tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    tag = await crud_tags.update(db, tag, data.name)
    await db.commit()
    return tag


@router.get("/{tag_id}/items", response_model=list[ItemRead])
async def list_tag_items(tag_id: UUID, current_user: CurrentUser, db: DbSession):
    user_id = UUID(current_user["sub"])
    tag = await crud_tags.get_one(db, user_id, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    user_items = await crud_tags.get_items_by_tag(db, user_id, tag_id)
    return [item_service._item_to_read(ui) for ui in user_items]


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(tag_id: UUID, current_user: CurrentUser, db: DbSession):
    tag = await crud_tags.get_one(db, UUID(current_user["sub"]), tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    await crud_tags.delete_tag(db, tag)
    await db.commit()
