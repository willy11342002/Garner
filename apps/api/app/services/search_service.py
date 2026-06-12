from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.item_tag import ItemTag
from app.models.tag import Tag
from app.models.user_item import UserItem, UserItemStatus
from app.schemas.item import ItemRead, PaginatedResult
from app.services import ai_service

_ACTIVE_FILTERS = (
    UserItem.deleted_at.is_(None),
    UserItem.status != UserItemStatus.archived,
)


def _to_item_read(ui: UserItem) -> ItemRead:
    return ItemRead(
        id=ui.id,
        url=ui.url,
        title=ui.title,
        notes_md=None,
        thumbnail_url=ui.thumbnail_url,
        saved_at=ui.saved_at,
        deleted_at=ui.deleted_at,
        source_type=ui.source_type,
        parsed_at=ui.parsed_at,
        status=ui.status,
    )


async def text_search(db: AsyncSession, user_id: UUID, query: str) -> list[ItemRead]:
    hits = await _text_search_raw(db, user_id, query)
    return [_to_item_read(ui) for ui in hits]


async def _text_search_raw(db: AsyncSession, user_id: UUID, query: str) -> list[UserItem]:
    pattern = f"%{query}%"
    result = await db.execute(
        select(UserItem)
        .where(
            UserItem.user_id == user_id,
            *_ACTIVE_FILTERS,
            or_(
                UserItem.title.ilike(pattern),
                UserItem.notes_md.ilike(pattern),
                UserItem.item_tags.any(
                    ItemTag.tag.has(Tag.name.ilike(pattern))
                ),
            ),
        )
        .limit(20)
    )
    return list(result.scalars().all())


_SEMANTIC_PAGE_SIZE = 10


async def semantic_search(
    db: AsyncSession, user_id: UUID, query: str, page: int = 1
) -> PaginatedResult[ItemRead]:
    query_embedding = await ai_service.embed(query)
    offset = (page - 1) * _SEMANTIC_PAGE_SIZE
    result = await db.execute(
        select(UserItem)
        .where(
            UserItem.user_id == user_id,
            *_ACTIVE_FILTERS,
            UserItem.embedding.is_not(None),
        )
        .order_by(UserItem.embedding.cosine_distance(query_embedding))
        .offset(offset)
        .limit(_SEMANTIC_PAGE_SIZE + 1)
    )
    rows = result.scalars().all()
    has_next = len(rows) > _SEMANTIC_PAGE_SIZE
    items = [_to_item_read(ui) for ui in rows[:_SEMANTIC_PAGE_SIZE]]
    return PaginatedResult(items=items, page=page, page_size=_SEMANTIC_PAGE_SIZE, has_next=has_next)
