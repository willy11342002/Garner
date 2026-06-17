"""
StreamRegistry：管理進行中的 chat assistant message 串流。

背景 task 透過 entry.publish() 推送 SSE event string；
SSE endpoint 透過 entry.subscribe() 取得一條獨立的 asyncio.Queue，
包含 buffer replay（斷線重連用）+ 後續 live 事件。

asyncio 單執行緒保證：publish / subscribe 均為同步方法，無 await，
故不會在兩者之間插入其他 coroutine，不需要 Lock。
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from uuid import UUID

logger = logging.getLogger("garner.stream_registry")

_DONE = object()
_FAILED = object()


@dataclass
class StreamEntry:
    buffer: list[str] = field(default_factory=list)
    _subscribers: list[asyncio.Queue] = field(default_factory=list)
    status: str = "streaming"  # streaming | complete | failed
    error_msg: str | None = None

    def publish(self, event_str: str) -> None:
        self.buffer.append(event_str)
        for q in self._subscribers:
            q.put_nowait(event_str)

    def subscribe(self, start_from: int = 0) -> asyncio.Queue:
        """回傳一條新 Queue，已包含 buffer[start_from:] 的 replay。"""
        q: asyncio.Queue = asyncio.Queue()
        # 先註冊，再 replay —— 保證之後的 publish 不會漏
        self._subscribers.append(q)
        for event_str in self.buffer[start_from:]:
            q.put_nowait(event_str)
        return q

    def complete(self) -> None:
        self.status = "complete"
        for q in self._subscribers:
            q.put_nowait(_DONE)

    def fail(self, error_msg: str = "") -> None:
        self.status = "failed"
        self.error_msg = error_msg
        for q in self._subscribers:
            q.put_nowait(_FAILED)

    def unsubscribe(self, q: asyncio.Queue) -> None:
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass


class StreamRegistry:
    def __init__(self) -> None:
        self._entries: dict[UUID, StreamEntry] = {}

    def create(self, message_id: UUID) -> StreamEntry:
        entry = StreamEntry()
        self._entries[message_id] = entry
        return entry

    def get(self, message_id: UUID) -> StreamEntry | None:
        return self._entries.get(message_id)

    def remove(self, message_id: UUID) -> None:
        self._entries.pop(message_id, None)
        logger.debug("stream_registry: removed %s (active=%d)", message_id, len(self._entries))


# Module-level singleton
stream_registry = StreamRegistry()


async def drain_entry(
    entry: StreamEntry,
    start_from: int = 0,
    heartbeat_interval: float = 15.0,
):
    """
    Async generator：從 entry 的 buffer（start_from 起）開始，
    接著 live 讀取直到 complete / failed。
    每 heartbeat_interval 秒靜默時插入一個 SSE comment 保持連線。
    """
    if entry.status in ("complete", "failed") and start_from >= len(entry.buffer):
        # 已結束且沒有新資料要 replay，直接結束
        return

    q = entry.subscribe(start_from=start_from)
    try:
        get_task: asyncio.Task | None = None
        while True:
            if get_task is None:
                get_task = asyncio.create_task(q.get())
            done, _ = await asyncio.wait({get_task}, timeout=heartbeat_interval)
            if not done:
                yield ": ping\n\n"
                continue
            item = get_task.result()
            get_task = None
            if item is _DONE:
                break
            if item is _FAILED:
                yield f"event: error\ndata: {{}}\n\n"
                break
            yield item
    finally:
        if get_task is not None:
            get_task.cancel()
        entry.unsubscribe(q)
