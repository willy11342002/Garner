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
        raw_content = content_md.strip() if content_md else None
        return FetchInfo(raw_data={}, raw_content=raw_content or None)

    async def fetch_content(
        self,
        url: str,
        info: FetchInfo,
        stage_cb=None,
    ) -> str | None:
        return info.raw_content
