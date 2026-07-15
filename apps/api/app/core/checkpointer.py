"""LangGraph checkpointer for the ingest pipeline (app/services/ingest/).

Separate from the main SQLAlchemy/asyncpg engine (app/core/database.py) —
langgraph-checkpoint-postgres talks to Postgres over psycopg3, its own
connection pool, only used by the ingest graph's checkpointer.

Module-level singleton, mirroring the `engine` / `AsyncSessionLocal` pattern
in app/core/database.py. Initialized once in the app lifespan.
"""
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.config import settings

_checkpointer: AsyncPostgresSaver | None = None
_cm = None


def _psycopg_conninfo() -> str:
    return settings.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def init_checkpointer() -> AsyncPostgresSaver:
    global _checkpointer, _cm
    _cm = AsyncPostgresSaver.from_conn_string(_psycopg_conninfo())
    _checkpointer = await _cm.__aenter__()
    await _checkpointer.setup()  # no-op after the first call — creates its own tables
    return _checkpointer


async def close_checkpointer() -> None:
    global _cm, _checkpointer
    if _cm is not None:
        await _cm.__aexit__(None, None, None)
    _cm = None
    _checkpointer = None


def get_checkpointer() -> AsyncPostgresSaver:
    if _checkpointer is None:
        raise RuntimeError("checkpointer not initialized — call init_checkpointer() during app startup")
    return _checkpointer
