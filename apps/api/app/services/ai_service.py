import json

import httpx

from app.core.config import settings

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_ANALYZE_PROMPT = """\
Analyze the following content and return ONLY a JSON object with this exact structure:
{
  "summary": {
    "zh-TW": "2-3 sentence summary in Traditional Chinese",
    "en": "2-3 sentence summary in English"
  },
  "tags": {
    "zh-TW": ["標籤1", "標籤2", "標籤3"],
    "en": ["tag1", "tag2", "tag3"]
  }
}

Rules:
- Summary: 2-3 sentences capturing the main ideas
- Tags: 3-7 short topic labels (1-3 words each)
- Tags must be BROAD, REUSABLE categories — themes, genres, domains, or concepts that apply across many pieces of content
- AVOID specific proper nouns (character names, place names, episode titles, technique names)
- AVOID overly narrow descriptors that only describe one specific detail
- PREFER general concepts: e.g. "穿越" over "穿越規則", "反派" over a specific villain's name, "戀愛" over "告白場景"
- A good tag should be usable to label dozens of different items on the same topic
- Tags must be conceptually paired (same index = same concept across languages)
- Return ONLY the JSON object, no markdown fences, no extra text

Content:
"""


async def analyze_content(content: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            json={
                "model": "anthropic/claude-3-5-haiku",
                "messages": [{"role": "user", "content": _ANALYZE_PROMPT + content[:8000]}],
            },
            timeout=60,
        )
        if resp.status_code == 401:
            raise RuntimeError("OpenRouter service unavailable")
        resp.raise_for_status()

    raw = resp.json()["choices"][0]["message"]["content"].strip()
    # Strip markdown code fences if model wraps the JSON
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    return json.loads(raw)


async def embed(text: str) -> list[float]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
    )
    result = await client.embeddings.create(model="openai/text-embedding-3-small", input=text)
    return result.data[0].embedding
