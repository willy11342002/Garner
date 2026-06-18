import re

from app.providers.base import ContentProvider, FetchInfo


def normalize_facebook_url(url: str) -> str:
    """Strip tracking params and return a canonical Facebook URL."""
    # Reel: facebook.com/reel/{id}
    reel = re.search(r"facebook\.com/reel/(\d+)", url)
    if reel:
        return f"https://www.facebook.com/reel/{reel.group(1)}"

    # fb.watch short link — pass through as-is (no stable canonical form)
    if "fb.watch" in url:
        return url.split("?")[0]

    # photo.php?fbid=xxx
    photo = re.search(r"facebook\.com/photo\.php\?.*?fbid=(\d+)", url)
    if photo:
        return f"https://www.facebook.com/photo.php?fbid={photo.group(1)}"

    # /posts/{id}
    posts = re.search(r"facebook\.com/([\w.]+)/posts/(\d+)", url)
    if posts:
        return f"https://www.facebook.com/{posts.group(1)}/posts/{posts.group(2)}"

    # permalink.php?story_fbid={id}
    permalink = re.search(r"story_fbid=(\d+)", url)
    if permalink:
        return f"https://www.facebook.com/permalink.php?story_fbid={permalink.group(1)}"

    return url.split("?")[0]


class FacebookProvider(ContentProvider):
    @classmethod
    def matches(cls, url: str) -> bool:
        return "facebook.com" in url or "fb.watch" in url

    async def fetch_info(
        self,
        url: str,
        content_id: str,
        content_md: str | None = None,
    ) -> FetchInfo:
        from app.services import apify_service

        result = await apify_service.fetch_facebook(url)

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
            duration_sec=result.duration_sec,
            thumbnail_url=thumbnail_url,
        )

    async def fetch_content(
        self,
        url: str,
        info: FetchInfo,
        stage_cb=None,
    ) -> str | None:
        import asyncio

        from app.services import ai_service, apify_service

        if stage_cb:
            stage_cb("fetching_content")

        description = (
            info.raw_data.get("caption")
            or info.raw_data.get("text")
            or info.raw_data.get("message")
            or ""
        )

        # Collect image URLs (actor does not provide video files)
        image_urls: list[str] = []
        for field_name in ("images", "photos", "attachments"):
            raw = info.raw_data.get(field_name) or []
            for entry in raw:
                if isinstance(entry, str):
                    image_urls.append(entry)
                elif isinstance(entry, dict):
                    img = entry.get("url") or entry.get("imageUrl") or entry.get("src")
                    if img:
                        image_urls.append(img)

        thumbnail = info.raw_data.get("thumbnailUrl")
        if thumbnail and thumbnail not in image_urls:
            image_urls.append(thumbnail)

        if stage_cb:
            stage_cb("understanding")

        image_bytes_list: list[bytes] = []
        if image_urls:
            results = await asyncio.gather(*[apify_service.download_bytes(u) for u in image_urls])
            image_bytes_list = [b for b in results if b]

        if image_bytes_list or description:
            return await ai_service.understand(image_bytes_list=image_bytes_list, description=description)

        return None
