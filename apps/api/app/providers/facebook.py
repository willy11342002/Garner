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

        raw = info.raw_data
        sfc = raw.get("short_form_video_context") or {}

        # ── Reel path: has video ──────────────────────────────────────────────
        if sfc:
            message = raw.get("message") or {}
            description = message.get("text") if isinstance(message, dict) else (message or "")

            playback = sfc.get("playback_video") or {}
            delivery = playback.get("videoDeliveryLegacyFields") or {}
            video_url = delivery.get("browser_native_sd_url") or delivery.get("browser_native_hd_url")

            if stage_cb:
                stage_cb("understanding")

            if video_url:
                video_bytes = await apify_service.download_bytes(video_url)
                if video_bytes:
                    return await ai_service.understand(
                        video_bytes_list=video_bytes,
                        mime_type="video/mp4",
                        description=description or None,
                    )

            return await ai_service.understand(description=description or None) if description else None

        # ── Post path: has images ─────────────────────────────────────────────
        description = raw.get("text") or ""

        image_urls: list[str] = []
        for media in raw.get("media", []):
            uri = (media.get("photo_image") or {}).get("uri") or media.get("thumbnail")
            if uri:
                image_urls.append(uri)

        if stage_cb:
            stage_cb("understanding")

        image_bytes_list: list[bytes] = []
        if image_urls:
            results = await asyncio.gather(*[apify_service.download_bytes(u) for u in image_urls])
            image_bytes_list = [b for b in results if b]

        if image_bytes_list or description:
            return await ai_service.understand(image_bytes_list=image_bytes_list, description=description or None)

        return None
