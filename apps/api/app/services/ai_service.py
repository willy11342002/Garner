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


_FOCUS_SYSTEM = """\
你是用戶的個人知識庫助理。根據以下用戶存過的內容，用繁體中文回答用戶的問題。
回答要具體、有洞察力，並直接引用或連結到相關內容。
使用 <em> 標籤標記關鍵詞或概念（HTML 格式）。
回答長度 3-5 句，不要分點列舉，用自然的段落。
"""

_FOCUS_TEMPLATE = """\
用戶問題：{query}

用戶存過的相關內容：
{items}

請根據上面的內容回答用戶的問題。
"""


async def synthesize_focus(query: str, items: list[dict]) -> str:
    items_text = "\n".join(
        f"[{i+1}] 標題：{it['title'] or '(無標題)'}\n    摘要：{it['summary'] or '(無摘要)'}"
        for i, it in enumerate(items)
    )
    prompt = _FOCUS_TEMPLATE.format(query=query, items=items_text)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            json={
                "model": "anthropic/claude-3-5-haiku",
                "messages": [
                    {"role": "system", "content": _FOCUS_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=60,
        )
        if resp.status_code == 401:
            raise RuntimeError("OpenRouter service unavailable")
        resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


_HOP_SYSTEM = """\
你是用戶的個人知識庫助理。分析兩筆內容之間的關聯，用繁體中文回答，返回 JSON。
"""

_HOP_TEMPLATE = """\
內容 A（較早存入）：
標題：{title_a}
摘要：{summary_a}

內容 B（較新存入）：
標題：{title_b}
摘要：{summary_b}

請返回 JSON，格式如下（只返回 JSON，不要 markdown fences）：
{{
  "connection": "2-3 句說明 A 和 B 的核心關聯，用 <em> 標記關鍵詞",
  "ideation": "2-3 句結合兩者的創意發想或應用可能",
  "question": "這個連結引出了什麼值得繼續探索的問題？一句話"
}}
"""

_CHAIN_SYSTEM = """\
你是用戶的個人知識庫助理。分析一段探索路徑，看出整體模式，用繁體中文回答。
"""

_CHAIN_TEMPLATE = """\
用戶的探索路徑（依序）：
{items}

請用 3-5 句話，分析這條探索路徑背後隱藏的思考模式或興趣主題，
並指出用戶可能還沒意識到的洞察。使用 <em> 標記關鍵詞。
"""


async def analyze_chain_hop(
    title_a: str | None,
    summary_a: str | None,
    title_b: str | None,
    summary_b: str | None,
) -> dict:
    prompt = _HOP_TEMPLATE.format(
        title_a=title_a or "(無標題)",
        summary_a=summary_a or "(無摘要)",
        title_b=title_b or "(無標題)",
        summary_b=summary_b or "(無摘要)",
    )
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            json={
                "model": "anthropic/claude-3-5-haiku",
                "messages": [
                    {"role": "system", "content": _HOP_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=60,
        )
        if resp.status_code == 401:
            raise RuntimeError("OpenRouter service unavailable")
        resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"].strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    return json.loads(raw)


async def analyze_full_chain(items: list[dict]) -> str:
    items_text = "\n".join(
        f"[{i+1}] {it['title'] or '(無標題)'}：{it['summary'] or '(無摘要)'}"
        for i, it in enumerate(items)
    )
    prompt = _CHAIN_TEMPLATE.format(items=items_text)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            json={
                "model": "anthropic/claude-3-5-haiku",
                "messages": [
                    {"role": "system", "content": _CHAIN_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=60,
        )
        if resp.status_code == 401:
            raise RuntimeError("OpenRouter service unavailable")
        resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


async def embed(text: str) -> list[float]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
    )
    result = await client.embeddings.create(model="openai/text-embedding-3-small", input=text)
    return result.data[0].embedding
