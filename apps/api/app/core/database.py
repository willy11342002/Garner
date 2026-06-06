from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    # Session-mode pooler (port 5432) supports prepared statements — no need to disable.
    # If you ever switch back to transaction-mode pooler (port 6543), add:
    #   connect_args={"statement_cache_size": 0}
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,   # drop stale connections after container restarts
    pool_recycle=1800,    # recycle every 30 min to avoid server-side idle timeout
    connect_args={
        "server_settings": {
            # Tell the server to send TCP keepalives so NAT/firewall
            # doesn't silently drop idle pool connections.
            "tcp_keepalives_idle": "60",
            "tcp_keepalives_interval": "10",
            "tcp_keepalives_count": "5",
        }
    },
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
