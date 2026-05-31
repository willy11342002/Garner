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


_PLAN_SYSTEM = """\
你是 Vela 知識助理的規劃引擎。分析用戶問題，決定要呼叫哪些工具來查詢個人知識庫。

可用工具：

1. semantic_search
   語意向量搜尋，適合概念性／主題性問題。
   參數：{{"name": "semantic_search", "query": "搜尋字串"}}

2. structured_filter
   結構化篩選，所有參數皆選填，可自由組合：
   - tags（list[str]）：按標籤篩選，OR 邏輯，符合任一標籤即回傳
   - source_type（str）：按來源類型，值為 "youtube" / "article" / "ig"
   - start_date（str）：儲存日期下限，格式 YYYY-MM-DD
   - end_date（str）：儲存日期上限，格式 YYYY-MM-DD
   參數：{{"name": "structured_filter", "tags": [...], "source_type": "...", "start_date": "...", "end_date": "..."}}

規則：
- 兩個工具可以同時呼叫，結果自動合併去重
- structured_filter 省略的參數代表不篩選該維度，不需要全填
- 如果問題同時有語意需求又有篩選條件，兩個工具一起用效果最好
- 只輸出 JSON，不要 markdown fences

今天日期：{today}

輸出格式：
{{
  "reasoning": "2-3 句分析推理，繁體中文",
  "tools": [
    {{"name": "工具名稱", ...其他參數}}
  ]
}}
"""


async def plan_tools(query: str, history: list[dict], today: str) -> dict:
    """分析用戶問題，回傳 reasoning + tool 清單。"""
    history_text = "\n".join(
        f"{'用戶' if m['role'] == 'user' else '助理'}：{m['content']}"
        for m in history[-4:]
    ) if history else ""
    prompt = f"對話脈絡：\n{history_text}\n\n用戶最新問題：{query}" if history_text else f"用戶問題：{query}"
    system = _PLAN_SYSTEM.format(today=today)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            json={
                "model": "anthropic/claude-3-5-haiku",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=30,
        )
        if resp.status_code == 401:
            raise RuntimeError("OpenRouter service unavailable")
        resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"].strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    return json.loads(raw)


_CHAT_SYSTEM = """\
你是 Vela 知識助理。用戶存了很多網頁文章和 YouTube 影片在知識庫裡。
你的工作是根據用戶的問題，從他們存過的內容中找到相關資訊，給出具體有洞察力的回答。
用繁體中文回答。回答自然、簡潔，不要過度列舉。
如果知識庫裡沒有相關內容，直接說沒有找到，不要捏造。
"""

_CHAT_CONTEXT_TEMPLATE = """\
【用戶長期記憶】
{memory}

【相關知識庫內容】
{items}

【對話歷史】
{history}

用戶：{query}
"""

_COMPRESS_SYSTEM = """\
將以下對話摘要成 3-5 句話的長期記憶，記住用戶感興趣的主題、關心的問題和思考模式。
只保留對未來對話有用的資訊，用繁體中文輸出。
"""


async def chat_stream(
    query: str,
    history: list[dict],
    retrieved_items: list[dict],
    memory_summary: str | None,
):
    """Yield text chunks from OpenRouter streaming response."""
    items_text = "\n".join(
        f"[{i+1}] 標題：{it['title'] or '(無標題)'}\n    摘要：{it['summary'] or '(無摘要)'}"
        for i, it in enumerate(retrieved_items)
    ) if retrieved_items else "（未找到相關內容）"

    history_text = "\n".join(
        f"{'用戶' if m['role'] == 'user' else '助理'}：{m['content']}"
        for m in history[-8:]
    ) if history else "（無）"

    user_content = _CHAT_CONTEXT_TEMPLATE.format(
        memory=memory_summary or "（無）",
        items=items_text,
        history=history_text,
        query=query,
    )

    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream(
            "POST",
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            json={
                "model": "anthropic/claude-3-5-haiku",
                "stream": True,
                "messages": [
                    {"role": "system", "content": _CHAT_SYSTEM},
                    {"role": "user", "content": user_content},
                ],
            },
        ) as resp:
            if resp.status_code == 401:
                raise RuntimeError("OpenRouter service unavailable")
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                import json as _json
                try:
                    chunk = _json.loads(data)
                    delta = chunk["choices"][0]["delta"].get("content", "")
                    if delta:
                        yield delta
                except Exception:
                    continue


async def compress_memory(
    current_summary: str | None,
    recent_messages: list[dict],
) -> str:
    conversation = "\n".join(
        f"{'用戶' if m['role'] == 'user' else '助理'}：{m['content']}"
        for m in recent_messages
    )
    prompt = f"現有摘要：\n{current_summary or '（無）'}\n\n新對話：\n{conversation}"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            json={
                "model": "anthropic/claude-3-5-haiku",
                "messages": [
                    {"role": "system", "content": _COMPRESS_SYSTEM},
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
