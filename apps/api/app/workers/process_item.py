import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import events
from app.crud import chunks as crud_chunks
from app.crud import notifications as crud_notifications
from app.crud import tags as crud_tags
from app.models.content_object import ContentObject
from app.models.user_item import UserItem
from app.models.item_tag import TagSource
from app.models.notification import NotificationType
from app.providers import get_provider
from app.providers.base import FetchInfo
from app.services import ai_service

logger = logging.getLogger(__name__)


async def process_item(
    db: AsyncSession,
    content_id: UUID,
    user_id: UUID,
    user_item_id: UUID,
    url: str,
    max_video_sec: int = 1200,
) -> None:
    content, user_item = await _load_content_and_item(db, content_id, user_item_id)
    if content is None or user_item is None:
        return

    provider = get_provider(url)

    # ── Stage: fetching_info ──────────────────────────────────────────────────
    events.emit(str(user_item_id), "fetching_info")
    try:
        info = await provider.fetch_info(
            url,
            str(content_id),
            # 文章（note）的 raw content 來自 UserItem.content_md
            content_md=user_item.content_md,
        )
    except Exception:
        logger.exception("fetch_info failed for url=%s", url)
        await _fail(db, user_id, user_item_id, user_item, url)
        return

    # commit #1: 立即儲存 provider metadata（title/thumbnail 等）
    await _save_fetch_info(db, content, user_item, info)

    # ArticleProvider 直接提供 raw_content，跳過 fetch_content
    if info.raw_content is not None:
        raw_content: str | None = info.raw_content
    else:
        # ── Stage: fetching_content → understanding ───────────────────────────
        try:
            raw_content = await provider.fetch_content(
                url,
                info,
                stage_cb=lambda stage: events.emit(str(user_item_id), stage),
            )
        except Exception:
            logger.exception("fetch_content failed for url=%s", url)
            await _fail(db, user_id, user_item_id, user_item, url)
            return

    if not raw_content or not raw_content.strip():
        logger.warning("No content extracted for url=%s", url)
        await _fail(db, user_id, user_item_id, user_item, url)
        return

    # ── Stage: analyzing ─────────────────────────────────────────────────────
    events.emit(str(user_item_id), "analyzing")
    candidate_tags = await crud_tags.get_top_tags(db, user_id, limit=50)
    analysis = await ai_service.analyze_content(
        raw_content, candidate_tags=[t.name for t in candidate_tags]
    )

    summary_md = analysis.get("summary_md", {}).get("zh-TW", "")
    if not summary_md:
        logger.error("AI returned empty summary for url=%s", url)
        await _fail(db, user_id, user_item_id, user_item, url)
        return

    # 若 provider 沒有提供 title，由 AI 生成
    title = user_item.title or info.title
    if not title:
        title = await ai_service.generate_title(summary_md)

    # ── Stage: embedding ─────────────────────────────────────────────────────
    events.emit(str(user_item_id), "embedding")
    embed_text = analysis.get("embed_text") or summary_md[:500]
    summary_embedding = await ai_service.embed(embed_text)

    chunk_texts = ai_service.chunk_text(raw_content)
    chunk_records: list[dict] = []
    for chunk in chunk_texts:
        emb = await ai_service.embed(chunk)
        chunk_records.append({"text": chunk, "embedding": emb})

    # ── Stage: validating ────────────────────────────────────────────────────
    events.emit(str(user_item_id), "validating")

    missing = []
    if not title:
        missing.append("title")
    if not summary_md:
        missing.append("summary")
    if not summary_embedding:
        missing.append("embedding")
    if not chunk_records:
        missing.append("chunks")

    if missing:
        logger.error("Validation failed for url=%s, missing=%s", url, missing)
        await _fail(db, user_id, user_item_id, user_item, url)
        return

    # commit #2: AI 結果 + parsed_at（同時更新 ContentObject 與 UserItem snapshot）
    await _save_analysis(
        db, content_id, content, user_item, user_id, user_item_id, url,
        title, analysis, summary_embedding, chunk_records,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _load_content_and_item(
    db: AsyncSession,
    content_id: UUID,
    user_item_id: UUID,
) -> tuple[ContentObject | None, UserItem | None]:
    content_result = await db.execute(
        select(ContentObject).where(ContentObject.id == content_id)
    )
    content = content_result.scalar_one_or_none()

    item_result = await db.execute(
        select(UserItem).where(UserItem.id == user_item_id)
    )
    user_item = item_result.scalar_one_or_none()

    if content is None or user_item is None:
        events.notify(str(user_item_id))
    return content, user_item


async def _save_fetch_info(
    db: AsyncSession,
    content: ContentObject,
    user_item: UserItem,
    info: FetchInfo,
) -> None:
    """commit #1: 儲存 provider 抓到的 metadata。
    title / thumbnail 同時寫進 UserItem snapshot。
    """
    if info.title:
        if not content.title:
            content.title = info.title       # ContentObject（CollectionItem 用）
        if not user_item.title:
            user_item.title = info.title     # UserItem snapshot
    if info.duration_sec is not None:
        content.duration_sec = info.duration_sec
    if info.thumbnail_url:
        if not content.thumbnail_url:
            content.thumbnail_url = info.thumbnail_url
        if not user_item.thumbnail_url:
            user_item.thumbnail_url = info.thumbnail_url
    if info.raw_data:
        content.raw_data = info.raw_data
    await db.commit()


async def _save_analysis(
    db: AsyncSession,
    content_id: UUID,
    content: ContentObject,
    user_item: UserItem,
    user_id: UUID,
    user_item_id: UUID,
    url: str,
    title: str,
    analysis: dict,
    summary_embedding: list[float],
    chunk_records: list[dict],
) -> None:
    """commit #2: AI 結果、embedding、chunks、tags、parsed_at。
    ContentObject 存 embedding（向量搜尋用）；
    UserItem 存 summary / summary_i18n / title（顯示用 snapshot）。
    """
    summary_i18n = analysis.get("summary", {})
    summary_md = analysis.get("summary_md", {})
    tags_i18n = analysis.get("tags", {})
    now = datetime.now(timezone.utc)

    # ── ContentObject：embedding + display 雙寫（CollectionItem 需要 display）─
    content.embedding = summary_embedding
    content.parsed_at = now
    if not content.title:
        content.title = title
    content.summary = summary_md.get("zh-TW", "")
    content.summary_i18n = summary_i18n

    # ── UserItem snapshot：同步顯示欄位（讀取不需 JOIN）────────────────────
    if not user_item.title:
        user_item.title = title
    user_item.summary = summary_md.get("zh-TW", "")
    user_item.summary_i18n = summary_i18n
    user_item.parsed_at = now

    # transcription_source snapshot（如果 content 有的話）
    if content.transcription_source is not None:
        user_item.transcription_source = content.transcription_source.value

    await crud_chunks.replace_chunks(db, content_id, chunk_records)

    zh_tags = tags_i18n.get("zh-TW", [])
    en_tags = tags_i18n.get("en", [])
    for zh_name, en_name in zip(zh_tags, en_tags):
        tag = await crud_tags.get_or_create(
            db, user_id, name=zh_name,
            name_i18n={"zh-TW": zh_name, "en": en_name},
        )
        await crud_tags.attach_tag(db, user_item_id, tag.id, source=TagSource.ai)

    await crud_notifications.create(
        db,
        user_id=user_id,
        type=NotificationType.item_processed,
        title=user_item.title or url,
        item_id=user_item_id,
    )

    await db.commit()
    events.notify(str(user_item_id))


async def _fail(
    db: AsyncSession,
    user_id: UUID,
    user_item_id: UUID,
    user_item: UserItem,
    url: str,
) -> None:
    user_item.deleted_at = datetime.now(timezone.utc)

    await crud_notifications.create(
        db,
        user_id=user_id,
        type=NotificationType.item_failed,
        title="內容處理失敗",
        body=f"「{user_item.title or url}」無法取得或分析內容，請稍後再試。",
        item_id=user_item_id,
    )

    await db.commit()
    events.fail(str(user_item_id))
