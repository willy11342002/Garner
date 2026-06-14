"""
Pipeline stage decorator for process_item DAG.

Usage:
    @stage("note", retries=2)
    async def run_note(ctx: StageContext, ...) -> None:
        ...

    # called with the user_item_id, NOT a pre-built context:
    await run_note(user_item_id, ...)

Each invocation runs in its OWN database session: the decorator opens an
`AsyncSessionLocal`, loads a fresh `UserItem` by id, builds a `StageContext`
bound to that session, and passes it to the wrapped function. This lets
independent stages run concurrently (via asyncio.gather) without sharing a
single AsyncSession — provided concurrent stages write disjoint columns / tables.

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
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import events
from app.core.database import AsyncSessionLocal
from app.models.user_item import UserItem

logger = logging.getLogger(__name__)


@dataclass
class StageContext:
    db: AsyncSession
    user_item: UserItem


def stage(name: str, retries: int = 2, retry_delay: float = 2.0):
    """Decorator factory. `name` must match the column prefix in user_items.

    The wrapped function is invoked as `wrapper(user_item_id, *args, **kwargs)`;
    the decorator loads the item in a fresh session and passes a StageContext
    (`ctx`) bound to that session as the first argument to the wrapped function.
    """

    def decorator(fn: Callable):
        async def wrapper(user_item_id: UUID, *args, **kwargs):
            last_exc: Exception | None = None
            last_elapsed_ms = 0

            for attempt in range(retries + 1):
                async with AsyncSessionLocal() as db:
                    item = await db.get(UserItem, user_item_id)
                    if item is None:
                        return None

                    setattr(item, f"{name}_status", "running")
                    setattr(item, f"{name}_error", None)
                    await db.commit()
                    events.emit(str(item.id), name)

                    ctx = StageContext(db=db, user_item=item)
                    t0 = time.monotonic()
                    try:
                        result = await fn(ctx, *args, **kwargs)
                    except Exception as exc:
                        last_exc = exc
                        last_elapsed_ms = int((time.monotonic() - t0) * 1000)
                        if attempt < retries:
                            logger.warning(
                                "stage=%s attempt=%d/%d failed, retrying in %.1fs: %s",
                                name, attempt + 1, retries + 1, retry_delay, exc,
                            )
                        else:
                            logger.exception("stage=%s failed after %d attempts", name, retries + 1)
                    else:
                        elapsed_ms = int((time.monotonic() - t0) * 1000)
                        setattr(item, f"{name}_status", "complete")
                        setattr(item, f"{name}_duration_ms", elapsed_ms)
                        await db.commit()
                        return result

                if attempt < retries:
                    await asyncio.sleep(retry_delay)

            # Final failure: record error state in a fresh session.
            async with AsyncSessionLocal() as db:
                item = await db.get(UserItem, user_item_id)
                if item is not None:
                    setattr(item, f"{name}_status", "error")
                    setattr(item, f"{name}_error", str(last_exc))
                    setattr(item, f"{name}_duration_ms", last_elapsed_ms)
                    await db.commit()
            raise last_exc  # re-raise so DAG can decide whether to abort or continue

        wrapper.__name__ = fn.__name__
        return wrapper

    return decorator
