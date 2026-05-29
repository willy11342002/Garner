from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.crud import collections as crud_collections
from app.crud import items as crud_items
from app.dependencies import CurrentUser, DbSession
from app.models.content_object import ContentObject
from app.schemas.collection import (
    CollectionCreate,
    CollectionForkCreate,
    CollectionRead,
    CollectionReadDetail,
    CollectionUpdate,
)
from app.schemas.item import ItemRead

router = APIRouter()


def _collection_detail(collection) -> CollectionReadDetail:
    items = [
        ItemRead(
            id=ci.content.id,
            url=ci.content.url,
            title=ci.content.title,
            summary=ci.content.summary,
            thumbnail_url=ci.content.thumbnail_url,
            saved_at=ci.added_at,
            deleted_at=None,
        )
        for ci in (collection.collection_items or [])
    ]
    return CollectionReadDetail(
        id=collection.id,
        title=collection.title,
        visibility=collection.visibility,
        slug=collection.slug,
        fork_count=collection.fork_count,
        created_at=collection.created_at,
        items=items,
    )


@router.get("/", response_model=list[CollectionRead])
async def list_collections(current_user: CurrentUser, db: DbSession):
    return await crud_collections.get_all(db, UUID(current_user["sub"]))


@router.post("/", response_model=CollectionRead, status_code=status.HTTP_201_CREATED)
async def create_collection(data: CollectionCreate, current_user: CurrentUser, db: DbSession):
    collection = await crud_collections.create(db, UUID(current_user["sub"]), data)
    await db.commit()
    return collection


@router.get("/{collection_id}", response_model=CollectionReadDetail)
async def get_collection(collection_id: UUID, current_user: CurrentUser, db: DbSession):
    collection = await crud_collections.get_one(db, UUID(current_user["sub"]), collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return _collection_detail(collection)


@router.patch("/{collection_id}", response_model=CollectionRead)
async def update_collection(
    collection_id: UUID, data: CollectionUpdate, current_user: CurrentUser, db: DbSession
):
    collection = await crud_collections.get_one(db, UUID(current_user["sub"]), collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    collection = await crud_collections.update(db, collection, data)
    await db.commit()
    return collection


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(collection_id: UUID, current_user: CurrentUser, db: DbSession):
    collection = await crud_collections.get_one(db, UUID(current_user["sub"]), collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    await crud_collections.delete_collection(db, collection)
    await db.commit()


@router.post("/{collection_id}/items", status_code=status.HTTP_204_NO_CONTENT)
async def add_item_to_collection(
    collection_id: UUID, content_id: UUID, current_user: CurrentUser, db: DbSession
):
    collection = await crud_collections.get_one(db, UUID(current_user["sub"]), collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    user_item = await crud_items.get_by_content_id(db, UUID(current_user["sub"]), content_id)
    if user_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    await crud_collections.add_item(db, collection_id, content_id)
    await db.commit()


@router.post("/{collection_id}/items/from-public", status_code=status.HTTP_204_NO_CONTENT)
async def add_public_item_to_collection(
    collection_id: UUID, content_id: UUID, current_user: CurrentUser, db: DbSession
):
    collection = await crud_collections.get_one(db, UUID(current_user["sub"]), collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    result = await db.execute(select(ContentObject).where(ContentObject.id == content_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Content not found")
    await crud_collections.add_item(db, collection_id, content_id)
    await db.commit()


@router.delete("/{collection_id}/items/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item_from_collection(
    collection_id: UUID, content_id: UUID, current_user: CurrentUser, db: DbSession
):
    collection = await crud_collections.get_one(db, UUID(current_user["sub"]), collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    await crud_collections.remove_item(db, collection_id, content_id)
    await db.commit()


@router.post("/{collection_id}/fork", response_model=CollectionRead, status_code=status.HTTP_201_CREATED)
async def fork_collection(
    collection_id: UUID, data: CollectionForkCreate, current_user: CurrentUser, db: DbSession
):
    source = await crud_collections.get_by_id_with_items(db, collection_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    title = data.title or source.title
    new_collection = await crud_collections.fork_collection(
        db, source, UUID(current_user["sub"]), title, data.content_ids, data.visibility
    )
    await db.commit()
    return new_collection
