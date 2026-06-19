"""Embedding functions — always use OpenRouter/OpenAI (text-embedding-3-small, 1536d)."""
from app.core.config import settings
from app.core.tracing import traced

from ._client import _emb


@traced(op="ai", name="embed")
async def embed(text: str) -> list[float]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
    )
    result = await client.embeddings.create(model=_emb(), input=text)
    return result.data[0].embedding


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
