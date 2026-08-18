from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    # Session-mode pooler (port 5432) supports prepared statements — no need to disable.
    # If you ever switch back to transaction-mode pooler (port 6543), add:
    #   connect_args={"statement_cache_size": 0}
    # 前端載入一頁會併發打 7+ 支 API（me / trips / trip-tags / notifications /
    # reports / folders / sessions）。pool_size 小於這個突發量時，超出的部分走
    # overflow，而 overflow 連線用完就關、不留在池裡 —— 等於每次載入都要重建幾條連線，
    # 而建一條到新加坡的連線是 TCP(110ms) + TLS(~220ms) + 認證(~110ms) ≈ 450ms。
    pool_size=20,
    max_overflow=10,
    # pre_ping 會在每次借出連線前多打一支 SELECT 1 —— 對 ap-southeast-1 實測是
    # 每個請求固定 +110ms。改成主動短週期回收：防陳舊連線的效果一樣，成本從
    # 「每個請求一次來回」降成「每 5 分鐘換一條連線」。
    # 若出現偶發的 stale connection 錯誤，把 pool_pre_ping=True 加回來即可。
    pool_recycle=300,
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
