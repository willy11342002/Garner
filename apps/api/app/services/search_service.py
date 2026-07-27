import asyncio
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud import items as crud_items
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


async def _get_cutoff(db: AsyncSession) -> float:
    from sqlalchemy import select as sa_select
    from app.models.app_setting import AppSetting
    result = await db.execute(
        sa_select(AppSetting.value).where(AppSetting.key == "chain_distance_cutoff")
    )
    val = result.scalar_one_or_none()
    try:
        return float(val) if val is not None else 0.45
    except (TypeError, ValueError):
        return 0.45


async def _merge_semantic(
    db: AsyncSession,
    user_id: UUID,
    query_embedding: list[float],
    fetch_limit: int,
    cutoff: float,
) -> dict[UUID, tuple[UserItem, float]]:
    """並搜 chunk + 整篇，回傳 {item_id: (UserItem, best_distance)}。"""
    from app.crud import chunks as crud_chunks

    distance_col = UserItem.embedding.cosine_distance(query_embedding).label("distance")

    chunk_coro = crud_chunks.semantic_search(
        db, user_id, query_embedding, limit=fetch_limit, cutoff=cutoff
    )
    article_coro = db.execute(
        select(UserItem, distance_col)
        .where(
            UserItem.user_id == user_id,
            *_ACTIVE_FILTERS,
            UserItem.embedding.is_not(None),
            distance_col <= cutoff,
        )
        .order_by(distance_col)
        .limit(fetch_limit)
    )
    chunk_hits, article_result = await asyncio.gather(chunk_coro, article_coro)

    merged: dict[UUID, tuple[UserItem, float]] = {}

    for row in article_result.all():
        ui, dist = row.UserItem, row.distance
        merged[ui.id] = (ui, dist)

    # chunk 命中：若比整篇更近則更新
    chunk_item_ids = list({c.user_item_id for c, _ in chunk_hits})
    if chunk_item_ids:
        from app.crud.items import get_by_ids
        chunk_items = {ui.id: ui for ui in await get_by_ids(db, user_id, chunk_item_ids)}
        for chunk, dist in chunk_hits:
            iid = chunk.user_item_id
            if iid not in merged or dist < merged[iid][1]:
                ui = chunk_items.get(iid)
                if ui:
                    merged[iid] = (ui, dist)

    return merged


_RRF_K = 60
_CANDIDATE_LIMIT = 30  # 向量、BM25 各取 _CANDIDATE_LIMIT，RRF 融合後維持同樣大小的候選池


def _rrf_fuse(*ranked_id_lists: list[UUID]) -> dict[UUID, float]:
    """Reciprocal Rank Fusion：每個排名清單裡 rank 從 1 起算，分數為 1/(k+rank) 加總。"""
    scores: dict[UUID, float] = {}
    for ranked_ids in ranked_id_lists:
        for rank, item_id in enumerate(ranked_ids, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (_RRF_K + rank)
    return scores


async def semantic_search(
    db: AsyncSession, user_id: UUID, query: str, page: int = 1
) -> PaginatedResult[ItemRead]:
    """Hybrid 檢索：向量語意 + BM25-like 全文檢索用 RRF 融合候選集，再用 cross-encoder 精排。"""
    query_embedding, segmented_query = await asyncio.gather(
        ai_service.embed(query), ai_service.segment(query),
    )
    cutoff = await _get_cutoff(db)

    vector_merged, bm25_hits = await asyncio.gather(
        _merge_semantic(db, user_id, query_embedding, _CANDIDATE_LIMIT, cutoff),
        crud_items.bm25_search(db, user_id, segmented_query, limit=_CANDIDATE_LIMIT),
    )

    vector_ranked_ids = [ui.id for ui, _ in sorted(vector_merged.values(), key=lambda t: t[1])]
    bm25_ranked_ids = [ui.id for ui, _ in bm25_hits]
    fused_scores = _rrf_fuse(vector_ranked_ids, bm25_ranked_ids)

    all_items = {ui.id: ui for ui, _ in vector_merged.values()}
    all_items.update({ui.id: ui for ui, _ in bm25_hits})
    fused_order = sorted(fused_scores.items(), key=lambda kv: -kv[1])[:_CANDIDATE_LIMIT]
    candidates = [all_items[iid] for iid, _ in fused_order]

    passages = [
        {"id": str(ui.id), "text": f"{ui.title or ''}\n{ui.notes_md or ''}"[:2000]}
        for ui in candidates
    ]
    reranked = await ai_service.rerank(query, passages) if passages else []
    order = [UUID(r["id"]) for r in reranked] if reranked else [ui.id for ui in candidates]

    offset = (page - 1) * _SEMANTIC_PAGE_SIZE
    page_ids = order[offset: offset + _SEMANTIC_PAGE_SIZE + 1]
    has_next = len(page_ids) > _SEMANTIC_PAGE_SIZE
    items = [_to_item_read(all_items[iid]) for iid in page_ids[:_SEMANTIC_PAGE_SIZE]]
    return PaginatedResult(items=items, page=page, page_size=_SEMANTIC_PAGE_SIZE, has_next=has_next)
