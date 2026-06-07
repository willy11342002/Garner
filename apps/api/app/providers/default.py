from app.providers.base import ContentProvider, FetchInfo


class DefaultProvider(ContentProvider):
    """Fallback provider for any http(s) URL not matched by a specific provider."""

    @classmethod
    def matches(cls, url: str) -> bool:
        return True

    async def fetch_info(
        self,
        url: str,
        content_id: str,
        content_md: str | None = None,
    ) -> FetchInfo:
        from app.services import apify_service

        result = await apify_service.fetch_article(url)

        thumbnail_url = None
        if result.thumbnail_url:
            thumb_bytes = await apify_service.download_bytes(result.thumbnail_url)
            if thumb_bytes:
                thumbnail_url = await self._cache_thumbnail(content_id, thumb_bytes)
        if not thumbnail_url:
            thumbnail_url = result.thumbnail_url

        return FetchInfo(
            raw_data=result.raw_data,
            title=result.title,
            duration_sec=None,
            thumbnail_url=thumbnail_url,
        )

    async def fetch_content(
        self,
        url: str,
        info: FetchInfo,
        stage_cb=None,
    ) -> str | None:
        if stage_cb:
            stage_cb("fetching_content")
        # Article text comes directly from Apify — no LLM understanding needed
        return info.raw_data.get("text") or info.raw_data.get("markdown") or None
