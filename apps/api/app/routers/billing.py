"""
Billing router — Gumroad Resource Subscriptions webhook + checkout URL helper。

驗證方式：比對 seller_id（Gumroad Resource Subscriptions 不發送 x-gumroad-signature）
"""
import logging
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.config import settings
from app.dependencies import CurrentUser, DbSession
from app.services import billing_service

logger = logging.getLogger(__name__)

router = APIRouter()

GUMROAD_CHECKOUT_URL = "https://willy11342002.gumroad.com/l/garner"
GUMROAD_MANAGE_URL = "https://app.gumroad.com/subscriptions"


# ── Webhook ───────────────────────────────────────────────────────────────────

@router.post("/webhook")
async def gumroad_webhook(request: Request, db: DbSession):
    """Gumroad Resource Subscriptions webhook endpoint。"""
    # form-encoded payload
    try:
        form = await request.form()
        payload = dict(form)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid form data")

    logger.info("Gumroad raw payload: %s", payload)

    # seller_id 防禦：確認事件來自自己的 Gumroad 帳號
    seller_id = payload.get("seller_id", "")
    if seller_id and seller_id != settings.gumroad_seller_id:
        logger.warning("Gumroad webhook: invalid seller_id %s", seller_id)
        raise HTTPException(status_code=403, detail="Invalid seller_id")

    logger.info(
        "Gumroad webhook received: resource=%s product=%s email=%s sub_id=%s",
        payload.get("resource_name"),
        payload.get("product_permalink"),
        payload.get("email"),
        payload.get("subscription_id"),
    )

    await billing_service.handle_webhook(db, payload)
    return {"status": "ok"}


# ── Cancel Subscription ───────────────────────────────────────────────────────

@router.post("/cancel", status_code=200)
async def cancel_subscription(current_user: CurrentUser, db: DbSession):
    """取消當前用戶的訂閱（呼叫 Gumroad API + 更新 DB）。"""
    user_id = UUID(current_user["sub"])
    try:
        await billing_service.cancel_user_subscription(db, user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel subscription for user %s: %s", user_id, e)
        raise HTTPException(status_code=502, detail="Failed to cancel via Gumroad, please try again")
    return {"status": "cancelled"}


# ── Checkout URL ──────────────────────────────────────────────────────────────

class CheckoutResponse(BaseModel):
    url: str


@router.get("/checkout", response_model=CheckoutResponse)
async def get_checkout_url(current_user: CurrentUser):
    """回傳 Gumroad checkout URL（附帶 email 預填）。"""
    email = current_user.get("email", "")
    url = GUMROAD_CHECKOUT_URL
    if email:
        url = f"{GUMROAD_CHECKOUT_URL}?{urlencode({'email': email})}"
    return CheckoutResponse(url=url)


# ── Billing Portal ────────────────────────────────────────────────────────────

class PortalResponse(BaseModel):
    url: str


@router.post("/portal", response_model=PortalResponse)
async def get_billing_portal(current_user: CurrentUser):
    """回傳 Gumroad 訂閱管理 URL。"""
    return PortalResponse(url=GUMROAD_MANAGE_URL)
