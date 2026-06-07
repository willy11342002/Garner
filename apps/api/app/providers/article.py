import json

from app.providers.base import ContentProvider, FetchInfo


class ArticleProvider(ContentProvider):
    """Internal content created directly in the app (URL starts with /)."""

    @classmethod
    def matches(cls, url: str) -> bool:
        return not url.startswith("http")

    async def fetch_info(
        self,
        url: str,
        content_id: str,
        content_md: str | None = None,
    ) -> FetchInfo:
        raw_content = _extract_text_from_tiptap(content_md) if content_md else None
        return FetchInfo(raw_data={}, raw_content=raw_content)

    async def fetch_content(
        self,
        url: str,
        info: FetchInfo,
        stage_cb=None,
    ) -> str | None:
        # raw_content already set in fetch_info; this path is never reached
        return info.raw_content


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
