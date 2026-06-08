"""
explore_service：Browse stats + Focus RAG + Surprise AI 洞察。

RAG 核心（rag_retrieve / rag_synthesize）設計為獨立函式，
未來 AI Chat service 可直接 import 複用，不依賴 explore 的 schema。
"""

from datetime import timedelta, timezone
from datetime import datetime as dt
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import chunks as crud_chunks
from app.crud import collections as crud_collections
from app.crud import items as crud_items
from app.models.content_chunk import ContentChunk
from app.models.user_item import UserItem
from app.schemas.explore import (
    ChainFullAnalysis,
    ChainHopAnalysis,
    ChainItem,
    ExploreStats,
    FocusResult,
    FocusSource,
    Insight,
    InsightItem,
    InsightType,
    PublicCollectionRead,
    SurpriseResult,
    TrendBar,
)
from app.services import ai_service


# ---------------------------------------------------------------------------
# Shared RAG primitives（可被 AI Chat service 複用）
# ---------------------------------------------------------------------------


async def rag_retrieve(
    db: AsyncSession,
    user_id: UUID,
    query: str,
    limit: int = 8,
) -> list[tuple[UserItem, float]]:
    """將 query embed 後做 chunk-level 向量搜尋，回傳去重後的 (UserItem, distance) 清單。
    若尚無 chunks（舊資料），fallback 到 content_objects embedding。
    """
    from sqlalchemy.orm import joinedload
    from sqlalchemy import select
    from app.models.content_object import ContentObject

    embedding = await ai_service.embed(query)
    chunk_hits = await crud_chunks.semantic_search(db, user_id, embedding, limit=limit * 2)

    if chunk_hits:
        # 從 chunks 反查 UserItem，去重保留最近距離
        seen: dict[UUID, tuple[UserItem, float]] = {}
        for chunk, dist in chunk_hits:
            result = await db.execute(
                select(UserItem)
                .options(joinedload(UserItem.content))
                .join(UserItem.content)
                .where(
                    UserItem.content_id == chunk.content_id,
                    UserItem.user_id == user_id,
                    UserItem.deleted_at.is_(None),
                )
                .limit(1)
            )
            ui = result.scalar_one_or_none()
            if ui and ui.id not in seen:
                seen[ui.id] = (ui, dist)
            if len(seen) >= limit:
                break
        return list(seen.values())

    # Fallback：沒有 chunks 時用 summary embedding
    return await crud_items.semantic_search(db, user_id, embedding, limit=limit)


async def rag_synthesize(
    query: str,
    hits: list[tuple[UserItem, float]],
) -> str:
    """將搜尋結果傳給 LLM 合成回答。輸入格式與 explore/chat 無關。"""
    items_payload = [
        {"title": ui.title, "summary": (ui.notes_md or "")[:500]}
        for ui, _ in hits
    ]
    return await ai_service.synthesize_focus(query, items_payload)


# ---------------------------------------------------------------------------
# Browse / Stats（原有）
# ---------------------------------------------------------------------------


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
            ci.user_items[0].thumbnail_url if ci.user_items else None
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
    total_items = await crud_items.count_all(db, user_id)
    public_collections = await crud_collections.count_public(db, user_id)
    weekly_new = await crud_items.count_weekly_new(db, user_id)
    return ExploreStats(
        total_items=total_items,
        public_collections=public_collections,
        weekly_new=weekly_new,
    )


# ---------------------------------------------------------------------------
# Focus
# ---------------------------------------------------------------------------


async def focus_query(db: AsyncSession, user_id: UUID, query: str) -> FocusResult:
    hits = await rag_retrieve(db, user_id, query, limit=8)
    if not hits:
        return FocusResult(
            synthesis="你的知識庫目前還沒有足夠的內容可以回答這個問題。存入更多內容後再試試看！",
            sources=[],
        )

    synthesis = await rag_synthesize(query, hits)

    sources = [
        FocusSource(
            id=ui.id,
            url=ui.url or ui.content.url,
            title=ui.title,
            thumbnail_url=ui.thumbnail_url,
            source_type=ui.source_type,
            saved_at=ui.saved_at,
        )
        for ui, _ in hits
    ]
    return FocusResult(synthesis=synthesis, sources=sources)


# ---------------------------------------------------------------------------
# Surprise
# ---------------------------------------------------------------------------


def _item_chip(ui: UserItem) -> InsightItem:
    return InsightItem(
        id=ui.id,
        url=ui.url or ui.content.url,
        title=ui.title,
        thumbnail_url=ui.thumbnail_url,
        source_type=ui.source_type,
    )


def _time_ago(ts: dt) -> str:
    diff = dt.now(timezone.utc) - ts
    days = diff.days
    if days == 0:
        return "剛剛產生"
    if days < 7:
        return f"{days} 天前"
    if days < 30:
        return f"{days // 7} 週前"
    return f"{days // 30} 個月前"


async def _unexpected_connection(
    db: AsyncSession, user_id: UUID
) -> Insight | None:
    """找最近 14 天存入的 items 中，與 30 天前的某個 item 相似度最高的一對。"""
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload
    from app.models.content_object import ContentObject

    now = dt.now(timezone.utc)
    recent_cutoff = now - timedelta(days=14)

    result = await db.execute(
        select(UserItem)
        .options(joinedload(UserItem.content))
        .join(UserItem.content)
        .where(
            UserItem.user_id == user_id,
            UserItem.deleted_at.is_(None),
            ContentObject.embedding.is_not(None),
            UserItem.saved_at >= recent_cutoff,
        )
        .order_by(UserItem.saved_at.desc())
        .limit(5)
    )
    recent_items = list(result.scalars().all())
    if not recent_items:
        return None

    best_pair: tuple[UserItem, UserItem, float] | None = None
    for recent in recent_items:
        old_hits = await crud_items.semantic_search(
            db,
            user_id,
            embedding=recent.content.embedding,
            limit=1,
            saved_before=recent.saved_at - timedelta(days=30),
            exclude_ids=[recent.id],
        )
        if old_hits:
            old_item, dist = old_hits[0]
            if best_pair is None or dist < best_pair[2]:
                best_pair = (recent, old_item, dist)

    if best_pair is None or best_pair[2] > 0.35:
        return None

    recent_item, old_item, _ = best_pair
    return Insight(
        type=InsightType.connection,
        badge="↗ 意外連結",
        title="這兩件事竟然有關聯",
        body=(
            f"你 {_time_ago(old_item.saved_at)}存的「{old_item.title or '(無標題)'}」"
            f"和最近存的「{recent_item.title or '(無標題)'}」"
            f"在語意上高度相似——它們可能在討論同一個核心觀點。"
        ),
        when="剛剛產生",
        items=[_item_chip(old_item), _item_chip(recent_item)],
    )


async def _forgotten_item(db: AsyncSession, user_id: UUID) -> Insight | None:
    forgotten = await crud_items.get_forgotten(db, user_id, limit=1)
    if not forgotten:
        return None
    ui = forgotten[0]
    return Insight(
        type=InsightType.forgotten,
        badge="◌ 遺忘中",
        title="你可能已經忘記這個了",
        body=(
            f"{_time_ago(ui.saved_at)}你存了「{ui.title or '(無標題)'}」，"
            f"但幾乎沒有再打開過。要不要重新複習一次？"
        ),
        when=_time_ago(ui.saved_at),
        items=[_item_chip(ui)],
    )


async def _topic_trend(db: AsyncSession, user_id: UUID) -> Insight | None:
    trends = await crud_items.get_tag_trends(db, user_id)
    if not trends:
        return None

    total = sum(cnt for _, cnt, _ in trends) or 1
    bars = [
        TrendBar(label=name, pct=round(cnt * 100 / total))
        for name, cnt, _ in trends[:4]
    ]

    top_name, top_cnt, top_prev = trends[0]
    growth_text = ""
    if top_prev > 0:
        growth_pct = round((top_cnt - top_prev) / top_prev * 100)
        if growth_pct > 0:
            growth_text = f"其中 **{top_name}** 的關注度比上個月增加了 {growth_pct}%。"

    total_last30 = sum(cnt for _, cnt, _ in trends)
    return Insight(
        type=InsightType.trend,
        badge="◈ 主題趨勢",
        title="本月你最關注的主題",
        body=f"過去 30 天你存了 {total_last30} 筆內容，主要集中在這些主題。{growth_text}",
        when="本月分析",
        trend_bars=bars,
    )


# ---------------------------------------------------------------------------
# Chain exploration
# ---------------------------------------------------------------------------


def _to_chain_item(ui: "UserItem") -> ChainItem:
    return ChainItem(
        id=ui.id,
        url=ui.url or ui.content.url,
        title=ui.title,
        thumbnail_url=ui.thumbnail_url,
        source_type=ui.source_type,
        saved_at=ui.saved_at,
    )


async def _get_public_chain_items(
    db: AsyncSession,
    embedding: list[float] | None,
    limit: int,
    user_id: UUID,
    exclude_content_ids: list[UUID] | None = None,
) -> list[ChainItem]:
    """從所有 ContentObjects 做向量搜尋，排除該用戶 user_items 中已有的，視為公開知識。"""
    from sqlalchemy import select
    from app.models.content_object import ContentObject

    owned_subq = select(UserItem.content_id).where(
        UserItem.user_id == user_id,
        UserItem.content_id.is_not(None),
        UserItem.deleted_at.is_(None),
    ).scalar_subquery()

    filters = [
        ContentObject.embedding.is_not(None),
        ContentObject.id.not_in(owned_subq),
    ]
    if exclude_content_ids:
        filters.append(ContentObject.id.not_in(exclude_content_ids))

    if embedding is not None:
        distance_col = ContentObject.embedding.cosine_distance(embedding).label("distance")
        result = await db.execute(
            select(ContentObject, distance_col)
            .where(*filters, distance_col <= 0.45)
            .order_by(distance_col)
            .limit(limit)
        )
        contents = [row.ContentObject for row in result.all()]
    else:
        result = await db.execute(
            select(ContentObject)
            .where(*filters)
            .order_by(ContentObject.parsed_at.desc())
            .limit(limit)
        )
        contents = list(result.scalars().all())

    return [
        ChainItem(
            id=co.id,
            url=co.url,
            title=co.title,
            thumbnail_url=co.thumbnail_url,
            source_type=co.source_type.value if co.source_type else None,
            saved_at=co.parsed_at or dt.now(timezone.utc),
            is_public=True,
        )
        for co in contents
    ]


async def _get_user_allow_public_chain(db: AsyncSession, user_id: UUID) -> bool:
    from sqlalchemy import select
    from app.models.user import User
    result = await db.execute(select(User.allow_public_chain).where(User.id == user_id))
    val = result.scalar_one_or_none()
    return bool(val)


async def get_chain_start_items(
    db: AsyncSession, user_id: UUID, start_type: str
) -> list[ChainItem]:
    allow_public = await _get_user_allow_public_chain(db, user_id)
    own_limit = 3 if allow_public else 5

    if start_type == "random":
        items = await crud_items.get_random_with_embedding(db, user_id, limit=own_limit)
    elif start_type == "forgotten":
        items = await crud_items.get_forgotten(db, user_id, limit=own_limit)
    else:
        items = await crud_items.get_recent_with_embedding(db, user_id, limit=own_limit)

    result = [_to_chain_item(ui) for ui in items]

    if allow_public:
        needed = 5 - len(result)
        public_items = await _get_public_chain_items(db, None, needed, user_id)
        result.extend(public_items)

    return result


async def _fetch_content_for_chain(
    db: AsyncSession,
    item_id: UUID,
    user_id: UUID,
) -> tuple[str | None, str | None, list[float] | None]:
    """嘗試先以 UserItem.id 查找，再以 ContentObject.id 查找（公開 items）。
    回傳 (title, summary, embedding)。
    """
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload
    from app.models.content_object import ContentObject

    r = await db.execute(
        select(UserItem)
        .options(joinedload(UserItem.content))
        .where(UserItem.id == item_id, UserItem.user_id == user_id)
    )
    ui = r.scalar_one_or_none()
    if ui:
        return ui.title, (ui.notes_md or "")[:500], ui.content.embedding

    r2 = await db.execute(
        select(ContentObject).where(ContentObject.id == item_id)
    )
    co = r2.scalar_one_or_none()
    if co:
        return co.title, None, co.embedding

    return None, None, None


async def _get_chain_cutoff(db: AsyncSession) -> float:
    from sqlalchemy import select
    from app.models.app_setting import AppSetting
    result = await db.execute(select(AppSetting.value).where(AppSetting.key == "chain_distance_cutoff"))
    val = result.scalar_one_or_none()
    try:
        return float(val) if val is not None else 0.45
    except (TypeError, ValueError):
        return 0.45


async def _resolve_content_ids(
    db: AsyncSession, user_id: UUID, item_ids: list[UUID]
) -> list[UUID]:
    """將 UserItem.id 清單轉換為對應的 ContentObject.id 清單（公開 item 直接視為 content_id）。"""
    from sqlalchemy import select
    content_ids: list[UUID] = []
    for iid in item_ids:
        r = await db.execute(
            select(UserItem.content_id)
            .where(UserItem.id == iid, UserItem.user_id == user_id)
        )
        cid = r.scalar_one_or_none()
        content_ids.append(cid if cid is not None else iid)
    return content_ids


async def get_chain_candidates(
    db: AsyncSession,
    user_id: UUID,
    item_id: UUID,
    exclude_ids: list[UUID],
) -> list[ChainItem]:
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload
    from app.models.content_object import ContentObject

    # 先嘗試當作 UserItem.id 查
    result = await db.execute(
        select(UserItem)
        .options(joinedload(UserItem.content))
        .join(UserItem.content)
        .where(UserItem.id == item_id, UserItem.user_id == user_id)
    )
    current = result.scalar_one_or_none()

    if current:
        embedding = current.content.embedding
        current_content_id = current.content_id
    else:
        # 可能是公開 item（ContentObject.id）
        r2 = await db.execute(select(ContentObject).where(ContentObject.id == item_id))
        co = r2.scalar_one_or_none()
        embedding = co.embedding if co else None
        current_content_id = item_id

    allow_public = await _get_user_allow_public_chain(db, user_id)
    own_limit = 3 if allow_public else 5

    own_hits = await crud_items.get_random_with_embedding(
        db, user_id, limit=own_limit + len(exclude_ids) + 1
    )
    exclude_id_set = {item_id, *exclude_ids}
    own_candidates = [
        _to_chain_item(ui) for ui in own_hits
        if ui.id not in exclude_id_set
    ][:own_limit]

    candidates = own_candidates

    if allow_public:
        needed = 5 - len(candidates)
        chain_content_ids = await _resolve_content_ids(db, user_id, [item_id, *exclude_ids])
        exclude_content_ids = list({cid for cid in chain_content_ids if cid is not None})
        public_items = await _get_public_chain_items(db, None, needed, user_id, exclude_content_ids)
        candidates.extend(public_items)

    return candidates


async def analyze_hop(
    db: AsyncSession,
    user_id: UUID,
    from_item_id: UUID,
    to_item_id: UUID,
) -> ChainHopAnalysis:
    title_a, summary_a, _ = await _fetch_content_for_chain(db, from_item_id, user_id)
    title_b, summary_b, _ = await _fetch_content_for_chain(db, to_item_id, user_id)

    raw = await ai_service.analyze_chain_hop(
        title_a=title_a,
        summary_a=summary_a,
        title_b=title_b,
        summary_b=summary_b,
    )
    return ChainHopAnalysis(
        connection=raw.get("connection", ""),
        ideation=raw.get("ideation", ""),
        question=raw.get("question", ""),
    )


async def analyze_full_chain(
    db: AsyncSession,
    user_id: UUID,
    item_ids: list[UUID],
) -> ChainFullAnalysis:
    items = []
    for iid in item_ids:
        title, summary, _ = await _fetch_content_for_chain(db, iid, user_id)
        if title or summary:
            items.append({"title": title, "summary": summary})

    text = await ai_service.analyze_full_chain(items)
    return ChainFullAnalysis(analysis=text)


async def get_random_items(
    db: AsyncSession, user_id: UUID, count: int = 5
) -> list[ChainItem]:
    items = await crud_items.get_random_with_embedding(db, user_id, limit=count)
    return [_to_chain_item(ui) for ui in items]


async def synthesize_with_items(
    db: AsyncSession,
    user_id: UUID,
    item_ids: list[UUID],
    prompt: str,
) -> "SynthesizeResult":
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload
    from app.schemas.explore import FocusSource, SynthesizeResult

    if not item_ids:
        raise ValueError("item_ids cannot be empty")

    result = await db.execute(
        select(UserItem)
        .options(joinedload(UserItem.content))
        .where(
            UserItem.id.in_(item_ids),
            UserItem.user_id == user_id,
            UserItem.deleted_at.is_(None),
        )
    )
    items = list(result.scalars().all())

    if not items:
        raise ValueError("no valid items found")

    items_payload = [
        {"title": ui.title, "summary": (ui.notes_md or "")[:500]}
        for ui in items
    ]
    content = await ai_service.synthesize_custom(prompt, items_payload)

    sources = [
        FocusSource(
            id=ui.id,
            url=ui.url or ui.content.url,
            title=ui.title,
            thumbnail_url=ui.thumbnail_url,
            source_type=ui.source_type,
            saved_at=ui.saved_at,
        )
        for ui in items
    ]
    return SynthesizeResult(content=content, sources=sources)


async def get_surprise(db: AsyncSession, user_id: UUID) -> SurpriseResult:
    # async session 不支援並發，循序執行
    connection = await _unexpected_connection(db, user_id)
    forgotten = await _forgotten_item(db, user_id)
    trend = await _topic_trend(db, user_id)
    insights = [i for i in [connection, forgotten, trend] if i is not None]
    return SurpriseResult(insights=insights)
