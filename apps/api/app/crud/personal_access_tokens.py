import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personal_access_token import PersonalAccessToken

TOKEN_PREFIX = "pat_"


def _generate_raw_token() -> str:
    return TOKEN_PREFIX + secrets.token_urlsafe(48)


def _hash_token(raw_token: str) -> str:
    """SHA-256 hash — 快速且足夠安全，PAT 本身已夠長"""
    return hashlib.sha256(raw_token.encode()).hexdigest()


async def create_pat(
    db: AsyncSession,
    user_id: uuid.UUID,
    name: str,
) -> tuple[PersonalAccessToken, str]:
    """建立 PAT，回傳 (model, raw_token)。raw_token 只出現這一次。"""
    raw_token = _generate_raw_token()
    token_hash = _hash_token(raw_token)

    pat = PersonalAccessToken(
        user_id=user_id,
        name=name,
        token_hash=token_hash,
        created_at=datetime.now(timezone.utc),
    )
    db.add(pat)
    await db.flush()
    return pat, raw_token


async def get_pats_by_user(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[PersonalAccessToken]:
    result = await db.execute(
        select(PersonalAccessToken)
        .where(PersonalAccessToken.user_id == user_id)
        .where(PersonalAccessToken.revoked_at.is_(None))
        .order_by(PersonalAccessToken.created_at.desc())
    )
    return list(result.scalars().all())


async def get_user_id_by_token(
    db: AsyncSession,
    raw_token: str,
) -> uuid.UUID | None:
    """驗證 PAT，成功時更新 last_used_at 並回傳 user_id"""
    if not raw_token.startswith(TOKEN_PREFIX):
        return None

    token_hash = _hash_token(raw_token)
    result = await db.execute(
        select(PersonalAccessToken)
        .where(PersonalAccessToken.token_hash == token_hash)
        .where(PersonalAccessToken.revoked_at.is_(None))
    )
    pat = result.scalar_one_or_none()
    if pat is None:
        return None

    # 更新最後使用時間
    await db.execute(
        update(PersonalAccessToken)
        .where(PersonalAccessToken.id == pat.id)
        .values(last_used_at=datetime.now(timezone.utc))
    )

    return pat.user_id


async def revoke_pat(
    db: AsyncSession,
    pat_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """撤銷 PAT，回傳是否成功（找不到或不屬於該 user 回傳 False）"""
    result = await db.execute(
        select(PersonalAccessToken)
        .where(PersonalAccessToken.id == pat_id)
        .where(PersonalAccessToken.user_id == user_id)
        .where(PersonalAccessToken.revoked_at.is_(None))
    )
    pat = result.scalar_one_or_none()
    if pat is None:
        return False

    pat.revoked_at = datetime.now(timezone.utc)
    return True
