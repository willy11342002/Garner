"""
explore_service：Browse stats + Focus RAG + Surprise AI 洞察。

RAG 核心（rag_retrieve / rag_synthesize）設計為獨立函式，
未來 AI Chat service 可直接 import 複用，不依賴 explore 的 schema。
"""

from datetime import timedelta, timezone
from datetime import datetime as dt
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import collections as crud_collections
from app.crud import items as crud_items
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
    """將 query embed 後做向量搜尋，回傳 (UserItem, distance) 清單。"""
    embedding = await ai_service.embed(query)
    return await crud_items.semantic_search(db, user_id, embedding, limit=limit)


async def rag_synthesize(
    query: str,
    hits: list[tuple[UserItem, float]],
) -> str:
    """將搜尋結果傳給 LLM 合成回答。輸入格式與 explore/chat 無關。"""
    items_payload = [
        {"title": ui.content.title, "summary": ui.content.summary}
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
            url=ui.content.url,
            title=ui.content.title,
            thumbnail_url=ui.content.thumbnail_url,
            source_type=ui.content.source_type.value if ui.content.source_type else None,
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
        url=ui.content.url,
        title=ui.content.title,
        thumbnail_url=ui.content.thumbnail_url,
        source_type=ui.content.source_type.value if ui.content.source_type else None,
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
            f"你 {_time_ago(old_item.saved_at)}存的「{old_item.content.title or '(無標題)'}」"
            f"和最近存的「{recent_item.content.title or '(無標題)'}」"
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
            f"{_time_ago(ui.saved_at)}你存了「{ui.content.title or '(無標題)'}」，"
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
        url=ui.content.url,
        title=ui.content.title,
        thumbnail_url=ui.content.thumbnail_url,
        source_type=ui.content.source_type.value if ui.content.source_type else None,
        saved_at=ui.saved_at,
    )


async def get_chain_start_items(
    db: AsyncSession, user_id: UUID, start_type: str
) -> list[ChainItem]:
    if start_type == "forgotten":
        items = await crud_items.get_forgotten(db, user_id, limit=3)
    else:
        items = await crud_items.get_recent_with_embedding(db, user_id, limit=3)
    return [_to_chain_item(ui) for ui in items]


async def get_chain_candidates(
    db: AsyncSession,
    user_id: UUID,
    item_id: UUID,
    exclude_ids: list[UUID],
) -> list[ChainItem]:
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload
    from app.models.content_object import ContentObject

    result = await db.execute(
        select(UserItem)
        .options(joinedload(UserItem.content))
        .join(UserItem.content)
        .where(UserItem.id == item_id, UserItem.user_id == user_id)
    )
    current = result.scalar_one_or_none()
    if not current or not current.content.embedding:
        return []

    hits = await crud_items.semantic_search(
        db,
        user_id,
        embedding=current.content.embedding,
        limit=4,
        exclude_ids=[item_id, *exclude_ids],
    )
    return [_to_chain_item(ui) for ui, _ in hits]


async def analyze_hop(
    db: AsyncSession,
    user_id: UUID,
    from_item_id: UUID,
    to_item_id: UUID,
) -> ChainHopAnalysis:
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    async def _fetch(iid: UUID) -> "UserItem":
        r = await db.execute(
            select(UserItem)
            .options(joinedload(UserItem.content))
            .where(UserItem.id == iid, UserItem.user_id == user_id)
        )
        return r.scalar_one()

    from_item = await _fetch(from_item_id)
    to_item = await _fetch(to_item_id)

    raw = await ai_service.analyze_chain_hop(
        title_a=from_item.content.title,
        summary_a=from_item.content.summary,
        title_b=to_item.content.title,
        summary_b=to_item.content.summary,
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
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    items = []
    for iid in item_ids:
        r = await db.execute(
            select(UserItem)
            .options(joinedload(UserItem.content))
            .where(UserItem.id == iid, UserItem.user_id == user_id)
        )
        ui = r.scalar_one_or_none()
        if ui:
            items.append({"title": ui.content.title, "summary": ui.content.summary})

    text = await ai_service.analyze_full_chain(items)
    return ChainFullAnalysis(analysis=text)


async def get_surprise(db: AsyncSession, user_id: UUID) -> SurpriseResult:
    # async session 不支援並發，循序執行
    connection = await _unexpected_connection(db, user_id)
    forgotten = await _forgotten_item(db, user_id)
    trend = await _topic_trend(db, user_id)
    insights = [i for i in [connection, forgotten, trend] if i is not None]
    return SurpriseResult(insights=insights)
