"""AI report generation and revision."""
from ._client import _llm_call, _parse_json

_REVISE_PROMPT = """\
你是用戶的個人知識庫寫作助理。下面有一篇現有文章與用戶的修改指示。
請依指示修改文章，保留與指示無關的內容，輸出「完整的」修改後 markdown 全文。
只輸出 markdown 內文，不要任何說明，不要用 ``` 包起來。

【修改指示】
{instruction}

【現有文章】
{content}
"""

_REPORT_PROMPT = """\
你是用戶的個人知識庫寫作助理。根據以下用戶存過的內容，產出一篇結構清楚、實用的繁體中文文章（報告／規劃／指南／清單皆可）。
沿用這個標題方向：{title}

只回傳 JSON 物件，不要 markdown fence，格式：
{{"title": "標題", "body_md": "完整 markdown 內文", "summary": "50 字以內摘要"}}

【用戶內容】
{sources}
"""


async def revise_text(content: str, instruction: str) -> str:
    """依指示修改一段 markdown，回傳修改後全文。"""
    prompt = _REVISE_PROMPT.format(instruction=instruction, content=(content or "")[:32000])
    return await _llm_call(prompt)


async def generate_report_body(title: str, source_texts: list[str]) -> dict:
    """從來源內容重新生成報告。回傳 {title, body_md, summary}。"""
    sources = "\n\n---\n\n".join(source_texts)[:32000]
    prompt = _REPORT_PROMPT.format(title=title, sources=sources)
    raw = await _llm_call(prompt)
    try:
        data = _parse_json(raw)
    except Exception:
        return {"title": title, "body_md": raw, "summary": None}
    return {
        "title": data.get("title") or title,
        "body_md": data.get("body_md") or "",
        "summary": data.get("summary"),
    }
