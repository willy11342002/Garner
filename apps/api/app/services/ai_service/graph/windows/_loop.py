"""B/C/D 窗口共用的內部迴圈骨架。

一顆 LLM + 一組工具，只看 event（獨立事件敘述）與 context（前一窗口傳來的原始結構化
結果），完全看不到對話歷史。可自行多次呼叫底層工具換角度重試，不用每次都回報 A；
真的做不下去時呼叫 report_missing_info 立刻收工，把「缺什麼」交回給呼叫端。

各窗口（knowledge / report / trip）自己的 dispatch() 負責：呼叫實際 domain executor、
把過程用 emit() 即時推流出去（tool_call / tool_result / report_draft / trip_draft 等），
本檔案只管迴圈機制本身，不知道任何 domain 細節。
"""
import json
import logging
from typing import Awaitable, Callable

from google.genai import types

from ..._client import _chunk_parts, generate_stream, model_turn, tool_results, user_turn

logger = logging.getLogger("garner.chat")

Dispatch = Callable[[str, dict], Awaitable[dict]]


def _model_visible(result):
    """濾掉工具結果中底線開頭的 key。

    那些是給前端做即時畫面更新的完整物件（`_item` 整張卡片、`_report` 整篇報告），
    模型不需要看 —— 灌回脈絡只會吃掉大量 token，而且模型接著要做的判斷用不到。
    """
    if not isinstance(result, dict):
        return result
    return {k: v for k, v in result.items() if not k.startswith("_")}

MISSING_INFO_TOOL = types.FunctionDeclaration(
    name="report_missing_info",
    description=(
        "當這個事件缺少必要資訊、無法繼續執行時呼叫，說明缺什麼；"
        "呼叫後這個窗口立刻結束，把缺什麼回報給上層決定下一步（問用戶／轉發查詢／自行推斷）。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "missing": {"type": "string", "description": "缺什麼資訊的簡短說明"},
        },
        "required": ["missing"],
    },
)


_SCOPE_HEADING = {
    "trip": "【目前正在編輯的行程】",
    "report": "【目前正在編輯的報告】",
}


def _fmt_context(context: dict | None) -> str:
    """把 context 轉成 system prompt 的附加區塊。

    scope（使用者正在編輯的項目）單獨拉出來用純文字呈現 —— 它的 brief 是給人／模型讀的
    敘述（行程的卡片清單、報告的 markdown 全文），塞進 JSON 會被引號和 \\n 淹沒。
    其餘（B 查到的 items/chunks）維持 JSON，結構化資料本來就該保留結構。
    """
    if not context:
        return ""

    out = ""
    scope = context.get("scope")
    if scope:
        heading = _SCOPE_HEADING.get(scope.get("kind"), "【目前正在編輯的項目】")
        out += f"\n\n{heading}\n{scope.get('brief') or '（無法取得當前狀態）'}"

    rest = {k: v for k, v in context.items() if k != "scope"}
    if rest:
        out += "\n\n【上一個窗口傳來的結果】\n" + json.dumps(rest, ensure_ascii=False, indent=2)
    return out


async def run_window_loop(
    *,
    window_name: str,
    system_prompt: str,
    tools: list[types.FunctionDeclaration],
    dispatch: Dispatch,
    event: str,
    context: dict | None,
    max_rounds: int = 6,
) -> str | None:
    """執行一輪窗口內迴圈。

    回傳 report_missing_info 帶的 missing 字串（窗口決定做不下去）；
    正常完成（無更多工具呼叫或達輪數上限）回傳 None，最終結果由呼叫端自己的
    累積變數（closure）組裝。
    """
    full_tools = tools + [MISSING_INFO_TOOL]
    system = system_prompt + _fmt_context(context)
    messages: list[types.Content] = [user_turn(event)]

    for _round in range(max_rounds):
        calls: list[tuple[str, dict]] = []
        text = ""

        async for chunk in generate_stream(messages, system=system, tools=full_tools):
            for part in _chunk_parts(chunk):
                if part.text:
                    text += part.text
                elif part.function_call:
                    fc = part.function_call
                    calls.append((fc.name, dict(fc.args or {})))

        if not calls:
            logger.debug("window %s finished (round %d, no more tool calls)", window_name, _round + 1)
            return None

        messages.append(model_turn(text or None, calls=calls))

        results: list[tuple[str, dict]] = []
        for name, args in calls:
            if name == "report_missing_info":
                return args.get("missing") or "缺少必要資訊"
            results.append((name, _model_visible(await dispatch(name, args))))

        messages.append(tool_results(*results))

    logger.debug("window %s hit max_rounds=%d without finishing", window_name, max_rounds)
    return None
