"""Embedding functions — always use OpenRouter/OpenAI (text-embedding-3-small, 1536d)."""
import asyncio
from collections import OrderedDict

from app.core.config import settings
from app.core.tracing import traced

from ._client import _emb

# In-process LRU cache for embed() — same (model, text) always yields the same
# vector, so entries never go stale; only bounded by size, not by age.
_EMBED_CACHE_MAXSIZE = 256
_embed_cache: OrderedDict[tuple[str, str], list[float]] = OrderedDict()
_embed_cache_lock = asyncio.Lock()


@traced(op="ai", name="embed")
async def embed(text: str) -> list[float]:
    key = (_emb(), text)

    async with _embed_cache_lock:
        cached = _embed_cache.get(key)
        if cached is not None:
            _embed_cache.move_to_end(key)
            return cached

        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        result = await client.embeddings.create(model=_emb(), input=text)
        embedding = result.data[0].embedding

        _embed_cache[key] = embedding
        if len(_embed_cache) > _EMBED_CACHE_MAXSIZE:
            _embed_cache.popitem(last=False)
        return embedding


@traced(op="ai", name="embed_many")
async def embed_many(texts: list[str]) -> list[list[float]]:
    """Batch embed multiple texts in a single API call. Order is preserved."""
    if not texts:
        return []
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
    )
    result = await client.embeddings.create(model=_emb(), input=texts)
    return [item.embedding for item in sorted(result.data, key=lambda x: x.index)]
