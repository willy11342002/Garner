"""C — 報告窗口：根據 B 查出的知識內容加工，新增／修改 AI 報告，並擁有報告的查詢功能。

只看事件敘述 + 上一窗口（通常是 B）傳來的 context，看不到對話歷史。
"""
from typing import Awaitable, Callable

from ..emit import emit
from ._loop import run_window_loop

ReportExecutor = Callable[[str, dict], Awaitable[dict]]

_SYSTEM = """\
你是「報告窗口」，負責根據提供的知識內容產出或修改 AI 報告（指南／清單／彙整），並能查詢既有報告。

規則：
- 若「上一個窗口傳來的結果」裡已有可用的知識內容，直接用那些內容產出，不要反問主題
- 若完全沒有任何可用知識內容、也無法從事件本身判斷要寫什麼，呼叫 report_missing_info 說明缺什麼
- 事件提到「之前的報告」「上次的報告」或要修改既有報告：先呼叫 search_reports 找到 id，再呼叫 revise_report；不要新建
- create_report 只在事件明確要求「產出」新報告時呼叫，一輪事件只建一份
- content 用 markdown 格式撰寫，可自由使用標題、段落、列表、粗體
- 只能引用提供的知識內容，不要憑空捏造
"""

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_report",
            "description": "根據提供的知識內容，產出一份 AI 報告（規劃／指南／清單／彙整）。只在事件明確要求產出內容時呼叫。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "報告標題（繁體中文，簡潔有力）"},
                    "content": {"type": "string", "description": "完整內容，使用 markdown 格式"},
                    "summary": {"type": "string", "description": "50 字以內的內容摘要"},
                },
                "required": ["title", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "revise_report",
            "description": "修改一份既有的 AI 報告。report_id 用 search_reports 查到的 id。",
            "parameters": {
                "type": "object",
                "properties": {
                    "report_id": {"type": "string", "description": "要修改的報告 id"},
                    "instruction": {"type": "string", "description": "修改指示，例如「改短一點」「語氣正式些」"},
                },
                "required": ["report_id", "instruction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_reports",
            "description": "語意搜尋用戶已建立的 AI 報告。事件提到「之前做的某個報告」或要修改報告時，先用此工具查出 report_id。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "查詢描述，例如「大阪旅遊指南」；留空則列最近幾筆"},
                    "limit": {"type": "integer", "description": "回傳筆數，預設 5"},
                },
            },
        },
    },
]


async def run_report_window(
    event: str, context: dict | None, executor: ReportExecutor
) -> dict:
    created_report: dict | None = None
    revised: dict | None = None
    found_reports: list[dict] | None = None

    async def dispatch(name: str, args: dict) -> dict:
        nonlocal created_report, revised, found_reports
        emit("tool_call", {"name": name, **args})
        result = await executor(name, args)

        if name == "create_report":
            draft = result.get("draft")
            if draft:
                created_report = draft
                emit("report_draft", draft)
                tool_result_data = {"tool": name, "created": True, "report_id": draft["id"], "title": draft["title"]}
            else:
                tool_result_data = {"tool": name, "created": False}
        elif name == "revise_report":
            revised = result
            tool_result_data = {"tool": name, "revised": bool(result.get("ok")), "report_id": result.get("report_id")}
        elif name == "search_reports":
            found_reports = result
            tool_result_data = {"tool": name, "count": len(result), "reports": result}
        else:
            tool_result_data = {"tool": name}

        emit("tool_result", tool_result_data)
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
    return {"created_report": created_report, "revised": revised, "found_reports": found_reports}
