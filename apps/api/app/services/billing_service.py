"""
Gumroad billing service.

Gumroad Resource Subscriptions webhook 事件分流：
- sale                 → 新購買 / 每月續費
- cancellation         → 訂閱取消（cancelled）
- subscription_ended   → 訂閱期滿結束（expired）
- subscription_restarted → 重新啟用（視同新購）
- refunded             → 退款（cancelled）
"""
import logging
from datetime import datetime, timezone, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User

logger = logging.getLogger(__name__)

_ENDED_EVENTS = {"cancellation", "subscription_ended", "refunded"}


async def handle_webhook(db: AsyncSession, payload: dict) -> None:
    """依 resource_name 分流至對應 handler。

    Ping（Settings → Ping endpoint）的 payload 沒有 resource_name，
    但 sale 事件會帶 cancelled / refunded flag，需在此處攔截。
    """
    resource_name = payload.get("resource_name", "sale")

    # Ping-style: sale event 裡帶 cancelled / refunded → 走結束邏輯
    if resource_name == "sale":
        cancelled = payload.get("cancelled", "false").lower() == "true"
        refunded = payload.get("refunded", "false").lower() == "true"
        if cancelled or refunded:
            gumroad_sub_id = payload.get("subscription_id") or payload.get("sale_id", "")
            email = payload.get("email", "").lower().strip()
            await _handle_ended(db, gumroad_sub_id=gumroad_sub_id, email=email, expired=False)
            return

    if resource_name in _ENDED_EVENTS:
        gumroad_sub_id = payload.get("subscription_id") or payload.get("sale_id", "")
        email = payload.get("email", "").lower().strip()
        expired = resource_name == "subscription_ended"
        await _handle_ended(db, gumroad_sub_id=gumroad_sub_id, email=email, expired=expired)
    else:
        # sale（正常購買 / 續費）/ subscription_restarted / 未知事件
        await _handle_sale(db, payload)


async def _handle_sale(db: AsyncSession, payload: dict) -> None:
    """處理新購買或每月續費。"""
    email = payload.get("email", "").lower().strip()
    gumroad_sub_id = payload.get("subscription_id") or payload.get("sale_id", "")

    if not email:
        logger.warning("Gumroad ping missing email, skipping")
        return

    user = await _get_user_by_email(db, email)
    if user is None:
        logger.info("Gumroad sale for unknown email %s, skipping", email)
        return

    pro_plan = await _get_pro_plan(db)
    if pro_plan is None:
        logger.error("Pro plan not found in DB")
        return

    now = datetime.now(timezone.utc)
    existing = await _get_subscription_by_gumroad_id(db, gumroad_sub_id)

    if existing:
        # 續費：從上期結束日往後算，避免因 webhook 延遲累積偏差
        prev_end = existing.current_period_end
        period_start = prev_end if prev_end > now else now
        period_end = period_start + timedelta(days=31)
        existing.status = SubscriptionStatus.active
        existing.current_period_start = period_start
        existing.current_period_end = period_end
        existing.cancelled_at = None
        logger.info("Renewed subscription %s for %s", gumroad_sub_id, email)
    else:
        # 新訂閱：先取消用戶舊的 active 訂閱（防重複）
        await _cancel_existing_active(db, user.id)
        sub = Subscription(
            user_id=user.id,
            plan_id=pro_plan.id,
            status=SubscriptionStatus.active,
            current_period_start=now,
            current_period_end=now + timedelta(days=31),
            gumroad_subscription_id=gumroad_sub_id or None,
        )
        db.add(sub)
        logger.info("Created new subscription for %s", email)

    await db.commit()


async def _handle_ended(
    db: AsyncSession,
    gumroad_sub_id: str = "",
    email: str = "",
    expired: bool = False,
) -> None:
    """處理取消、退款、或期滿結束。"""
    sub = None

    if gumroad_sub_id:
        sub = await _get_subscription_by_gumroad_id(db, gumroad_sub_id)

    if sub is None and email:
        user = await _get_user_by_email(db, email)
        if user:
            sub = await _get_active_subscription(db, user.id)

    if sub is None:
        logger.info("No active subscription found to end (id=%s email=%s)", gumroad_sub_id, email)
        return

    sub.status = SubscriptionStatus.expired if expired else SubscriptionStatus.cancelled
    sub.cancelled_at = datetime.now(timezone.utc)
    await db.commit()
    logger.info(
        "%s subscription %s",
        "Expired" if expired else "Cancelled",
        gumroad_sub_id or email,
    )


async def cancel_user_subscription(db: AsyncSession, user_id: UUID) -> None:
    """在 app 內取消訂閱：先呼叫 Gumroad API，成功後更新 DB。"""
    from app.services.gumroad_service import cancel_subscriber

    sub = await _get_active_subscription(db, user_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="No active subscription found")

    if sub.gumroad_subscription_id:
        await cancel_subscriber(sub.gumroad_subscription_id)

    sub.status = SubscriptionStatus.cancelled
    sub.cancelled_at = datetime.now(timezone.utc)
    await db.commit()
    logger.info("Cancelled subscription for user %s", user_id)


# ── helpers ──────────────────────────────────────────────────────────────────

async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def _get_pro_plan(db: AsyncSession) -> Plan | None:
    result = await db.execute(select(Plan).where(Plan.name == "pro"))
    return result.scalar_one_or_none()


async def _get_subscription_by_gumroad_id(db: AsyncSession, gumroad_sub_id: str) -> Subscription | None:
    if not gumroad_sub_id:
        return None
    result = await db.execute(
        select(Subscription).where(Subscription.gumroad_subscription_id == gumroad_sub_id)
    )
    return result.scalar_one_or_none()


async def _get_active_subscription(db: AsyncSession, user_id) -> Subscription | None:
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.status.in_([SubscriptionStatus.active, SubscriptionStatus.trialing]),
        )
    )
    return result.scalar_one_or_none()


async def _cancel_existing_active(db: AsyncSession, user_id) -> None:
    sub = await _get_active_subscription(db, user_id)
    if sub:
        sub.status = SubscriptionStatus.cancelled
        sub.cancelled_at = datetime.now(timezone.utc)
