"""量 DB 的往返延遲，判斷 /trips/ 慢在哪。

用法（在 apps/api 底下）：
    uv run python scripts/db_latency_probe.py

只做唯讀查詢（SELECT 1 與 list_trips），不會改任何資料。
輸出的四個數字怎麼讀：
  - connect        ：建立一條新連線（TCP + TLS + 認證）。pool 冷啟動時每條連線付一次
  - rtt            ：一次 SELECT 1 的往返。這就是「每多打一支查詢」的單價
  - pre_ping       ：pool_pre_ping=True 時每個請求多付的成本（等於一次 rtt）
  - list_trips     ：實際的列表查詢

如果 rtt 就有好幾百毫秒，瓶頸是 API 與 Supabase 的地理距離，
再怎麼減查詢數也只能逼近「1 × rtt」，得考慮把 API 部到同一區域。
"""
import asyncio
import time
from uuid import UUID

from sqlalchemy import text

from app.core.database import AsyncSessionLocal, engine


async def _timed(label, coro_fn, rounds=5):
    times = []
    for _ in range(rounds):
        t0 = time.perf_counter()
        await coro_fn()
        times.append((time.perf_counter() - t0) * 1000)
    times.sort()
    print(f"{label:<12} median {times[len(times)//2]:7.1f} ms   min {times[0]:7.1f}   max {times[-1]:7.1f}")


async def main():
    user_id = input("你的 user_id (UUID，可留空跳過 list_trips)： ").strip()

    async def connect():
        conn = await engine.connect()
        await conn.close()

    async def rtt():
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))

    print()
    await _timed("connect", connect, rounds=3)
    await _timed("rtt", rtt)

    if user_id:
        from app.crud import trips as crud_trips

        async def list_trips():
            async with AsyncSessionLocal() as db:
                await crud_trips.list_trips(db, UUID(user_id))

        await _timed("list_trips", list_trips)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
