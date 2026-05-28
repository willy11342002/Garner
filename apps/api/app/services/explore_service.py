import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import collections as crud_collections
from app.crud import items as crud_items
from app.schemas.explore import ExploreStats


async def get_stats(db: AsyncSession, user_id: UUID) -> ExploreStats:
    total_items, public_collections, weekly_new = await asyncio.gather(
        crud_items.count_all(db, user_id),
        crud_collections.count_public(db, user_id),
        crud_items.count_weekly_new(db, user_id),
    )
    return ExploreStats(
        total_items=total_items,
        public_collections=public_collections,
        weekly_new=weekly_new,
    )
