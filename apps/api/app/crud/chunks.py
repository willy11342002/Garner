from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_chunk import ContentChunk


async def replace_chunks(
    db: AsyncSession,
    user_item_id: UUID,
    chunks: list[dict],  # [{"text": str, "embedding": list[float]}]
) -> None:
    """刪除舊 chunks 並批量插入新 chunks。"""
    await db.execute(delete(ContentChunk).where(ContentChunk.user_item_id == user_item_id))
    for i, chunk in enumerate(chunks):
        db.add(ContentChunk(
            user_item_id=user_item_id,
            chunk_index=i,
            text=chunk["text"],
            embedding=chunk["embedding"],
        ))
    await db.flush()


async def semantic_search(
    db: AsyncSession,
    user_id: UUID,
    embedding: list[float],
    limit: int = 6,
    cutoff: float = 0.45,
) -> list[tuple[ContentChunk, float]]:
    """在 content_chunks 做向量搜尋，回傳 (ContentChunk, distance)。
    只搜尋屬於該 user 未刪除 items 的 chunks。
    """
    from app.models.user_item import UserItem, UserItemStatus

    distance_col = ContentChunk.embedding.cosine_distance(embedding).label("distance")

    result = await db.execute(
        select(ContentChunk, distance_col)
        .join(UserItem, UserItem.id == ContentChunk.user_item_id)
        .where(
            UserItem.user_id == user_id,
            UserItem.deleted_at.is_(None),
            UserItem.status != UserItemStatus.archived,
            ContentChunk.embedding.is_not(None),
            distance_col <= cutoff,
        )
        .order_by(distance_col)
        .limit(limit)
    )
    return [(row.ContentChunk, row.distance) for row in result.all()]
