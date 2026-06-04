import json
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_object import ContentObject
from app.providers.base import ContentProvider, FetchResult


class ArticleProvider(ContentProvider):
    @classmethod
    def matches(cls, url: str) -> bool:
        return not url.startswith("http")  # internal content (URL starts with /)

    async def fetch(
        self,
        db: AsyncSession,
        user_id: UUID,
        url: str,
        content: ContentObject,
        stage_cb=None,
    ) -> FetchResult:
        raw = _extract_text_from_tiptap(content.content_md) if content.content_md else None
        thumbnail_url = await self.fetch_thumbnail(str(content.id), url)
        return FetchResult(raw_content=raw, thumbnail_url=thumbnail_url)


def _extract_text_from_tiptap(content_md: str) -> str | None:
    try:
        doc = json.loads(content_md)
    except Exception:
        return None

    parts: list[str] = []

    def walk(node: dict) -> None:
        if node.get("type") == "text":
            parts.append(node.get("text", ""))
        for child in node.get("content", []):
            walk(child)
        if node.get("type") in ("paragraph", "heading", "blockquote", "listItem"):
            parts.append("\n")

    walk(doc)
    text = "".join(parts).strip()
    return text or None
