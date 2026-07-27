"""CKIP ALBERT-tiny 中文斷詞 — 供 BM25 tsvector 建置與查詢時使用。

Postgres 的 'simple' text search config 對連續中文字不會斷詞（整段當一個 token），
所以中文內容要先在應用層斷好詞、空白分隔後再進 to_tsvector。
"""
import asyncio

_ws_driver = None
_driver_lock = asyncio.Lock()


def _load_driver():
    from ckip_transformers.nlp import CkipWordSegmenter

    return CkipWordSegmenter(model="albert-tiny")


async def segment(text: str) -> str:
    """回傳空白分隔的斷詞結果，供 to_tsvector('simple', ...) 使用。"""
    global _ws_driver
    if not text:
        return ""
    if _ws_driver is None:
        async with _driver_lock:
            if _ws_driver is None:
                _ws_driver = await asyncio.to_thread(_load_driver)
    tokens = await asyncio.to_thread(_ws_driver, [text])
    return " ".join(tokens[0])
