from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer, selectinload

from app.models.item_tag import ItemTag
from app.models.tag import Tag
from app.models.user_item import UserItem, UserItemStatus


async def get_all(db: AsyncSession, user_id: UUID) -> list[UserItem]:
    result = await db.execute(
        select(UserItem)
        .where(
            UserItem.user_id == user_id,
            UserItem.deleted_at.is_(None),
            UserItem.status == UserItemStatus.active,
        )
        .options(
            defer(UserItem.notes_md),
            defer(UserItem.embedding),
            selectinload(UserItem.item_tags).joinedload(ItemTag.tag),
        )
        .order_by(UserItem.saved_at.desc())
    )
    return list(result.scalars().unique().all())


async def get_archived(db: AsyncSession, user_id: UUID) -> list[UserItem]:
    result = await db.execute(
        select(UserItem)
        .where(
            UserItem.user_id == user_id,
            UserItem.deleted_at.is_(None),
            UserItem.status == UserItemStatus.archived,
        )
        .order_by(UserItem.saved_at.desc())
    )
    return list(result.scalars().all())


async def get_one(db: AsyncSession, user_id: UUID, item_id: UUID) -> UserItem | None:
    result = await db.execute(
        select(UserItem)
        .where(
            UserItem.id == item_id,
            UserItem.user_id == user_id,
            UserItem.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def get_by_ids(db: AsyncSession, user_id: UUID, item_ids: list[UUID]) -> list[UserItem]:
    """批次取得指定 item_ids，保留原始順序，忽略不屬於該 user 或已刪除的。"""
    if not item_ids:
        return []
    result = await db.execute(
        select(UserItem)
        .where(
            UserItem.id.in_(item_ids),
            UserItem.user_id == user_id,
            UserItem.deleted_at.is_(None),
        )
    )
    items = {ui.id: ui for ui in result.scalars().all()}
    return [items[iid] for iid in item_ids if iid in items]


async def get_by_url(
    db: AsyncSession, user_id: UUID, url: str, include_deleted: bool = False
) -> UserItem | None:
    filters = [UserItem.user_id == user_id, UserItem.url == url]
    if not include_deleted:
        filters.append(UserItem.deleted_at.is_(None))
    result = await db.execute(select(UserItem).where(*filters))
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    user_id: UUID,
    url: str,
    source_type: str,
    title: str | None = None,
) -> UserItem:
    user_item = UserItem(user_id=user_id, url=url, source_type=source_type, title=title)
    db.add(user_item)
    await db.flush()
    await db.refresh(user_item)
    return user_item


async def soft_delete(db: AsyncSession, user_item: UserItem) -> UserItem:
    user_item.deleted_at = datetime.now(timezone.utc)
    user_item.status = UserItemStatus.deleted
    await db.flush()
    return user_item


async def get_page(
    db: AsyncSession,
    user_id: UUID,
    *,
    tag_ids: list[UUID] | None = None,
    tag_logic: str = "and",
    saved_after: datetime | None = None,
    sort: str = "saved_desc",
    offset: int = 0,
    limit: int = 25,
) -> tuple[list[UserItem], int]:
    base_filters = [
        UserItem.user_id == user_id,
        UserItem.deleted_at.is_(None),
        UserItem.status == UserItemStatus.active,
    ]
    if saved_after:
        base_filters.append(UserItem.saved_at >= saved_after)

    if sort == "random":
        order_col = func.random()
    elif sort == "saved_asc":
        order_col = UserItem.saved_at.asc()
    else:
        order_col = UserItem.saved_at.desc()

    if tag_ids:
        if tag_logic == "and":
            ids_subq = (
                select(UserItem.id)
                .join(ItemTag, ItemTag.user_item_id == UserItem.id)
                .where(*base_filters, ItemTag.tag_id.in_(tag_ids))
                .group_by(UserItem.id)
                .having(func.count(func.distinct(ItemTag.tag_id)) == len(tag_ids))
                .subquery()
            )
        else:
            ids_subq = (
                select(UserItem.id)
                .join(ItemTag, ItemTag.user_item_id == UserItem.id)
                .where(*base_filters, ItemTag.tag_id.in_(tag_ids))
                .distinct()
                .subquery()
            )

        total_result = await db.execute(select(func.count()).select_from(ids_subq))
        total = total_result.scalar_one()

        ids_result = await db.execute(
            select(UserItem.id)
            .where(UserItem.id.in_(select(ids_subq.c.id)))
            .order_by(order_col)
            .offset(offset)
            .limit(limit)
        )
    else:
        base_q = select(UserItem.id).where(*base_filters)
        total_result = await db.execute(select(func.count()).select_from(base_q.subquery()))
        total = total_result.scalar_one()

        ids_result = await db.execute(
            base_q.order_by(order_col).offset(offset).limit(limit)
        )

    ids = [row[0] for row in ids_result.all()]
    if not ids:
        return [], total

    result = await db.execute(
        select(UserItem)
        .where(UserItem.id.in_(ids))
        .options(
            defer(UserItem.notes_md),
            defer(UserItem.embedding),
            selectinload(UserItem.item_tags).joinedload(ItemTag.tag),
        )
    )
    items_by_id = {ui.id: ui for ui in result.scalars().unique().all()}
    return [items_by_id[id_] for id_ in ids if id_ in items_by_id], total


async def count_all(db: AsyncSession, user_id: UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(UserItem)
        .where(
            UserItem.user_id == user_id,
            UserItem.deleted_at.is_(None),
            UserItem.status.in_([UserItemStatus.active, UserItemStatus.archived]),
        )
    )
    return result.scalar_one()


async def count_weekly_new(db: AsyncSession, user_id: UUID) -> int:
    week_start = datetime.now(timezone.utc) - timedelta(days=7)
    result = await db.execute(
        select(func.count())
        .select_from(UserItem)
        .where(
            UserItem.user_id == user_id,
            UserItem.deleted_at.is_(None),
            UserItem.saved_at >= week_start,
        )
    )
    return result.scalar_one()


_NON_DELETED = (UserItem.deleted_at.is_(None),)


async def semantic_search(
    db: AsyncSession,
    user_id: UUID,
    embedding: list[float],
    limit: int = 8,
    saved_before: datetime | None = None,
    saved_after: datetime | None = None,
    exclude_ids: list[UUID] | None = None,
    cutoff: float = 0.45,
) -> list[tuple[UserItem, float]]:
    """向量搜尋，回傳 (UserItem, cosine_distance) 清單。"""
    filters = [
        UserItem.user_id == user_id,
        *_NON_DELETED,
        UserItem.embedding.is_not(None),
    ]
    if saved_before:
        filters.append(UserItem.saved_at < saved_before)
    if saved_after:
        filters.append(UserItem.saved_at >= saved_after)
    if exclude_ids:
        filters.append(UserItem.id.not_in(exclude_ids))

    distance_col = UserItem.embedding.cosine_distance(embedding).label("distance")
    result = await db.execute(
        select(UserItem, distance_col)
        .where(*filters, distance_col <= cutoff)
        .order_by(distance_col)
        .limit(limit)
    )
    return [(row.UserItem, row.distance) for row in result.all()]


async def get_forgotten(db: AsyncSession, user_id: UUID, limit: int = 3) -> list[UserItem]:
    """回傳 90 天以上未開啟、且有 embedding 的 items（供 Surprise 洞察使用）。"""
    threshold = datetime.now(timezone.utc) - timedelta(days=90)
    result = await db.execute(
        select(UserItem)
        .where(
            UserItem.user_id == user_id,
            *_NON_DELETED,
            UserItem.embedding.is_not(None),
            (UserItem.last_opened_at.is_(None)) | (UserItem.last_opened_at < threshold),
            UserItem.saved_at < threshold,
        )
        .order_by(UserItem.saved_at.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_recent_with_embedding(
    db: AsyncSession, user_id: UUID, limit: int = 3
) -> list[UserItem]:
    """回傳最近 14 天存入、有 embedding 的 items。"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    result = await db.execute(
        select(UserItem)
        .where(
            UserItem.user_id == user_id,
            *_NON_DELETED,
            UserItem.embedding.is_not(None),
            UserItem.saved_at >= cutoff,
        )
        .order_by(UserItem.saved_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_random_with_embedding(
    db: AsyncSession, user_id: UUID, limit: int = 3
) -> list[UserItem]:
    """從所有有 embedding 的 items 中隨機取樣（DB 層 ORDER BY RANDOM()）。"""
    result = await db.execute(
        select(UserItem)
        .where(
            UserItem.user_id == user_id,
            *_NON_DELETED,
            UserItem.embedding.is_not(None),
        )
        .order_by(func.random())
        .limit(limit)
    )
    return list(result.scalars().all())


async def structured_filter(
    db: AsyncSession,
    user_id: UUID,
    tags: list[str] | None = None,
    source_type: str | None = None,
    saved_after: datetime | None = None,
    saved_before: datetime | None = None,
    locations: list[str] | None = None,
    item_ids: list[UUID] | None = None,
    limit: int = 8,
) -> list[UserItem]:
    """結構化篩選：tag / source_type / 日期範圍 / location / item_ids，可自由組合。"""
    from app.models.content_location import ContentLocation

    filters = [
        UserItem.user_id == user_id,
        *_NON_DELETED,
    ]
    if saved_after:
        filters.append(UserItem.saved_at >= saved_after)
    if saved_before:
        filters.append(UserItem.saved_at < saved_before)
    if source_type:
        filters.append(UserItem.source_type == source_type)
    if item_ids:
        filters.append(UserItem.id.in_(item_ids))

    q = select(UserItem).where(*filters)

    if tags:
        q = (
            q.join(ItemTag, ItemTag.user_item_id == UserItem.id)
            .join(Tag, Tag.id == ItemTag.tag_id)
            .where(Tag.name.in_(tags))
            .distinct()
        )

    if locations:
        loc_subq = (
            select(ContentLocation.user_item_id)
            .where(ContentLocation.name.in_(locations))
            .distinct()
            .subquery()
        )
        q = q.where(UserItem.id.in_(select(loc_subq.c.user_item_id)))

    q = q.order_by(UserItem.saved_at.desc()).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().unique().all())


async def get_tag_trends(
    db: AsyncSession, user_id: UUID
) -> list[tuple[str, int, int]]:
    """回傳 (tag_name, count_last30d, count_prev30d)，按 count_last30d desc。"""
    now = datetime.now(timezone.utc)
    last30_start = now - timedelta(days=30)
    prev30_start = now - timedelta(days=60)

    last30_q = (
        select(Tag.name, func.count().label("cnt"))
        .select_from(UserItem)
        .join(ItemTag, ItemTag.user_item_id == UserItem.id)
        .join(Tag, Tag.id == ItemTag.tag_id)
        .where(
            UserItem.user_id == user_id,
            *_NON_DELETED,
            UserItem.saved_at >= last30_start,
        )
        .group_by(Tag.name)
        .order_by(func.count().desc())
        .limit(5)
    )
    last30_rows = (await db.execute(last30_q)).all()
    if not last30_rows:
        return []

    tag_names = [r.name for r in last30_rows]
    prev30_q = (
        select(Tag.name, func.count().label("cnt"))
        .select_from(UserItem)
        .join(ItemTag, ItemTag.user_item_id == UserItem.id)
        .join(Tag, Tag.id == ItemTag.tag_id)
        .where(
            UserItem.user_id == user_id,
            *_NON_DELETED,
            UserItem.saved_at >= prev30_start,
            UserItem.saved_at < last30_start,
            Tag.name.in_(tag_names),
        )
        .group_by(Tag.name)
    )
    prev30_map = {r.name: r.cnt for r in (await db.execute(prev30_q)).all()}

    total = sum(r.cnt for r in last30_rows) or 1
    return [
        (r.name, r.cnt, prev30_map.get(r.name, 0))
        for r in last30_rows
        if r.cnt * 100 // total >= 5
    ]
