"""
Pipeline stage decorator for process_item DAG.

Usage:
    @stage("note", retries=2)
    async def run_note(ctx: StageContext) -> None:
        ...

The decorator:
- Sets <stage>_status = "running" before the call
- Records duration in <stage>_duration_ms
- On success: sets status = "complete", clears error
- On failure after all retries: sets status = "error", writes error message
- Commits after each status change so the frontend can poll progress
"""
import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import events
from app.models.user_item import UserItem

logger = logging.getLogger(__name__)


@dataclass
class StageContext:
    db: AsyncSession
    user_item: UserItem


def stage(name: str, retries: int = 2, retry_delay: float = 2.0):
    """Decorator factory. `name` must match the column prefix in user_items."""

    def decorator(fn: Callable):
        async def wrapper(ctx: StageContext, *args, **kwargs):
            item = ctx.user_item
            db = ctx.db

            setattr(item, f"{name}_status", "running")
            setattr(item, f"{name}_error", None)
            await db.commit()
            events.emit(str(item.id), name)

            last_exc: Exception | None = None
            for attempt in range(retries + 1):
                t0 = time.monotonic()
                try:
                    result = await fn(ctx, *args, **kwargs)
                    elapsed_ms = int((time.monotonic() - t0) * 1000)
                    setattr(item, f"{name}_status", "complete")
                    setattr(item, f"{name}_duration_ms", elapsed_ms)
                    await db.commit()
                    return result
                except Exception as exc:
                    last_exc = exc
                    elapsed_ms = int((time.monotonic() - t0) * 1000)
                    setattr(item, f"{name}_duration_ms", elapsed_ms)
                    if attempt < retries:
                        logger.warning(
                            "stage=%s attempt=%d/%d failed, retrying in %.1fs: %s",
                            name, attempt + 1, retries + 1, retry_delay, exc,
                        )
                        await asyncio.sleep(retry_delay)
                    else:
                        logger.exception("stage=%s failed after %d attempts", name, retries + 1)

            setattr(item, f"{name}_status", "error")
            setattr(item, f"{name}_error", str(last_exc))
            await db.commit()
            raise last_exc  # re-raise so DAG can decide whether to abort or continue

        wrapper.__name__ = fn.__name__
        return wrapper

    return decorator
