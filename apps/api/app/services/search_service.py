from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.content_object import ContentObject
from app.models.item_tag import ItemTag
from app.models.tag import Tag
from app.models.user_item import UserItem, UserItemStatus
from app.schemas.item import ItemRead
from app.services import ai_service

_ACTIVE_FILTERS = (
    UserItem.deleted_at.is_(None),
    UserItem.status != UserItemStatus.archived,
)


def _to_item_read(ui: UserItem) -> ItemRead:
    return ItemRead(
        id=ui.id,
        content_id=ui.content.id,
        url=ui.content.url,
        title=ui.content.title,
        summary=ui.content.summary,
        thumbnail_url=ui.content.thumbnail_url,
        saved_at=ui.saved_at,
        deleted_at=ui.deleted_at,
    )


async def text_search(db: AsyncSession, user_id: UUID, query: str) -> list[ItemRead]:
    hits = await _text_search_raw(db, user_id, query)
    return [_to_item_read(ui) for ui in hits]


async def _text_search_raw(db: AsyncSession, user_id: UUID, query: str) -> list[UserItem]:
    pattern = f"%{query}%"
    result = await db.execute(
        select(UserItem)
        .options(selectinload(UserItem.content))
        .join(UserItem.content)
        .where(
            UserItem.user_id == user_id,
            *_ACTIVE_FILTERS,
            or_(
                ContentObject.title.ilike(pattern),
                ContentObject.summary.ilike(pattern),
                UserItem.item_tags.any(
                    ItemTag.tag.has(Tag.name.ilike(pattern))
                ),
            ),
        )
        .limit(20)
    )
    return list(result.scalars().all())


async def semantic_search(db: AsyncSession, user_id: UUID, query: str) -> list[ItemRead]:
    query_embedding = await ai_service.embed(query)
    result = await db.execute(
        select(UserItem)
        .options(selectinload(UserItem.content))
        .join(UserItem.content)
        .where(
            UserItem.user_id == user_id,
            *_ACTIVE_FILTERS,
            ContentObject.embedding.is_not(None),
        )
        .order_by(ContentObject.embedding.cosine_distance(query_embedding))
        .limit(20)
    )
    return [_to_item_read(ui) for ui in result.scalars().all()]
