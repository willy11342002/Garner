import re
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.collection import Collection, CollectionVisibility
from app.models.collection_item import CollectionItem
from app.models.tag import Tag
from app.models.user import User
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
    return result.unique().scalar_one_or_none()


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


async def count_public(db: AsyncSession, user_id: UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(Collection)
        .where(
            Collection.user_id == user_id,
            Collection.visibility == CollectionVisibility.public,
        )
    )
    return result.scalar_one()


async def get_by_id_with_items(db: AsyncSession, collection_id: UUID) -> Collection | None:
    result = await db.execute(
        select(Collection)
        .where(
            Collection.id == collection_id,
            Collection.visibility.in_([CollectionVisibility.public, CollectionVisibility.link]),
        )
        .options(joinedload(Collection.collection_items).joinedload(CollectionItem.content))
    )
    return result.unique().scalar_one_or_none()


async def get_public_by_slug(db: AsyncSession, slug: str) -> Collection | None:
    result = await db.execute(
        select(Collection)
        .where(
            Collection.slug == slug,
            Collection.visibility.in_([CollectionVisibility.public, CollectionVisibility.link]),
        )
        .options(
            joinedload(Collection.user),
            joinedload(Collection.collection_items).joinedload(CollectionItem.content),
        )
    )
    return result.unique().scalar_one_or_none()


async def list_public(
    db: AsyncSession,
    q: str | None = None,
    tag: str | None = None,
    offset: int = 0,
    limit: int = 24,
) -> list[tuple[Collection, int]]:
    item_count_subq = (
        select(CollectionItem.collection_id, func.count().label("cnt"))
        .group_by(CollectionItem.collection_id)
        .subquery()
    )
    stmt = (
        select(Collection, func.coalesce(item_count_subq.c.cnt, 0).label("item_count"))
        .join(item_count_subq, item_count_subq.c.collection_id == Collection.id, isouter=True)
        .join(Collection.user)
        .where(Collection.visibility == CollectionVisibility.public)
        .options(
            joinedload(Collection.user),
            joinedload(Collection.source_tag),
            joinedload(Collection.collection_items).joinedload(CollectionItem.content),
        )
    )
    if q:
        stmt = stmt.where(Collection.title.ilike(f"%{q}%"))
    if tag:
        stmt = stmt.join(Collection.source_tag).where(Tag.name.ilike(f"%{tag}%"))
    stmt = stmt.order_by(Collection.fork_count.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return [(row.Collection, row.item_count) for row in result.unique().all()]


async def fork_collection(
    db: AsyncSession,
    source: Collection,
    user_id: UUID,
    title: str,
    content_ids: list[UUID],
    visibility: CollectionVisibility = CollectionVisibility.link,
) -> Collection:
    slug_base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
    slug = f"{slug_base}-{str(uuid4())[:8]}"

    new_collection = Collection(
        user_id=user_id,
        title=title,
        visibility=visibility,
        slug=slug,
        fork_from_collection_id=source.id,
    )
    db.add(new_collection)
    await db.flush()

    items_to_copy = source.collection_items
    if content_ids:
        id_set = set(content_ids)
        items_to_copy = [ci for ci in items_to_copy if ci.content_id in id_set]

    for ci in items_to_copy:
        db.add(CollectionItem(collection_id=new_collection.id, content_id=ci.content_id))

    source.fork_count += 1
    await db.flush()
    await db.refresh(new_collection)
    return new_collection
