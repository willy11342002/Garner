from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.collection import Collection
from app.models.collection_item import CollectionItem
from app.schemas.collection import CollectionCreate, CollectionUpdate


async def get_all(db: AsyncSession, user_id: UUID) -> list[Collection]:
    result = await db.execute(
        select(Collection)
        .where(Collection.user_id == user_id)
        .order_by(Collection.created_at.desc())
    )
    return list(result.scalars().all())


async def get_one(db: AsyncSession, user_id: UUID, collection_id: UUID) -> Collection | None:
    result = await db.execute(
        select(Collection)
        .where(Collection.id == collection_id, Collection.user_id == user_id)
        .options(joinedload(Collection.collection_items).joinedload(CollectionItem.content))
    )
    return result.scalar_one_or_none()


async def create(db: AsyncSession, user_id: UUID, data: CollectionCreate) -> Collection:
    collection = Collection(
        user_id=user_id,
        title=data.title,
        visibility=data.visibility,
        slug=data.slug,
    )
    db.add(collection)
    await db.flush()
    await db.refresh(collection)
    return collection


async def update(db: AsyncSession, collection: Collection, data: CollectionUpdate) -> Collection:
    if data.title is not None:
        collection.title = data.title
    if data.visibility is not None:
        collection.visibility = data.visibility
    await db.flush()
    return collection


async def delete_collection(db: AsyncSession, collection: Collection) -> None:
    await db.execute(
        delete(CollectionItem).where(CollectionItem.collection_id == collection.id)
    )
    await db.delete(collection)
    await db.flush()


async def add_item(db: AsyncSession, collection_id: UUID, content_id: UUID) -> CollectionItem:
    result = await db.execute(
        select(CollectionItem).where(
            CollectionItem.collection_id == collection_id,
            CollectionItem.content_id == content_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    ci = CollectionItem(collection_id=collection_id, content_id=content_id)
    db.add(ci)
    await db.flush()
    return ci


async def remove_item(db: AsyncSession, collection_id: UUID, content_id: UUID) -> None:
    await db.execute(
        delete(CollectionItem).where(
            CollectionItem.collection_id == collection_id,
            CollectionItem.content_id == content_id,
        )
    )
    await db.flush()
