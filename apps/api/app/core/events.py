import asyncio

_queues: dict[str, asyncio.Queue] = {}


def register(item_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _queues[item_id] = q
    return q


def emit(item_id: str, stage: str) -> None:
    q = _queues.get(item_id)
    if q:
        q.put_nowait({"stage": stage})


def notify(item_id: str) -> None:
    _signal(item_id, "done")


def fail(item_id: str) -> None:
    _signal(item_id, "failed")


def _signal(item_id: str, stage: str) -> None:
    q = _queues.pop(item_id, None)
    if q:
        q.put_nowait({"stage": stage})
