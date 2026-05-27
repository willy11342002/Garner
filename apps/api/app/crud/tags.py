from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item_tag import ItemTag, TagSource
from app.models.tag import Tag


async def get_all(db: AsyncSession, user_id: UUID) -> list[Tag]:
    result = await db.execute(
        select(Tag).where(Tag.user_id == user_id).order_by(Tag.name)
    )
    return list(result.scalars().all())


async def get_one(db: AsyncSession, user_id: UUID, tag_id: UUID) -> Tag | None:
    result = await db.execute(
        select(Tag).where(Tag.id == tag_id, Tag.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_or_create(db: AsyncSession, user_id: UUID, name: str) -> Tag:
    result = await db.execute(
        select(Tag).where(Tag.user_id == user_id, Tag.name == name)
    )
    tag = result.scalar_one_or_none()
    if tag is None:
        tag = Tag(user_id=user_id, name=name)
        db.add(tag)
        await db.flush()
    return tag


async def update(db: AsyncSession, tag: Tag, name: str) -> Tag:
    tag.name = name
    await db.flush()
    return tag


async def delete_tag(db: AsyncSession, tag: Tag) -> None:
    await db.execute(delete(ItemTag).where(ItemTag.tag_id == tag.id))
    await db.delete(tag)
    await db.flush()


async def attach_tag(
    db: AsyncSession, user_item_id: UUID, tag_id: UUID, source: TagSource = TagSource.user
) -> ItemTag:
    result = await db.execute(
        select(ItemTag).where(
            ItemTag.user_item_id == user_item_id, ItemTag.tag_id == tag_id
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    item_tag = ItemTag(user_item_id=user_item_id, tag_id=tag_id, source=source)
    db.add(item_tag)
    await db.flush()

    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    if tag:
        tag.item_count += 1
        tag.last_used_at = datetime.now(timezone.utc)

    return item_tag


async def detach_tag(db: AsyncSession, user_item_id: UUID, tag_id: UUID) -> None:
    await db.execute(
        delete(ItemTag).where(
            ItemTag.user_item_id == user_item_id, ItemTag.tag_id == tag_id
        )
    )
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    if tag and tag.item_count > 0:
        tag.item_count -= 1
    await db.flush()
