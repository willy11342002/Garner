from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_object import ContentObject
from app.models.user_item import UserItem
from app.schemas.item import ItemRead
from app.services import ai_service


async def semantic_search(db: AsyncSession, user_id: UUID, query: str) -> list[ItemRead]:
    query_embedding = await ai_service.embed(query)

    result = await db.execute(
        select(UserItem)
        .join(UserItem.content)
        .where(
            UserItem.user_id == user_id,
            UserItem.deleted_at.is_(None),
            ContentObject.embedding.is_not(None),
        )
        .order_by(ContentObject.embedding.cosine_distance(query_embedding))
        .limit(20)
    )
    user_items = list(result.scalars().all())

    return [
        ItemRead(
            id=ui.id,
            url=ui.content.url,
            title=ui.content.title,
            summary=ui.content.summary,
            thumbnail_url=ui.content.thumbnail_url,
            saved_at=ui.saved_at,
            deleted_at=ui.deleted_at,
        )
        for ui in user_items
    ]
