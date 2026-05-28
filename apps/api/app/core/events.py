import asyncio

_pending: dict[str, asyncio.Event] = {}


def register(item_id: str) -> asyncio.Event:
    event = asyncio.Event()
    _pending[item_id] = event
    return event


def notify(item_id: str) -> None:
    event = _pending.pop(item_id, None)
    if event:
        event.set()
