import logging
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.crud import items as crud_items
from app.models.content_object import ContentObject, SourceType, detect_source_type
from app.quota_depends import get_video_max_sec
from app.schemas.item import ArticleUpdate, ItemCreate, ItemRead, ItemSummaryUpdate, ItemUpdate
from app.providers.instagram import normalize_instagram_url
from app.providers.youtube import normalize_youtube_url
from app.workers.process_item import process_item


@dataclass
class _ItemCreateResult:
    item: ItemRead
    needs_processing: bool
    content_id: UUID | None = None
    user_item_id: UUID | None = None
    url: str | None = None
    max_video_sec: int = field(default=1200)


def _item_to_read(
    user_item,
    current_user_id: UUID | None = None,
    tags=None,
    include_content_md: bool = True,
) -> ItemRead:
    """UserItem snapshot 欄位直讀，不再需要 JOIN ContentObject 取 display 資料。
    content 只用於取 content_id（AI 層 FK）。
    """
    from app.schemas.tag import TagRead as _TagRead
    resolved_tags = [_TagRead.model_validate(t) for t in (tags or [])]

    # is_owner: 由 source_type 判斷，note 代表使用者手寫
    is_owner = user_item.source_type == SourceType.note.value

    content = user_item.content  # 可能為 None（未來 nullable 時）
    content_id = content.id if content is not None else None

    return ItemRead(
        id=user_item.id,
        content_id=content_id,
        url=user_item.url or (content.url if content else ""),
        title=user_item.title,
        summary=user_item.summary,
        summary_i18n=user_item.summary_i18n,
        thumbnail_url=user_item.thumbnail_url,
        saved_at=user_item.saved_at,
        deleted_at=user_item.deleted_at,
        parsed_at=user_item.parsed_at,
        status=user_item.status,
        source_type=user_item.source_type,
        transcription_source=user_item.transcription_source,
        is_owner=is_owner,
        content_md=user_item.content_md if include_content_md else None,
        is_draft=user_item.is_draft,
        is_public=user_item.is_public,
        tags=resolved_tags,
    )


async def _run_process_item(
    content_id: UUID, user_id: UUID, user_item_id: UUID, url: str, max_video_sec: int = 1200
) -> None:
    from app.core import events
    async with AsyncSessionLocal() as db:
        try:
            await process_item(db, content_id, user_id, user_item_id, url, max_video_sec)
        except Exception:
            logger.exception(
                "process_item failed: content_id=%s user_id=%s user_item_id=%s",
                content_id, user_id, user_item_id,
            )
            events.fail(str(user_item_id))


async def prepare_item_create(
    db: AsyncSession,
    user_id: UUID,
    data: ItemCreate,
) -> _ItemCreateResult:
    """Create or restore DB records. Returns item data plus processing params when AI processing is needed."""
    if data.url is None:
        # ── 使用者手寫文章：直接建立 UserItem，snapshot 欄位直接填入 ──────────
        item_id = uuid4()
        article_url = f"/app/item/{item_id}"

        # ContentObject 仍然建立，作為 AI 處理（embedding/chunks）的錨點
        content = ContentObject(
            url=article_url,
            source_type=SourceType.note,
        )
        db.add(content)
        await db.flush()

        from app.models.user_item import UserItem as UserItemModel
        init_title = data.title or "未命名文章"
        user_item = UserItemModel(
            id=item_id,
            user_id=user_id,
            content_id=content.id,
            is_draft=True,
            # snapshot 欄位
            url=article_url,
            title=init_title,
            source_type=SourceType.note.value,
        )
        db.add(user_item)
        await db.flush()
        await db.commit()
        await db.refresh(user_item)
        return _ItemCreateResult(item=_item_to_read(user_item, user_id), needs_processing=False)

    # ── 外部 URL ──────────────────────────────────────────────────────────────
    url = normalize_youtube_url(normalize_instagram_url(data.url))
    max_video_sec = await get_video_max_sec(db, user_id)

    result = await db.execute(select(ContentObject).where(ContentObject.url == url))
    content = result.scalar_one_or_none()

    is_new_content = content is None
    if is_new_content:
        content = ContentObject(
            url=url,
            source_type=detect_source_type(url),
        )
        db.add(content)
        await db.flush()

    existing = await crud_items.get_by_content_id(db, user_id, content.id, include_deleted=True)
    if existing is not None:
        if existing.deleted_at is not None:
            from datetime import datetime, timezone
            existing.deleted_at = None
            existing.status = "active"
            await db.commit()
            await db.refresh(existing)
        needs = content.parsed_at is None
        return _ItemCreateResult(
            item=_item_to_read(existing, user_id),
            needs_processing=needs,
            content_id=content.id if needs else None,
            user_item_id=existing.id if needs else None,
            url=url if needs else None,
            max_video_sec=max_video_sec,
        )

    src_type = detect_source_type(url)
    from app.models.user_item import UserItem as UserItemModel
    user_item = UserItemModel(
        user_id=user_id,
        content_id=content.id,
        # snapshot 欄位（title/summary 等 AI 處理後由 process_item 寫入）
        url=url,
        source_type=src_type.value,
        title=data.title,
    )
    db.add(user_item)
    await db.commit()
    await db.refresh(user_item)

    needs = is_new_content or content.parsed_at is None
    return _ItemCreateResult(
        item=_item_to_read(user_item, user_id),
        needs_processing=needs,
        content_id=content.id if needs else None,
        user_item_id=user_item.id if needs else None,
        url=url if needs else None,
        max_video_sec=max_video_sec,
    )


async def create_item(
    db: AsyncSession,
    user_id: UUID,
    data: ItemCreate,
    background_tasks: BackgroundTasks,
) -> ItemRead:
    result = await prepare_item_create(db, user_id, data)
    if result.needs_processing:
        background_tasks.add_task(
            _run_process_item,
            result.content_id,
            user_id,
            result.user_item_id,
            result.url,
            result.max_video_sec,
        )
    return result.item


async def list_items(db: AsyncSession, user_id: UUID) -> list[ItemRead]:
    user_items = await crud_items.get_all(db, user_id)
    return [
        _item_to_read(ui, user_id, tags=[it.tag for it in ui.item_tags], include_content_md=False)
        for ui in user_items
    ]


async def list_items_page(
    db: AsyncSession,
    user_id: UUID,
    *,
    tag_ids: list[UUID] | None = None,
    tag_logic: str = "and",
    saved_after: datetime | None = None,
    sort: str = "saved_desc",
    page: int = 1,
    page_size: int = 25,
) -> "ItemPage":
    from app.schemas.item import ItemPage as _ItemPage
    offset = (page - 1) * page_size
    user_items, total = await crud_items.get_page(
        db, user_id,
        tag_ids=tag_ids,
        tag_logic=tag_logic,
        saved_after=saved_after,
        sort=sort,
        offset=offset,
        limit=page_size,
    )
    items = [
        _item_to_read(ui, user_id, tags=[it.tag for it in ui.item_tags], include_content_md=False)
        for ui in user_items
    ]
    return _ItemPage(items=items, total=total, page=page, page_size=page_size)


async def get_item(db: AsyncSession, user_id: UUID, item_id: UUID) -> ItemRead:
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return _item_to_read(user_item, user_id)


async def update_item(
    db: AsyncSession, user_id: UUID, item_id: UUID, data: ItemUpdate
) -> ItemRead:
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if data.title is not None:
        user_item.title = data.title          # snapshot 欄位
    if data.status is not None:
        user_item.status = data.status
    await db.commit()
    await db.refresh(user_item)
    return _item_to_read(user_item, user_id)


async def update_item_summary(
    db: AsyncSession, user_id: UUID, item_id: UUID, data: ItemSummaryUpdate
) -> ItemRead:
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    if user_item.source_type != SourceType.note.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot edit summary of external content",
        )

    user_item.summary_i18n = data.summary_i18n
    await db.commit()
    await db.refresh(user_item)
    return _item_to_read(user_item, user_id)


async def list_archived_items(db: AsyncSession, user_id: UUID) -> list[ItemRead]:
    user_items = await crud_items.get_archived(db, user_id)
    return [_item_to_read(ui, user_id) for ui in user_items]


async def translate_item_notes(
    db: AsyncSession, user_id: UUID, item_id: UUID, locale: str
) -> ItemRead:
    from app.services import ai_service

    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    summary_i18n: dict = dict(user_item.summary_i18n or {})
    if summary_i18n.get(locale):
        return _item_to_read(user_item, user_id)

    zh_md = user_item.summary
    if not zh_md:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No source notes to translate",
        )

    translated_md = await ai_service.translate_notes(zh_md)
    summary_i18n[locale] = ai_service.md_to_tiptap(translated_md)
    user_item.summary_i18n = summary_i18n
    await db.commit()
    await db.refresh(user_item)
    return _item_to_read(user_item, user_id)


async def delete_item(db: AsyncSession, user_id: UUID, item_id: UUID) -> None:
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    await crud_items.soft_delete(db, user_item)
    await db.commit()


async def list_articles(db: AsyncSession, user_id: UUID) -> list[ItemRead]:
    from app.models.user_item import UserItem as UserItemModel
    result = await db.execute(
        select(UserItemModel)
        .where(
            UserItemModel.user_id == user_id,
            UserItemModel.deleted_at.is_(None),
            UserItemModel.source_type == SourceType.note.value,
        )
        .order_by(UserItemModel.saved_at.desc())
    )
    # 不需要 JOIN ContentObject：snapshot 欄位直接在 UserItem 上
    return [_item_to_read(ui, user_id) for ui in result.scalars().all()]


async def update_article(
    db: AsyncSession, user_id: UUID, item_id: UUID, data: ArticleUpdate
) -> ItemRead:
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if user_item.source_type != SourceType.note.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an owned article")
    if data.title is not None:
        user_item.title = data.title
    if data.content_md is not None:
        user_item.content_md = data.content_md
    if data.is_draft is not None:
        user_item.is_draft = data.is_draft
    if data.is_public is not None:
        user_item.is_public = data.is_public
    await db.commit()
    await db.refresh(user_item)
    return _item_to_read(user_item, user_id)


async def publish_article(
    db: AsyncSession,
    user_id: UUID,
    item_id: UUID,
    background_tasks: BackgroundTasks,
) -> ItemRead:
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if user_item.source_type != SourceType.note.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an owned article")
    user_item.is_draft = False
    await db.commit()
    await db.refresh(user_item)
    # 每次保存都重新 AI 分析（文章內容會變動）
    content = user_item.content
    background_tasks.add_task(
        _run_process_item, content.id, user_id, user_item.id, user_item.url or content.url
    )
    return _item_to_read(user_item, user_id)


async def upload_article_cover(
    db: AsyncSession,
    user_id: UUID,
    item_id: UUID,
    image_bytes: bytes,
    content_type: str,
) -> ItemRead:
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if user_item.source_type != SourceType.note.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an owned article")

    from app.core.supabase import get_supabase
    from app.core.config import settings
    supabase = await get_supabase()
    ext = "jpg" if "jpeg" in content_type or "jpg" in content_type else "png"
    # 用 user_item.id 當 storage path（原為 content.id，語意相同，因為 note 是 1:1）
    path = f"thumbnails/{user_item.id}.{ext}"
    try:
        await supabase.storage.from_(settings.storage_bucket).upload(
            path, image_bytes, {"content-type": content_type, "upsert": "true"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Storage upload failed: {e}",
        )
    thumbnail_url = await supabase.storage.from_(settings.storage_bucket).get_public_url(path)
    user_item.thumbnail_url = thumbnail_url
    await db.commit()
    await db.refresh(user_item)
    return _item_to_read(user_item, user_id)


async def delete_article_cover(
    db: AsyncSession,
    user_id: UUID,
    item_id: UUID,
) -> ItemRead:
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if user_item.source_type != SourceType.note.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an owned article")

    if user_item.thumbnail_url:
        from app.core.supabase import get_supabase
        from app.core.config import settings
        supabase = await get_supabase()
        for ext in ("jpg", "png", "webp"):
            path = f"thumbnails/{user_item.id}.{ext}"
            try:
                await supabase.storage.from_(settings.storage_bucket).remove([path])
            except Exception:
                pass
        user_item.thumbnail_url = None
        await db.commit()
        await db.refresh(user_item)
    return _item_to_read(user_item, user_id)
