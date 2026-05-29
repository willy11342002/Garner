import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import collections as crud_collections
from app.crud import items as crud_items
from app.schemas.explore import ExploreStats, PublicCollectionRead


async def browse_public_collections(
    db: AsyncSession,
    q: str | None = None,
    tag: str | None = None,
    offset: int = 0,
    limit: int = 24,
) -> list[PublicCollectionRead]:
    rows = await crud_collections.list_public(db, q=q, tag=tag, offset=offset, limit=limit)
    results = []
    for collection, item_count in rows:
        thumbnails = [
            ci.content.thumbnail_url
            for ci in sorted(collection.collection_items, key=lambda x: x.sort_order)[:3]
        ]
        results.append(
            PublicCollectionRead(
                id=collection.id,
                title=collection.title,
                slug=collection.slug,
                fork_count=collection.fork_count,
                created_at=collection.created_at,
                item_count=item_count,
                author_username=collection.user.username,
                author_avatar_url=collection.user.avatar_url,
                source_tag_name=collection.source_tag.name if collection.source_tag else None,
                cover_thumbnails=thumbnails,
            )
        )
    return results


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
