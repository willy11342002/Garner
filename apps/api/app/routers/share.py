from fastapi import APIRouter, HTTPException, Query

from app.crud import collections as crud_collections
from app.dependencies import DbSession
from app.schemas.collection import CollectionShareItemRead, CollectionShareRead, PublicCollectionRead

router = APIRouter()


def _to_share_read(collection) -> CollectionShareRead:
    seen: set = set()
    items = []
    for ci in sorted(collection.collection_items, key=lambda x: x.sort_order):
        if ci.content_id in seen:
            continue
        seen.add(ci.content_id)
        items.append(CollectionShareItemRead(
            id=ci.content.id,
            url=ci.content.url,
            title=ci.content.title,
            summary=ci.content.summary,
            thumbnail_url=ci.content.thumbnail_url,
            source_type=ci.content.source_type,
        ))
    return CollectionShareRead(
        id=collection.id,
        title=collection.title,
        slug=collection.slug,
        fork_count=collection.fork_count,
        created_at=collection.created_at,
        author_username=collection.user.username,
        author_avatar_url=collection.user.avatar_url,
        items=items,
    )


@router.get("/recommendations", response_model=list[PublicCollectionRead])
async def get_recommendations(
    db: DbSession,
    exclude_slug: str | None = Query(default=None),
    limit: int = Query(default=8, ge=1, le=24),
):
    rows = await crud_collections.list_public(db, offset=0, limit=limit + (1 if exclude_slug else 0))
    results = []
    for collection, item_count in rows:
        if exclude_slug and collection.slug == exclude_slug:
            continue
        if len(results) >= limit:
            break
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


@router.get("/{slug}", response_model=CollectionShareRead)
async def get_public_collection(slug: str, db: DbSession):
    collection = await crud_collections.get_public_by_slug(db, slug)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return _to_share_read(collection)
