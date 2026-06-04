import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.core import events
from app.crud import items as crud_items
from app.crud import tags as crud_tags
from app.dependencies import CurrentUser, DbSession
from app.schemas.item import ItemCreate, ItemPendingReviewRead, ItemRead, ItemSummaryUpdate, ItemUpdate
from app.schemas.tag import TagBulkConfirm, TagCreate, TagRead, TagSingleConfirm
from app.services import item_service

router = APIRouter()


@router.get("/", response_model=list[ItemRead])
async def list_items(current_user: CurrentUser, db: DbSession):
    return await item_service.list_items(db, UUID(current_user["sub"]))


@router.post("/", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(
    data: ItemCreate,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DbSession,
):
    return await item_service.create_item(db, UUID(current_user["sub"]), data, background_tasks)


@router.get("/pending-review", response_model=list[ItemPendingReviewRead])
async def list_pending_review(current_user: CurrentUser, db: DbSession):
    rows = await crud_tags.get_items_with_pending_tags(db, UUID(current_user["sub"]))
    return [
        ItemPendingReviewRead(
            id=ui.id,
            url=ui.content.url,
            title=ui.content.title,
            thumbnail_url=ui.content.thumbnail_url,
            saved_at=ui.saved_at,
            pending_tags=[TagRead.model_validate(t) for t in tags],
        )
        for ui, tags in rows
    ]


@router.get("/archived", response_model=list[ItemRead])
async def list_archived(current_user: CurrentUser, db: DbSession):
    return await item_service.list_archived_items(db, UUID(current_user["sub"]))


@router.get("/{item_id}", response_model=ItemRead)
async def get_item(item_id: UUID, current_user: CurrentUser, db: DbSession):
    return await item_service.get_item(db, UUID(current_user["sub"]), item_id)


@router.patch("/{item_id}", response_model=ItemRead)
async def update_item(item_id: UUID, data: ItemUpdate, current_user: CurrentUser, db: DbSession):
    return await item_service.update_item(db, UUID(current_user["sub"]), item_id, data)


@router.patch("/{item_id}/summary", response_model=ItemRead)
async def update_item_summary(item_id: UUID, data: ItemSummaryUpdate, current_user: CurrentUser, db: DbSession):
    return await item_service.update_item_summary(db, UUID(current_user["sub"]), item_id, data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: UUID, current_user: CurrentUser, db: DbSession):
    await item_service.delete_item(db, UUID(current_user["sub"]), item_id)


@router.get("/{item_id}/stream")
async def stream_item_status(item_id: UUID, current_user: CurrentUser, db: DbSession):
    user_item = await crud_items.get_one(db, UUID(current_user["sub"]), item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    async def generator():
        if user_item.content.parsed_at is not None:
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
            ItemTag.confirmed == True,  # noqa: E712
        )
    )
    return list(result.scalars().all())


@router.get("/{item_id}/tags/pending", response_model=list[TagRead])
async def list_pending_item_tags(item_id: UUID, current_user: CurrentUser, db: DbSession):
    from sqlalchemy import select
    from app.models.item_tag import ItemTag
    from app.models.tag import Tag
    result = await db.execute(
        select(Tag)
        .join(ItemTag, ItemTag.tag_id == Tag.id)
        .where(
            ItemTag.user_item_id == item_id,
            Tag.user_id == UUID(current_user["sub"]),
            ItemTag.confirmed == False,  # noqa: E712
        )
    )
    return list(result.scalars().all())


@router.post("/{item_id}/tags", response_model=TagRead)
async def attach_tag(
    item_id: UUID,
    data: TagCreate,
    current_user: CurrentUser,
    db: DbSession,
    pending: bool = Query(default=False),
):
    user_id = UUID(current_user["sub"])
    tag = await crud_tags.get_or_create(db, user_id, data.name)
    await crud_tags.attach_tag(db, item_id, tag.id, confirmed=not pending)
    await db.commit()
    return tag


@router.post("/{item_id}/tags/confirm/single", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_item_tag(item_id: UUID, body: TagSingleConfirm, current_user: CurrentUser, db: DbSession):
    found = await crud_tags.confirm_item_tag(db, item_id, body.tag_id)
    if not found:
        raise HTTPException(status_code=404, detail="Pending tag not found")
    await db.commit()


@router.post("/{item_id}/tags/confirm/bulk", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_item_tags_bulk(item_id: UUID, body: TagBulkConfirm, current_user: CurrentUser, db: DbSession):
    await crud_tags.confirm_item_tags_bulk(db, item_id, body.tag_ids)
    await db.commit()


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
