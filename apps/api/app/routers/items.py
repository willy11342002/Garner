import asyncio
import json
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, StreamingResponse

from app.core import events
from app.core.database import AsyncSessionLocal
from app.crud import items as crud_items
from app.crud import tags as crud_tags
from app.dependencies import CurrentUser, DbSession
from app.quota_depends import SaveQuota, ReanalyzeQuota
from app.schemas.item import ItemCreate, ItemPage, ItemRead, ItemUpdate
from app.schemas.tag import TagCreate, TagRead
from app.services import item_service

router = APIRouter()


@router.get("/", response_model=ItemPage)
async def list_items(
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    tag_ids: list[UUID] = Query(default=[]),
    tag_logic: str = Query(default="and"),
    saved_after: datetime | None = Query(default=None),
    sort: str = Query(default="saved_desc"),
):
    return await item_service.list_items_page(
        db,
        UUID(current_user["sub"]),
        tag_ids=tag_ids or None,
        tag_logic=tag_logic,
        saved_after=saved_after,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_item(
    request: Request,
    data: ItemCreate,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DbSession,
    _quota: SaveQuota,
    mode: str | None = None,
):
    user_id = UUID(current_user["sub"])
    response_mode = mode or request.headers.get("X-Response-Mode", "sse")

    if response_mode == "async":
        item = await item_service.create_item(db, user_id, data, background_tasks)
        return JSONResponse(
            content=json.loads(item.model_dump_json()),
            status_code=status.HTTP_201_CREATED,
        )

    # SSE mode (default): stream progress in the POST response itself
    create_result = await item_service.prepare_item_create(db, user_id, data)
    item = create_result.item
    item_id_str = str(item.id)

    async def generator():
        # Always send the initial item first so the client has the ID immediately
        yield f"data: {json.dumps({'status': 'created', 'item': json.loads(item.model_dump_json())})}\n\n"

        if not create_result.needs_processing:
            yield f"data: {json.dumps({'status': 'done', 'item': json.loads(item.model_dump_json())})}\n\n"
            return

        q = events.register(item_id_str)
        asyncio.create_task(
            item_service._run_process_item(
                user_id,
                create_result.user_item_id,
                create_result.url,
                create_result.max_video_sec,
            )
        )

        try:
            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=300)
                except asyncio.TimeoutError:
                    yield 'data: {"status":"timeout"}\n\n'
                    return

                stage = msg.get("stage")

                if stage == "done":
                    async with AsyncSessionLocal() as fresh_db:
                        updated = await crud_items.get_one(fresh_db, user_id, create_result.user_item_id)
                        if updated:
                            item_data = item_service._item_to_read(updated, user_id)
                            yield f"data: {json.dumps({'status': 'done', 'item': json.loads(item_data.model_dump_json())})}\n\n"
                    return

                if stage == "failed":
                    yield 'data: {"status":"failed"}\n\n'
                    return

                yield f"data: {json.dumps({'status': 'progress', 'stage': stage})}\n\n"
        finally:
            events._queues.pop(item_id_str, None)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/archived", response_model=list[ItemRead])
async def list_archived(current_user: CurrentUser, db: DbSession):
    return await item_service.list_archived_items(db, UUID(current_user["sub"]))


@router.get("/{item_id}", response_model=ItemRead)
async def get_item(item_id: UUID, current_user: CurrentUser, db: DbSession):
    return await item_service.get_item(db, UUID(current_user["sub"]), item_id)


@router.patch("/{item_id}", response_model=ItemRead)
async def update_item(item_id: UUID, data: ItemUpdate, current_user: CurrentUser, db: DbSession):
    return await item_service.update_item(db, UUID(current_user["sub"]), item_id, data)



@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: UUID, current_user: CurrentUser, db: DbSession, hard: bool = False):
    await item_service.delete_item(db, UUID(current_user["sub"]), item_id, hard=hard)


@router.get("/{item_id}/stream")
async def stream_item_status(item_id: UUID, current_user: CurrentUser, db: DbSession):
    user_item = await crud_items.get_one(db, UUID(current_user["sub"]), item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    async def generator():
        if user_item.parsed_at is not None:
            item_data = item_service._item_to_read(user_item)
            yield f"data: {json.dumps({'status': 'done', 'item': json.loads(item_data.model_dump_json())})}\n\n"
            return

        q = events.register(str(item_id))

        try:
            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=300)
                except asyncio.TimeoutError:
                    yield 'data: {"status":"timeout"}\n\n'
                    return

                stage = msg.get("stage")

                if stage == "done":
                    updated = await crud_items.get_one(db, UUID(current_user["sub"]), item_id)
                    if updated:
                        item_data = item_service._item_to_read(updated)
                        yield f"data: {json.dumps({'status': 'done', 'item': json.loads(item_data.model_dump_json())})}\n\n"
                    return

                if stage == "failed":
                    yield 'data: {"status":"failed"}\n\n'
                    return

                yield f"data: {json.dumps({'status': 'progress', 'stage': stage})}\n\n"
        finally:
            events._queues.pop(str(item_id), None)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{item_id}/tags", response_model=list[TagRead])
async def list_item_tags(item_id: UUID, current_user: CurrentUser, db: DbSession):
    from sqlalchemy import select
    from app.models.item_tag import ItemTag
    from app.models.tag import Tag
    result = await db.execute(
        select(Tag)
        .join(ItemTag, ItemTag.tag_id == Tag.id)
        .where(
            ItemTag.user_item_id == item_id,
            Tag.user_id == UUID(current_user["sub"]),
        )
    )
    return list(result.scalars().all())


@router.post("/{item_id}/tags", response_model=TagRead)
async def attach_tag(
    item_id: UUID,
    data: TagCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    user_id = UUID(current_user["sub"])
    tag = await crud_tags.get_or_create(db, user_id, data.name)
    await crud_tags.attach_tag(db, item_id, tag.id)
    await db.commit()
    return tag


@router.post("/{item_id}/translate/{locale}", response_model=ItemRead)
async def translate_item_notes(
    item_id: UUID,
    locale: str,
    current_user: CurrentUser,
    db: DbSession,
):
    """Generate notes in the requested locale if not yet available. Currently supports: en."""
    SUPPORTED = {"en"}
    if locale not in SUPPORTED:
        from fastapi import HTTPException as _HTTPException
        raise _HTTPException(status_code=400, detail=f"Unsupported locale '{locale}'. Supported: {sorted(SUPPORTED)}")
    return await item_service.translate_item_notes(db, UUID(current_user["sub"]), item_id, locale)


@router.delete("/{item_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def detach_tag(item_id: UUID, tag_id: UUID, current_user: CurrentUser, db: DbSession):
    await crud_tags.detach_tag(db, item_id, tag_id)
    await db.commit()


@router.post("/{item_id}/reanalyze", status_code=status.HTTP_202_ACCEPTED)
async def reanalyze_item_notes(
    item_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DbSession,
    _quota: ReanalyzeQuota,
):
    """Re-run stage 3 (note) → stage 5 (embedding) for an existing item.

    Consumes one monthly save quota (ReanalyzeQuota checks + increments before
    this body runs). Returns immediately. Caller can poll note_status /
    embedding_status to track progress.
    """
    user_id = UUID(current_user["sub"])
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if not user_item.extract or not user_item.extract.get("raw_content"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="No raw content available for reanalysis",
        )

    async def _run() -> None:
        from sqlalchemy import select
        from app.models.user_item import UserItem
        from app.workers.process_item import _note_and_embedding

        async with AsyncSessionLocal() as bg_db:
            raw_content = (await bg_db.execute(
                select(UserItem.extract).where(UserItem.id == item_id)
            )).scalar_one()["raw_content"]

        # Each stage opens its own session; we only need raw_content + ids here.
        await _note_and_embedding(item_id, raw_content, user_id)

    background_tasks.add_task(_run)
    return {"status": "accepted"}
