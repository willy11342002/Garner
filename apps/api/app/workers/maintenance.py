"""
定期維護任務：重算 tag.item_count、清理孤兒 tag、清理解析失敗 item。
可由排程自動呼叫，也可透過 admin API 手動觸發。
"""

import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.item_tag import ItemTag
from app.models.tag import Tag
from app.models.user_item import UserItem

logger = logging.getLogger(__name__)


async def recalculate_tag_counts(db: AsyncSession) -> int:
    """用 JOIN 重算所有 tag 的 item_count，回傳更新筆數。"""
    real_counts = (
        select(
            ItemTag.tag_id,
            func.count(ItemTag.user_item_id).label("cnt"),
        )
        .join(UserItem, UserItem.id == ItemTag.user_item_id)
        .where(UserItem.deleted_at.is_(None))
        .group_by(ItemTag.tag_id)
        .subquery()
    )

    result = await db.execute(
        update(Tag)
        .where(Tag.id == real_counts.c.tag_id)
        .values(item_count=real_counts.c.cnt)
        .execution_options(synchronize_session=False)
    )
    updated = result.rowcount

    # tag 沒有任何 active confirmed item → count 設為 0
    has_any = select(real_counts.c.tag_id)
    await db.execute(
        update(Tag)
        .where(Tag.id.not_in(has_any))
        .values(item_count=0)
        .execution_options(synchronize_session=False)
    )

    return updated


async def delete_orphan_tags(db: AsyncSession) -> int:
    """刪除沒有任何 active item 的孤兒 tag（先清 item_tags）。"""
    has_active_item = (
        select(ItemTag.tag_id)
        .join(UserItem, UserItem.id == ItemTag.user_item_id)
        .where(UserItem.deleted_at.is_(None))
        .distinct()
    )
    orphan_tag_ids = select(Tag.id).where(Tag.id.not_in(has_active_item))

    # 先刪 item_tags，解除 FK
    await db.execute(
        delete(ItemTag)
        .where(ItemTag.tag_id.in_(orphan_tag_ids))
        .execution_options(synchronize_session=False)
    )

    # 再刪 tags
    result = await db.execute(
        delete(Tag)
        .where(Tag.id.in_(orphan_tag_ids))
        .execution_options(synchronize_session=False)
    )
    return result.rowcount


async def soft_delete_unparsed_items(db: AsyncSession, older_than_hours: int = 24) -> int:
    """將儲存超過指定時間且 title 仍為 null 的 item 標記為軟刪除。"""
    from app.models.user_item import UserItemStatus

    cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
    result = await db.execute(
        update(UserItem)
        .where(
            UserItem.title.is_(None),
            UserItem.deleted_at.is_(None),
            UserItem.saved_at < cutoff,
        )
        .values(
            deleted_at=datetime.now(timezone.utc),
            status=UserItemStatus.deleted,
        )
        .execution_options(synchronize_session=False)
    )
    return result.rowcount


async def run_maintenance() -> dict:
    """完整執行一次維護：清理解析失敗 item → 重算 count → 清理孤兒。"""
    async with AsyncSessionLocal() as db:
        async with db.begin():
            unparsed_deleted = await soft_delete_unparsed_items(db)
            updated = await recalculate_tag_counts(db)
            deleted = await delete_orphan_tags(db)

    logger.info(
        "maintenance done: unparsed_deleted=%d recalculated=%d orphans_deleted=%d",
        unparsed_deleted, updated, deleted,
    )
    return {"recalculated": updated, "orphans_deleted": deleted, "unparsed_deleted": unparsed_deleted}
