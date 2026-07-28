"""jieba 中文斷詞 — 供 BM25 tsvector 建置與查詢時使用。

Postgres 的 'simple' text search config 對連續中文字不會斷詞（整段當一個 token），
所以中文內容要先在應用層斷好詞、空白分隔後再進 to_tsvector。

字典打包在 pip 套件內、從本地磁碟載入，沒有網路請求（原本用 CKIP 的
ckip-transformers 每次冷啟動都會打好幾輪 HuggingFace API 做 revision 檢查，
在 Fly 的 shared-cpu-1x 單核機器上會卡住整個 event loop，連 /health 都回應不了）。
"""
import asyncio

_ws_driver = None
_driver_lock = asyncio.Lock()


def _load_driver():
    import jieba

    jieba.initialize()
    return jieba


def _cut(driver, text: str) -> list[str]:
    return list(driver.cut(text))


async def preload_segment() -> None:
    """供啟動時背景預熱用，避免第一次真正呼叫 segment() 時卡在載入 driver。"""
    global _ws_driver
    if _ws_driver is None:
        async with _driver_lock:
            if _ws_driver is None:
                _ws_driver = await asyncio.to_thread(_load_driver)


async def segment(text: str) -> str:
    """回傳空白分隔的斷詞結果，供 to_tsvector('simple', ...) 使用。"""
    if not text:
        return ""
    await preload_segment()
    tokens = await asyncio.to_thread(_cut, _ws_driver, text)
    return " ".join(tokens)
