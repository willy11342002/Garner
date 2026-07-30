"""B — 知識庫窗口：只負責查找（search）與存入（save_url）用戶的個人知識庫。

不做內容生成、不管報告／旅遊。只看事件敘述 + 上一窗口傳來的 context，看不到對話歷史。
底層 executor（實際 DB 查詢／embedding／建立 item）由 chat_service.py 綁定 db/user_id
等 session 狀態後傳入，本檔案只管 prompt、工具宣告、以及把過程即時推流出去。
"""
from typing import Awaitable, Callable

from google.genai import types

from ..emit import emit
from ._loop import run_window_loop

KnowledgeExecutor = Callable[[str, dict], Awaitable[dict]]

_SYSTEM = """\
你是「知識庫窗口」，只負責查找與存入用戶的個人知識庫，不做內容生成、不管報告或旅遊規劃。

規則：
- 需要查知識庫時呼叫 search，可以多次呼叫、換角度搜尋（同一主題只搜一次，換完全不同主題/角度才再查）
- search 回傳結果後，若 count > 0，代表已找到；不要為了「再詳細查」重複同一種查詢
- 只在事件明確要求「存入某個網址」時才呼叫 save_url
- 如果查無相關內容，直接完成（不呼叫更多工具），不要捏造
- 如果事件本身含糊到不知道要查什麼（既沒有主題也沒有網址），呼叫 report_missing_info 說明缺什麼
"""

_TOOLS = [
    types.FunctionDeclaration(
        name="search",
        description="搜尋用戶的個人知識庫。可以用語意查詢、或按來源類型、日期範圍過濾。可多次呼叫換角度搜尋。",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "語意搜尋描述句，完整描述想找的概念或主題（用完整句子，不要只寫關鍵字）",
                },
                "source_type": {
                    "type": "string",
                    "enum": ["youtube", "article", "ig"],
                    "description": "按來源類型過濾",
                },
                "start_date": {"type": "string", "description": "儲存日期下限，格式 YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "儲存日期上限，格式 YYYY-MM-DD"},
                "limit": {"type": "integer", "description": "回傳筆數，預設 6，最多 15"},
                "offset": {"type": "integer", "description": "跳過前 N 筆，用於換頁"},
                "item_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "直接按知識 ID 查詢（例如剛用 save_url 存入的條目）。有此參數時略過語意搜尋，直接回傳指定 ID 的知識。",
                },
            },
        },
    ),
    types.FunctionDeclaration(
        name="save_url",
        description="將一個網址（YouTube 影片、網頁文章）存入用戶的知識庫，系統會自動抓取內容、產生摘要與標籤。只在事件明確要求存入網址時呼叫。會消耗一次存入額度。",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "要存入的完整網址（https://...）"},
            },
            "required": ["url"],
        },
    ),
]


async def run_knowledge_window(
    event: str, context: dict | None, executor: KnowledgeExecutor
) -> dict:
    all_items: list[dict] = []
    all_chunks: list[dict] = []
    saved: list[dict] = []

    async def dispatch(name: str, args: dict) -> dict:
        emit("tool_call", {"name": name, **args})
        result = await executor(name, args)

        if name == "search":
            items = result.get("items", [])
            all_items.extend(items)
            all_chunks.extend(result.get("chunks", []))
            event_data = {
                "count": len(items),
                "titles": [
                    {
                        "id": it.get("id"),
                        "title": it.get("title") or it.get("url") or "",
                        "summary_preview": (it.get("summary") or "")[:200],
                    }
                    for it in items
                ],
            }
        elif name == "save_url":
            saved.append(result)
            event_data = {
                "ok": bool(result.get("ok")),
                "id": result.get("id"),
                "title": result.get("title"),
                "source_type": result.get("source_type"),
                "error": result.get("error"),
            }
        else:
            event_data = {}

        emit("tool_result", {"name": name, **event_data})
        return result

    missing = await run_window_loop(
        window_name="knowledge",
        system_prompt=_SYSTEM,
        tools=_TOOLS,
        dispatch=dispatch,
        event=event,
        context=context,
    )
    if missing:
        return {"status": "needs_input", "missing": missing}
    return {"items": all_items, "chunks": all_chunks, "saved": saved}
