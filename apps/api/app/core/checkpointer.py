"""LangGraph checkpointer for the ingest pipeline (app/services/ingest/).

Separate from the main SQLAlchemy/asyncpg engine (app/core/database.py) —
langgraph-checkpoint-postgres talks to Postgres over psycopg3, its own
connection pool, only used by the ingest graph's checkpointer.

Module-level singleton, mirroring the `engine` / `AsyncSessionLocal` pattern
in app/core/database.py. Initialized once in the app lifespan.

用 AsyncConnectionPool 而非 AsyncPostgresSaver.from_conn_string()：後者開的是
**單一連線**、沒有探活機制，而 fly.toml 的 auto_stop_machines = 'suspend' 不會重跑
lifespan——機器休眠幾小時後帶著一條早被 Supabase 砍掉的連線醒來，第一次 ingest 就
炸 OperationalError（item 卡在沒 parsed 的狀態）。pool 的 `check` 等同
database.py 的 pool_pre_ping=True：每次借出前先探活，死的直接丟掉重開。
"""
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.config import settings

_checkpointer: AsyncPostgresSaver | None = None
_pool: AsyncConnectionPool | None = None


def _psycopg_conninfo() -> str:
    return settings.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def init_checkpointer() -> AsyncPostgresSaver:
    global _checkpointer, _pool
    _pool = AsyncConnectionPool(
        conninfo=_psycopg_conninfo(),
        min_size=1,
        max_size=5,
        # 借出前先 SELECT 1 探活——等同 database.py 的 pool_pre_ping=True。
        check=AsyncConnectionPool.check_connection,
        # kwargs 與 from_conn_string() 內部用的完全一致：autocommit 是 setup() 跑 DDL
        # 的必要條件，dict_row 是 AsyncPostgresSaver 型別簽章要求的 row factory。
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=False,
    )
    await _pool.open(wait=True)
    _checkpointer = AsyncPostgresSaver(_pool)
    await _checkpointer.setup()  # no-op after the first call — creates its own tables
    return _checkpointer


async def close_checkpointer() -> None:
    global _pool, _checkpointer
    if _pool is not None:
        await _pool.close()
    _pool = None
    _checkpointer = None


def get_checkpointer() -> AsyncPostgresSaver:
    if _checkpointer is None:
        raise RuntimeError("checkpointer not initialized — call init_checkpointer() during app startup")
    return _checkpointer
