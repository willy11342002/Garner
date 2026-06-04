from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.item_tag import ItemTag, TagSource
from app.models.tag import Tag


async def get_all(db: AsyncSession, user_id: UUID) -> list[Tag]:
    result = await db.execute(
        select(Tag).where(Tag.user_id == user_id).order_by(Tag.item_count.desc(), Tag.name)
    )
    return list(result.scalars().all())


async def get_one(db: AsyncSession, user_id: UUID, tag_id: UUID) -> Tag | None:
    result = await db.execute(
        select(Tag).where(Tag.id == tag_id, Tag.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_top_tags(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 50,
) -> list[Tag]:
    """取用戶使用頻率最高的 tag，作為 LLM 正規化的候選清單。"""
    result = await db.execute(
        select(Tag)
        .where(Tag.user_id == user_id)
        .order_by(Tag.item_count.desc(), Tag.last_used_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_or_create(
    db: AsyncSession,
    user_id: UUID,
    name: str,
    name_i18n: dict[str, str] | None = None,
) -> Tag:
    result = await db.execute(
        select(Tag).where(Tag.user_id == user_id, Tag.name == name)
    )
    tag = result.scalar_one_or_none()
    if tag is None:
        tag = Tag(user_id=user_id, name=name, name_i18n=name_i18n)
        db.add(tag)
        await db.flush()
    elif name_i18n and tag.name_i18n is None:
        tag.name_i18n = name_i18n
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
    db: AsyncSession,
    user_item_id: UUID,
    tag_id: UUID,
    source: TagSource = TagSource.user,
    confirmed: bool | None = None,
) -> ItemTag:
    result = await db.execute(
        select(ItemTag).where(
            ItemTag.user_item_id == user_item_id, ItemTag.tag_id == tag_id
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    if confirmed is None:
        confirmed = source == TagSource.user
    item_tag = ItemTag(user_item_id=user_item_id, tag_id=tag_id, source=source, confirmed=confirmed)
    db.add(item_tag)
    await db.flush()

    if confirmed:
        result = await db.execute(select(Tag).where(Tag.id == tag_id))
        tag = result.scalar_one_or_none()
        if tag:
            tag.item_count += 1
            tag.last_used_at = datetime.now(timezone.utc)

    return item_tag


async def detach_tag(db: AsyncSession, user_item_id: UUID, tag_id: UUID) -> None:
    result = await db.execute(
        select(ItemTag).where(
            ItemTag.user_item_id == user_item_id, ItemTag.tag_id == tag_id
        )
    )
    item_tag = result.scalar_one_or_none()

    await db.execute(
        delete(ItemTag).where(
            ItemTag.user_item_id == user_item_id, ItemTag.tag_id == tag_id
        )
    )

    if item_tag and item_tag.confirmed:
        result = await db.execute(select(Tag).where(Tag.id == tag_id))
        tag = result.scalar_one_or_none()
        if tag and tag.item_count > 0:
            tag.item_count -= 1
    await db.flush()


async def get_items_with_pending_tags(
    db: AsyncSession, user_id: UUID
) -> list[tuple["UserItem", list[Tag]]]:  # type: ignore[name-defined]
    from app.models.user_item import UserItem

    result = await db.execute(
        select(UserItem)
        .join(ItemTag, ItemTag.user_item_id == UserItem.id)
        .where(
            UserItem.user_id == user_id,
            ItemTag.confirmed == False,  # noqa: E712
        )
        .options(joinedload(UserItem.content))
        .distinct()
        .order_by(UserItem.saved_at.desc())
    )
    user_items = result.unique().scalars().all()

    rows = []
    for ui in user_items:
        tag_result = await db.execute(
            select(Tag)
            .join(ItemTag, ItemTag.tag_id == Tag.id)
            .where(
                ItemTag.user_item_id == ui.id,
                ItemTag.confirmed == False,  # noqa: E712
            )
        )
        rows.append((ui, list(tag_result.scalars().all())))
    return rows


async def get_items_by_tag(
    db: AsyncSession, user_id: UUID, tag_id: UUID
) -> list["UserItem"]:  # type: ignore[name-defined]
    from app.models.user_item import UserItem

    result = await db.execute(
        select(UserItem)
        .join(ItemTag, ItemTag.user_item_id == UserItem.id)
        .where(
            UserItem.user_id == user_id,
            ItemTag.tag_id == tag_id,
            ItemTag.confirmed == True,  # noqa: E712
            UserItem.deleted_at.is_(None),
        )
        .options(joinedload(UserItem.content))
        .order_by(UserItem.saved_at.desc())
    )
    return list(result.unique().scalars().all())


async def confirm_item_tag(
    db: AsyncSession, user_item_id: UUID, tag_id: UUID
) -> bool:
    result = await db.execute(
        select(ItemTag).where(
            ItemTag.user_item_id == user_item_id,
            ItemTag.tag_id == tag_id,
            ItemTag.confirmed == False,  # noqa: E712
        )
    )
    item_tag = result.scalar_one_or_none()
    if item_tag is None:
        return False

    item_tag.confirmed = True

    tag_result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = tag_result.scalar_one_or_none()
    if tag:
        tag.item_count += 1
        tag.last_used_at = datetime.now(timezone.utc)

    await db.flush()
    return True


async def confirm_item_tags_bulk(
    db: AsyncSession, user_item_id: UUID, tag_ids: list[UUID]
) -> int:
    result = await db.execute(
        select(ItemTag).where(
            ItemTag.user_item_id == user_item_id,
            ItemTag.tag_id.in_(tag_ids),
            ItemTag.confirmed == False,  # noqa: E712
        )
    )
    item_tags = result.scalars().all()
    confirmed_tag_ids = [it.tag_id for it in item_tags]
    for item_tag in item_tags:
        item_tag.confirmed = True

    if confirmed_tag_ids:
        tags_result = await db.execute(
            select(Tag).where(Tag.id.in_(confirmed_tag_ids))
        )
        for tag in tags_result.scalars().all():
            tag.item_count += 1
            tag.last_used_at = datetime.now(timezone.utc)

    await db.flush()
    return len(item_tags)
