from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, status

from app.crud import tags as crud_tags
from app.dependencies import CurrentUser, DbSession
from app.schemas.item import ItemCreate, ItemRead, ItemUpdate
from app.schemas.tag import TagCreate, TagRead
from app.services import item_service

router = APIRouter()


@router.get("/", response_model=list[ItemRead])
async def list_items(current_user: CurrentUser, db: DbSession):
    return await item_service.list_items(db, UUID(current_user["sub"]))


@router.post("/", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(
    data: ItemCreate,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DbSession,
):
    return await item_service.create_item(db, UUID(current_user["sub"]), data, background_tasks)


@router.get("/{item_id}", response_model=ItemRead)
async def get_item(item_id: UUID, current_user: CurrentUser, db: DbSession):
    return await item_service.get_item(db, UUID(current_user["sub"]), item_id)


@router.patch("/{item_id}", response_model=ItemRead)
async def update_item(item_id: UUID, data: ItemUpdate, current_user: CurrentUser, db: DbSession):
    return await item_service.update_item(db, UUID(current_user["sub"]), item_id, data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: UUID, current_user: CurrentUser, db: DbSession):
    await item_service.delete_item(db, UUID(current_user["sub"]), item_id)


@router.get("/{item_id}/tags", response_model=list[TagRead])
async def list_item_tags(item_id: UUID, current_user: CurrentUser, db: DbSession):
    from sqlalchemy import select
    from app.models.item_tag import ItemTag
    from app.models.tag import Tag
    result = await db.execute(
        select(Tag)
        .join(ItemTag, ItemTag.tag_id == Tag.id)
        .where(ItemTag.user_item_id == item_id, Tag.user_id == UUID(current_user["sub"]))
    )
    return list(result.scalars().all())


@router.post("/{item_id}/tags", status_code=status.HTTP_204_NO_CONTENT)
async def attach_tag(item_id: UUID, data: TagCreate, current_user: CurrentUser, db: DbSession):
    user_id = UUID(current_user["sub"])
    tag = await crud_tags.get_or_create(db, user_id, data.name)
    await crud_tags.attach_tag(db, item_id, tag.id)
    await db.commit()


@router.delete("/{item_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def detach_tag(item_id: UUID, tag_id: UUID, current_user: CurrentUser, db: DbSession):
    await crud_tags.detach_tag(db, item_id, tag_id)
    await db.commit()
