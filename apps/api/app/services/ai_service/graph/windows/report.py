"""C — 報告窗口：根據 B 查出的知識內容加工，新增／修改 AI 報告，並擁有報告的查詢功能。

只看事件敘述 + 上一窗口（通常是 B）傳來的 context，看不到對話歷史。
"""
from typing import Awaitable, Callable

from google.genai import types

from ..emit import emit
from ._loop import run_window_loop

ReportExecutor = Callable[[str, dict], Awaitable[dict]]

_SYSTEM = """\
你是「報告窗口」，負責產出新的 AI 報告（指南／清單／彙整）、或改寫既有報告，並能查詢既有報告。

規則：
- 若「目前正在編輯的報告」區塊存在，代表使用者正在某一份報告的頁面上：
  用 update_report 改寫那一份，**不要呼叫 create_report**，除非事件明確要求「另外寫一份新的」
- update_report 要輸出**完整**的 markdown 全文（含所有未修改的段落），它是整篇覆寫、不是差異套用；
  在既有內文上接續修改，不要把使用者自己編輯過的內容砍掉重寫
- 若 context 裡已有可用的知識內容，直接用那些內容產出，不要反問主題
- 若完全沒有任何可用知識內容、也無法從事件本身判斷要寫什麼，呼叫 report_missing_info 說明缺什麼
- 事件提到「之前的報告」「上次的報告」而目前沒有正在編輯的報告時：先呼叫 search_reports 找出來回報，
  由上層決定下一步；你只能改寫「使用者正在編輯的」那一份
- create_report 只在事件明確要求「產出」新報告時呼叫，一輪事件只建一份
- content 用 markdown 格式撰寫，可自由使用標題、段落、列表、粗體
- 只能引用提供的知識內容，不要憑空捏造
"""

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
            "改寫使用者目前正在編輯的那份報告。body_md 必須是完整的 markdown 全文"
            "（整篇覆寫，不是差異套用），在既有內文上接續修改。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "新標題；不改標題就省略"},
                "body_md": {"type": "string", "description": "完整的 markdown 內文（含所有修改）"},
            },
            "required": ["body_md"],
        },
    ),
    types.FunctionDeclaration(
        name="search_reports",
        description="語意搜尋用戶已建立的 AI 報告。事件提到「之前做的某個報告」或要修改報告時，先用此工具查出 report_id。",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "查詢描述，例如「大阪旅遊指南」；留空則列最近幾筆"},
                "limit": {"type": "integer", "description": "回傳筆數，預設 5"},
            },
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
        ok = bool(result.get("ok"))

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
            event_data = {k: v for k, v in result.items() if k != "ok"}
        elif name == "search_reports":
            found_reports = result if isinstance(result, list) else []
            event_data = {"count": len(found_reports), "reports": found_reports}
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
