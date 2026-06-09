"""
Gumroad Resource Subscriptions 管理。

啟動時自動向 Gumroad 註冊 webhook，確保以下事件都能收到：
- sale
- cancellation
- subscription_ended
- subscription_restarted
- refunded
"""
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GUMROAD_API = "https://api.gumroad.com/v2"

EVENTS = [
    "sale",
    "cancellation",
    "subscription_ended",
    "subscription_restarted",
    "refunded",
]


async def cancel_subscriber(subscriber_id: str) -> None:
    """透過 Gumroad API 取消訂閱。"""
    if not settings.gumroad_access_token:
        raise RuntimeError("GUMROAD_ACCESS_TOKEN not set")

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.delete(
            f"{GUMROAD_API}/subscribers/{subscriber_id}",
            params={"access_token": settings.gumroad_access_token},
        )

    if resp.status_code != 200:
        logger.error("Failed to cancel Gumroad subscriber %s: %s", subscriber_id, resp.text)
        raise RuntimeError(f"Gumroad cancel failed: {resp.text}")

    logger.info("Cancelled Gumroad subscriber %s", subscriber_id)


async def register_webhooks(webhook_url: str) -> None:
    """
    向 Gumroad 註冊所有需要的 webhook event。
    若已存在相同 URL 的訂閱則跳過（冪等）。
    """
    if not settings.gumroad_access_token:
        logger.warning("GUMROAD_ACCESS_TOKEN not set, skipping webhook registration")
        return

    async with httpx.AsyncClient(timeout=10) as client:
        # 先取得現有的 resource subscriptions
        resp = await client.get(
            f"{GUMROAD_API}/resource_subscriptions",
            params={"access_token": settings.gumroad_access_token},
        )
        if resp.status_code != 200:
            logger.error("Failed to list Gumroad resource subscriptions: %s", resp.text)
            return

        existing = resp.json().get("resource_subscriptions", [])
        existing_set = {
            (s["resource_name"], s["post_url"])
            for s in existing
        }

        for event in EVENTS:
            if (event, webhook_url) in existing_set:
                logger.info("Gumroad webhook already registered: %s → %s", event, webhook_url)
                continue

            reg = await client.put(
                f"{GUMROAD_API}/resource_subscriptions",
                data={
                    "access_token": settings.gumroad_access_token,
                    "resource_name": event,
                    "post_url": webhook_url,
                },
            )
            if reg.status_code == 200:
                logger.info("Gumroad webhook registered: %s → %s", event, webhook_url)
            else:
                logger.error(
                    "Failed to register Gumroad webhook %s: %s", event, reg.text
                )
