from fastapi import APIRouter, HTTPException

from app.crud import collections as crud_collections
from app.dependencies import DbSession
from app.schemas.collection import CollectionShareItemRead, CollectionShareRead

router = APIRouter()


def _to_share_read(collection) -> CollectionShareRead:
    items = [
        CollectionShareItemRead(
            id=ci.content.id,
            url=ci.content.url,
            title=ci.content.title,
            thumbnail_url=ci.content.thumbnail_url,
            source_type=ci.content.source_type,
        )
        for ci in sorted(collection.collection_items, key=lambda x: x.sort_order)
    ]
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


@router.get("/{slug}", response_model=CollectionShareRead)
async def get_public_collection(slug: str, db: DbSession):
    collection = await crud_collections.get_public_by_slug(db, slug)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return _to_share_read(collection)
