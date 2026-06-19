"""Knowledge chain analysis — hop-level and full-chain synthesis."""
from ._client import _gemini_call, _parse_json

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
    raw = await _gemini_call([
        {"role": "system", "content": _HOP_SYSTEM},
        {"role": "user", "content": prompt},
    ], timeout=60)
    return _parse_json(raw)


async def analyze_full_chain(items: list[dict]) -> str:
    items_text = "\n".join(
        f"[{i+1}] {it['title'] or '(無標題)'}：{it['summary'] or '(無摘要)'}"
        for i, it in enumerate(items)
    )
    prompt = _CHAIN_TEMPLATE.format(items=items_text)
    return await _gemini_call([
        {"role": "system", "content": _CHAIN_SYSTEM},
        {"role": "user", "content": prompt},
    ], timeout=60)
