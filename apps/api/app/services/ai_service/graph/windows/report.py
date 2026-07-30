"""C — 報告窗口：查詢、新增、改寫使用者的任何一份 AI 報告。

只看事件敘述 + 上一窗口（通常是 B）傳來的 context，看不到對話歷史。

【能改哪一份？任何一份】
工具全部收 report_id，能力不因入口而異 —— 從首頁 chat 進來、或從報告頁的 AI 懸浮球
進來，做得到的事完全一樣。context["scope"] 只是「使用者畫面上開著哪一份」的提示，
**不是權限機制**；權限由 crud_reports.get_one(db, user_id, ...) 在資料層擋。
"""
from typing import Awaitable, Callable

from google.genai import types

from ..emit import emit
from ._loop import run_window_loop

ReportExecutor = Callable[[str, dict], Awaitable[dict]]

_SYSTEM = """\
你是「報告窗口」，負責查詢、產出、改寫用戶的 AI 報告（指南／清單／彙整）。你可以操作用戶的**任何一份**報告。

要改既有報告時的固定順序：
1. 不知道是哪一份 → search_reports 找出 report_id（「目前正在編輯的報告」區塊已經給了 report_id 的話就直接用，不用再查）
2. get_report 讀出全文
3. update_report 帶上 report_id 與改寫後的完整內文

其他規則：
- update_report 要輸出**完整**的 markdown 全文（含所有未修改的段落），它是整篇覆寫、不是差異套用；
  一定要先 get_report 看過現況再改，在既有內文上接續修改，不要把使用者自己編輯過的內容砍掉重寫
- 若「目前正在編輯的報告」區塊存在，代表使用者正看著那一份：預設就改那一份，
  **不要呼叫 create_report**，除非事件明確要求「另外寫一份新的」
- 若 context 裡已有可用的知識內容，直接用那些內容產出，不要反問主題
- 若完全沒有任何可用知識內容、也無法從事件本身判斷要寫什麼，呼叫 report_missing_info 說明缺什麼
- create_report 只在事件明確要求「產出」新報告時呼叫，一輪事件只建一份
- content 用 markdown 格式撰寫，可自由使用標題、段落、列表、粗體
- 只能用 search_reports／get_report／create_report 實際拿到的 report_id，不要自己編
- 只能引用提供的知識內容，不要憑空捏造
"""

_REPORT_ID_PARAM = {"type": "string", "description": "要操作的報告 id（來自 search_reports／get_report／create_report）"}

_TOOLS = [
    types.FunctionDeclaration(
        name="create_report",
        description="根據提供的知識內容，產出一份 AI 報告（規劃／指南／清單／彙整）。只在事件明確要求產出內容時呼叫。",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "報告標題（繁體中文，簡潔有力）"},
                "content": {"type": "string", "description": "完整內容，使用 markdown 格式"},
                "summary": {"type": "string", "description": "50 字以內的內容摘要"},
            },
            "required": ["title", "content"],
        },
    ),
    types.FunctionDeclaration(
        name="update_report",
        description=(
            "改寫一份既有報告。body_md 必須是完整的 markdown 全文（整篇覆寫，不是差異套用），"
            "所以要先 get_report 讀過現況再改。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "report_id": _REPORT_ID_PARAM,
                "title": {"type": "string", "description": "新標題；不改標題就省略"},
                "body_md": {"type": "string", "description": "完整的 markdown 內文（含所有修改）"},
            },
            "required": ["report_id", "body_md"],
        },
    ),
    types.FunctionDeclaration(
        name="search_reports",
        description="語意搜尋用戶已建立的 AI 報告，取得 report_id。要改某一份既有報告時的第一步。",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "查詢描述，例如「大阪旅遊指南」；留空則列最近幾筆"},
                "limit": {"type": "integer", "description": "回傳筆數，預設 5"},
            },
        },
    ),
    types.FunctionDeclaration(
        name="get_report",
        description="讀出一份報告的完整內文。update_report 是整篇覆寫，改之前必須先呼叫這個。",
        parameters={
            "type": "object",
            "properties": {"report_id": _REPORT_ID_PARAM},
            "required": ["report_id"],
        },
    ),
]


async def run_report_window(
    event: str, context: dict | None, executor: ReportExecutor
) -> dict:
    created_report: dict | None = None
    updated = False
    found_reports: list[dict] | None = None

    async def dispatch(name: str, args: dict) -> dict:
        nonlocal created_report, updated, found_reports
        emit("tool_call", {"name": name, **args})
        result = await executor(name, args)
        # search_reports 回的是 list，其餘是 dict —— 別假設一定有 .get
        ok = bool(result.get("ok")) if isinstance(result, dict) else bool(result)

        if name == "create_report":
            draft = result.get("draft")
            if draft:
                created_report = draft
                emit("report_draft", draft)
                event_data = {"created": True, "report_id": draft["id"], "title": draft["title"]}
            else:
                event_data = {"created": False}
        elif name == "update_report":
            updated = updated or ok
            # _report 原樣帶給前端做即時畫面更新；run_window_loop 會在灌回模型脈絡前
            # 把底線開頭的 key 濾掉（整篇報告 JSON 很吃 token）
            event_data = {k: v for k, v in result.items() if k != "ok"} if isinstance(result, dict) else {}
        elif name == "search_reports":
            found_reports = result if isinstance(result, list) else []
            event_data = {"count": len(found_reports), "reports": found_reports}
        elif name == "get_report" and isinstance(result, dict):
            event_data = {"title": result.get("title")}
        else:
            event_data = {}

        emit("tool_result", {"name": name, "ok": ok, **event_data})
        return result

    missing = await run_window_loop(
        window_name="report",
        system_prompt=_SYSTEM,
        tools=_TOOLS,
        dispatch=dispatch,
        event=event,
        context=context,
    )
    if missing:
        return {"status": "needs_input", "missing": missing}
    return {"created_report": created_report, "updated": updated, "found_reports": found_reports}
