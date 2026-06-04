import json

import httpx

from app.core.config import settings

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# In-memory cache loaded at startup via load_model_configs().
# Fallbacks keep the service alive even if the table is empty.
_model_cache: dict[str, str] = {
    "llm": "anthropic/claude-3-5-haiku",
    "embedding": "openai/text-embedding-3-small",
}


async def load_model_configs() -> None:
    """Load ai_model_configs from DB into the in-memory cache. Call once at startup."""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.ai_model_config import AiModelConfig

    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(AiModelConfig))).scalars().all()
        for row in rows:
            _model_cache[row.key] = row.model_id


def _llm() -> str:
    return _model_cache["llm"]


def _emb() -> str:
    return _model_cache["embedding"]

_NOTES_PROMPT = """\
You are a knowledge base assistant. Read the following content and produce structured notes in Traditional Chinese Markdown.

Use EXACTLY these section headers, in this order:

## 核心主題
One or two paragraphs explaining what this content is about and why it matters.

## 重點整理
- Key point 1
- Key point 2
(3–8 bullet points, each a complete, standalone insight)

## 內容詳解
Organize into 2–5 thematic subsections using ### headers. Each subsection captures a coherent chunk of ideas — organized knowledge, not a transcript. Omit filler and repetition.

## 關鍵洞察
- Insight or implication worth remembering
(1–4 bullets on the deeper "so what")

Rules:
- Write entirely in Traditional Chinese
- Do NOT include the video/article title as a heading
- Be thorough but organized — capture all meaningful ideas
- Return ONLY the Markdown, no extra commentary, no code fences

Content:
"""

_TAGS_PROMPT = """\
Analyze the following content and return ONLY a JSON object:
{
  "embed_text": "A concise 2-3 sentence English description of the main topic, for semantic search",
  "tags": {
    "zh-TW": ["標籤1", "標籤2", "標籤3"],
    "en": ["tag1", "tag2", "tag3"]
  }
}

Rules for tags:
- 3–7 short labels (1–3 words each)
- BROAD, REUSABLE categories — themes, domains, concepts that apply across many items
- AVOID specific proper nouns or one-off details
- Tags must be conceptually paired (same index = same concept across languages)
- Return ONLY the JSON object, no markdown fences, no extra text

Content:
"""

_TAGS_WITH_CANDIDATES_PROMPT = """\
Analyze the following content and return ONLY a JSON object.

The user already has these existing tags (zh-TW names):
{candidates}

Rules for tags:
- Choose 3–7 short labels (1–3 words each)
- PREFER existing tags from the list above when they fit — this keeps the user's tag space clean
- Only create NEW tags when no existing tag adequately covers the concept (max 2 new tags)
- BROAD, REUSABLE categories — themes, domains, concepts that apply across many items
- AVOID specific proper nouns or one-off details
- For existing tags: use the exact zh-TW name from the list; derive the English equivalent yourself
- Tags must be conceptually paired (same index = same concept across languages)
- Return ONLY the JSON object, no markdown fences, no extra text

Output format:
{{
  "embed_text": "A concise 2-3 sentence English description of the main topic, for semantic search",
  "tags": {{
    "zh-TW": ["標籤1", "標籤2", "標籤3"],
    "en": ["tag1", "tag2", "tag3"]
  }}
}}

Content:
"""


async def _llm_call(prompt: str, timeout: int = 90) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            json={
                "model": _llm(),
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=timeout,
        )
        if resp.status_code == 401:
            raise RuntimeError("OpenRouter service unavailable")
        resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _parse_json(raw: str) -> dict:
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    return json.loads(raw, strict=False)


def md_to_tiptap(md: str) -> dict:
    """Convert AI-generated Markdown to Tiptap JSON doc format."""
    lines = md.splitlines()
    nodes: list[dict] = []
    current_list_items: list[dict] = []

    def flush_list() -> None:
        if current_list_items:
            nodes.append({"type": "bulletList", "content": list(current_list_items)})
            current_list_items.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_list()
            continue
        if stripped.startswith("## "):
            flush_list()
            nodes.append({
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": stripped[3:].strip()}],
            })
        elif stripped.startswith("### "):
            flush_list()
            nodes.append({
                "type": "heading",
                "attrs": {"level": 3},
                "content": [{"type": "text", "text": stripped[4:].strip()}],
            })
        elif stripped.startswith("- ") or stripped.startswith("* "):
            current_list_items.append({
                "type": "listItem",
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": stripped[2:].strip()}]}],
            })
        else:
            flush_list()
            nodes.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": stripped}],
            })

    flush_list()
    return {"type": "doc", "content": nodes}


async def analyze_content(content: str, candidate_tags: list[str] | None = None) -> dict:
    """Returns {summary: {zh-TW: <tiptap_doc>}, summary_md: {zh-TW: <markdown>}, embed_text: str, tags: {zh-TW, en}}."""
    import asyncio

    truncated = content[:32000]

    if candidate_tags:
        candidates_str = "、".join(candidate_tags)
        tags_prompt = _TAGS_WITH_CANDIDATES_PROMPT.format(candidates=candidates_str) + truncated
    else:
        tags_prompt = _TAGS_PROMPT + truncated

    notes_task = asyncio.create_task(_llm_call(_NOTES_PROMPT + truncated))
    tags_task = asyncio.create_task(_llm_call(tags_prompt))

    zh_md, tags_raw = await asyncio.gather(notes_task, tags_task)
    tags_data = _parse_json(tags_raw)

    return {
        "summary_md": {"zh-TW": zh_md},
        "summary": {"zh-TW": md_to_tiptap(zh_md)},
        "embed_text": tags_data.get("embed_text", ""),
        "tags": tags_data.get("tags", {"zh-TW": [], "en": []}),
    }


_TRANSLATE_NOTES_PROMPT = """\
Translate the following Traditional Chinese structured Markdown notes into English.

Rules:
- Keep the EXACT same Markdown structure (same ## and ### headers, same bullet format)
- Translate section headers into natural English equivalents:
  - ## 核心主題 → ## Core Topic
  - ## 重點整理 → ## Key Points
  - ## 內容詳解 → ## Detailed Notes
  - ## 關鍵洞察 → ## Key Insights
  - Translate any ### subsection titles naturally
- Translate all content faithfully — do not summarize or add new content
- Return ONLY the translated Markdown, no extra commentary

Notes to translate:
"""


async def translate_notes(zh_md: str) -> str:
    return await _llm_call(_TRANSLATE_NOTES_PROMPT + zh_md)


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
                "model": _llm(),
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
                "model": _llm(),
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
                "model": _llm(),
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
                "model": _llm(),
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
                "model": _llm(),
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
                "model": _llm(),
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


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    """依 token 估算切割文字。用空白估算（1 token ≈ 4 chars）。"""
    char_size = chunk_size * 4
    char_overlap = overlap * 4
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + char_size
        chunks.append(text[start:end].strip())
        start += char_size - char_overlap
    return [c for c in chunks if c]


_VISION_PROMPT = """\
以下是一篇 Instagram 貼文的圖片（按順序排列）。
請仔細辨識並轉錄每張圖片中的所有文字，同時描述視覺內容。
若圖片中有資訊圖表、列表、時間表等結構化內容，請保留其結構。

輸出格式（每張圖片一段）：
[圖片 N]
文字：（逐字轉錄圖中所有可見文字）
描述：（簡短描述圖片視覺內容）

請用繁體中文輸出，確保文字轉錄完整準確。
"""


async def describe_images(images: list[bytes]) -> str:
    """Run vision AI on a list of image bytes, return combined text description."""
    import base64

    if not images:
        return ""

    content: list[dict] = []
    for img_bytes in images[:10]:
        b64 = base64.b64encode(img_bytes).decode()
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        })
    content.append({"type": "text", "text": _VISION_PROMPT})

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            json={
                "model": _llm(),
                "messages": [{"role": "user", "content": content}],
            },
            timeout=120,
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
    result = await client.embeddings.create(model=_emb(), input=text)
    return result.data[0].embedding
