"""Cross-encoder rerank — FlashRank 自架 ONNX，多語模型（含中文）。"""
import asyncio

_ranker = None
_ranker_lock = asyncio.Lock()


def _load_ranker():
    from flashrank import Ranker

    # cache_dir must match the Dockerfile's pre-download step exactly, or the
    # baked-in model weights won't be found and this re-downloads at runtime.
    return Ranker(model_name="ms-marco-MultiBERT-L-12", cache_dir="/app/.cache/flashrank")


async def rerank(query: str, passages: list[dict]) -> list[dict]:
    """passages: [{"id": str, "text": str}, ...] → 依相關度降冪排序後的同結構清單。"""
    global _ranker
    if not passages:
        return []
    if _ranker is None:
        async with _ranker_lock:
            if _ranker is None:
                _ranker = await asyncio.to_thread(_load_ranker)
    from flashrank import RerankRequest

    request = RerankRequest(query=query, passages=passages)
    return await asyncio.to_thread(_ranker.rerank, request)
