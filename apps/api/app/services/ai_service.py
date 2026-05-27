import asyncio

import httpx

from app.core.config import settings

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


async def summarize(content: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            json={
                "model": "anthropic/claude-3-5-haiku",
                "messages": [{"role": "user", "content": f"Summarize:\n{content}"}],
            },
            timeout=60,
        )
        if resp.status_code == 401:
            raise RuntimeError("OpenRouter service unavailable")
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def embed(text: str) -> list[float]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
    )
    result = await client.embeddings.create(model="openai/text-embedding-3-small", input=text)
    return result.data[0].embedding
