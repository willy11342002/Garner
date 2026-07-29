"""A — 對外窗口／監督者。

持有完整對話歷史，跟用戶對話；自己不查資料、不寫報告、不規劃行程，只能把工作派給
B（知識庫）／C（報告）／D（旅遊）其中一個窗口，一次一個、多輪循序，直到判斷可以收工。

B/C/D 各自是完整的多步驟 sub-agent（見 windows/），只看得到 A 給的 event 敘述，
看不到這裡的 messages（對話歷史）。

派給 report/trip 時要帶的知識內容，走「A 選、程式碼搬」的分工：A 綜合『整個對話歷史』
（不只最近一輪，見 chat_service._build_history 會把每一輪查過的完整結果都留著）判斷
哪些先前查到的知識 id 真正有用，只把 id 填進 dispatch_report_desk/dispatch_trip_desk 的
item_ids 參數；實際把這些 id 換成完整資料（items/chunks，欄位不裁切、不摘要）這件事
由 _build_knowledge_index() 在程式碼裡做，不經過 LLM retype，避免失真。
"""
import datetime as _dt
import logging

from google.genai import types
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from .._client import _chunk_parts, generate_stream, model_turn, tool_results
from .emit import emit
from .state import GraphState
from .windows import run_knowledge_window, run_report_window, run_trip_window

logger = logging.getLogger("garner.chat")

_SUPERVISOR_SYSTEM = """\
你是 Garner 知識助理的對外窗口。用戶把網頁文章和 YouTube 影片存在個人知識庫裡。

你自己不會直接查資料、寫報告或規劃行程 —— 你只能把工作「派給」底下三個窗口，各自完成後把結果回報給你：
- dispatch_knowledge_base：查找或存入知識庫內容
- dispatch_report_desk：產出或修改 AI 報告（指南／清單／彙整），也能查詢既有報告
- dispatch_trip_desk：規劃或修改旅遊行程，也能查詢既有行程

規則：
- 一次只能派工給一個窗口；event 要獨立自足（用完整句子描述要做什麼），因為該窗口看不到對話歷史，只看得到你給的 event 文字
- 派給 dispatch_report_desk／dispatch_trip_desk、且這次事件需要知識庫內容佐證時：
  先綜合檢視「整個對話歷史」中所有 dispatch_knowledge_base 查到的知識項目（不是只看最近一輪），
  篩選出跟這次事件真正相關、有用的知識 id，填進 item_ids（只列有用的，不相關的不要列；
  資料本身的完整內容由系統自動帶給對應窗口，你不用、也不要在 event 裡覆述查到的內容）
- 如果目前為止都沒查到任何相關知識、或現有的都不足以回答這次事件，先派給 dispatch_knowledge_base
  （針對這次事件本身組一個新的查詢，不要假設之前查過的還適用），拿到新結果後，再派給對應窗口並帶上新查到的 item_ids
- 純粹修改或查詢既有報告／行程本身（例如「把上次的行程改短一點」「查一下我之前做的某份報告」），
  不需要新的知識庫佐證時，item_ids 可以留空，直接派給 dispatch_report_desk／dispatch_trip_desk
  （C／D 自己有 search_reports／search_trips 可以查既有項目）
- 窗口回傳 {"status": "needs_input", "missing": "..."} 代表它做不下去了，你要判斷：
  - 缺的是只有用戶才知道的資訊（例如出發日期、具體偏好、要修改哪一個既有項目）→ 直接用文字回覆詢問用戶，不要再派工，也不要說「請稍候」之類的話
  - 缺的是知識庫裡可能有的資料 → 派給 dispatch_knowledge_base 補查（針對這次事件組新查詢），查到後再派回原本的窗口並帶上新查到的 item_ids
  - 缺的資訊你能合理推斷（例如常識性預設值）→ 自己補上細節，重新組一個更完整的 event 再派給原本的窗口
- 如果問題超出知識庫範圍（一般編程問題、常識問答、數學計算、創意寫作、角色扮演等），直接回覆
  「我只能幫你整理和探索你的知識庫內容，這個問題超出我的服務範圍。」不要派工，不得在任何情況下繞過此限制
- 不管任何時候，只要還有事情要做（要派工），就直接呼叫對應的 dispatch 工具；絕對不要先用文字說
  「好的，我來處理」「請稍候，我正在為你生成」之類的話再結束這一輪——文字回覆只在你真正決定收工、
  把最終答案交給用戶時才輸出。沒有實際完成事情之前，不要輸出任何暗示已經在做或已經做完的文字
- 全部完成後，用繁體中文簡潔回答用戶，不要過度列舉；只輸出你自己的回覆，不要模擬用戶的後續回應
"""

_ITEM_IDS_PARAM = {
    "type": "array",
    "items": {"type": "string"},
    "description": "從對話歷史中先前查到的知識庫內容裡，篩選出跟這次事件真正相關、有用的知識 id；只列有用的，不相關的不要列。若目前沒有相關內容，留空並改派給 dispatch_knowledge_base 先查。",
}

_KNOWLEDGE_TOOL = "dispatch_knowledge_base"

_DISPATCH_TOOLS = [
    types.FunctionDeclaration(
        name=_KNOWLEDGE_TOOL,
        description="派工給知識庫窗口：查找或存入用戶的個人知識庫內容。",
        parameters={
            "type": "object",
            "properties": {
                "event": {"type": "string", "description": "獨立、完整描述要查什麼或要存什麼網址的事件敘述"},
            },
            "required": ["event"],
        },
    ),
    types.FunctionDeclaration(
        name="dispatch_report_desk",
        description="派工給報告窗口：產出或修改 AI 報告，或查詢既有報告。",
        parameters={
            "type": "object",
            "properties": {
                "event": {"type": "string", "description": "獨立、完整描述要產出／修改／查詢什麼報告的事件敘述"},
                "item_ids": _ITEM_IDS_PARAM,
            },
            "required": ["event"],
        },
    ),
    types.FunctionDeclaration(
        name="dispatch_trip_desk",
        description="派工給旅遊窗口：規劃或修改旅遊行程，或查詢既有行程。",
        parameters={
            "type": "object",
            "properties": {
                "event": {"type": "string", "description": "獨立、完整描述要規劃／修改／查詢什麼行程的事件敘述"},
                "item_ids": _ITEM_IDS_PARAM,
            },
            "required": ["event"],
        },
    ),
]

_DISPATCH_TARGET = {
    _KNOWLEDGE_TOOL: "knowledge",
    "dispatch_report_desk": "report",
    "dispatch_trip_desk": "trip",
}


def _build_knowledge_index(
    messages: list[types.Content],
) -> tuple[dict[str, dict], list[dict]]:
    """掃過『整個對話歷史』（不只最近一輪），把每一次 dispatch_knowledge_base 查到的
    items（依 id 建索引，同 id 以較新的一次覆蓋）與 chunks 都收集起來，供 A 篩選出的
    item_ids 換成完整、未經摘要裁切的原始資料。

    Gemini 的 functionResponse 自帶工具名，所以這裡直接認 name 就好，不必像 OpenAI
    格式那樣先建一張 tool_call_id → name 的對照表再回查。
    """
    items_by_id: dict[str, dict] = {}
    all_chunks: list[dict] = []
    for content in messages:
        for part in content.parts or []:
            fr = part.function_response
            if fr is None or fr.name != _KNOWLEDGE_TOOL:
                continue
            data = fr.response
            if not isinstance(data, dict):
                continue
            for it in data.get("items") or []:
                if it.get("id"):
                    items_by_id[it["id"]] = it
            all_chunks.extend(data.get("chunks") or [])
    return items_by_id, all_chunks


def _resolve_dispatch_context(
    target: str, args: dict, messages: list[types.Content]
) -> dict | None:
    """把 A 選出的 item_ids 換成完整資料（items/chunks，欄位不裁切），純程式碼處理，
    不經過 LLM retype。knowledge 目標不需要 context（B 自己查）。"""
    if target not in ("report", "trip"):
        return None
    selected = [i for i in (args.get("item_ids") or []) if isinstance(i, str)]
    if not selected:
        return None
    items_by_id, all_chunks = _build_knowledge_index(messages)
    selected_set = set(selected)
    return {
        "items": [items_by_id[i] for i in selected if i in items_by_id],
        "chunks": [c for c in all_chunks if c.get("item_id") in selected_set],
        "saved": [],
    }


def _system_prompt(context_summary: str | None) -> str:
    today = _dt.date.today().isoformat()
    system = _SUPERVISOR_SYSTEM + f"\n今天日期：{today}"
    if context_summary:
        system += f"\n\n【對話摘要（早期）】\n{context_summary}"
    return system


async def _supervisor_node(state: GraphState, config: RunnableConfig) -> dict:
    system = _system_prompt(state.get("context_summary"))
    round_ = state["round"]
    forced_final = round_ >= state["max_rounds"]

    tools = None if forced_final else _DISPATCH_TOOLS

    text = ""
    tool_calls_list: list[tuple[str, dict]] = []
    async for chunk in generate_stream(state["messages"], system=system, tools=tools):
        for part in _chunk_parts(chunk):
            if part.text:
                text += part.text
                emit("delta", {"text": part.text})
            elif part.function_call:
                fc = part.function_call
                tool_calls_list.append((fc.name, dict(fc.args or {})))

    if forced_final or not tool_calls_list:
        logger.debug(
            "supervisor final answer (round %d, forced=%s, len=%d)",
            round_ + 1, forced_final, len(text),
        )
        return {"final_reply": text, "finished": True, "dispatch_target": None}

    # prompt 已規範一次只派一個窗口；這裡只取第一個 tool call 以防模型多開
    tool_name, args = tool_calls_list[0]
    target = _DISPATCH_TARGET.get(tool_name)
    if target is None:
        # 模型呼叫了不認得的名字，當作沒有派工，直接用已產生的文字收尾
        return {"final_reply": text, "finished": True, "dispatch_target": None}

    # A 只決定「選哪些 id」；把 id 換成完整 items/chunks 這件事在程式碼裡做，不經過 LLM
    dispatch_context = _resolve_dispatch_context(target, args, state["messages"])

    return {
        "messages": state["messages"] + [model_turn(text or None, calls=[(tool_name, args)])],
        "round": round_ + 1,
        "dispatch_target": target,
        "dispatch_tool_name": tool_name,
        "dispatch_event": args.get("event", ""),
        "dispatch_context": dispatch_context,
    }


def _route(state: GraphState) -> str:
    target = state.get("dispatch_target")
    if target in ("knowledge", "report", "trip"):
        return target
    return END


def _after_window(state: GraphState, result: dict) -> dict:
    """窗口跑完，把結果當成 tool 回應接回 A 的 messages。

    dispatch_context 不在這裡設——它只在 _supervisor_node 決定下一次派工時，
    依 A 選的 item_ids 重新解析（見 _resolve_dispatch_context），所以這裡刻意不寫，
    避免留著一個下一輪馬上會被蓋掉、看起來卻像有作用的欄位。
    """
    return {
        "messages": state["messages"] + [tool_results((state["dispatch_tool_name"], result))],
        "window_result": result,
        "dispatch_target": None,
    }


async def _knowledge_node(state: GraphState, config: RunnableConfig) -> dict:
    executor = config["configurable"]["knowledge_executor"]
    result = await run_knowledge_window(state.get("dispatch_event") or "", state.get("dispatch_context"), executor)
    return _after_window(state, result)


async def _report_node(state: GraphState, config: RunnableConfig) -> dict:
    executor = config["configurable"]["report_executor"]
    result = await run_report_window(state.get("dispatch_event") or "", state.get("dispatch_context"), executor)
    return _after_window(state, result)


async def _trip_node(state: GraphState, config: RunnableConfig) -> dict:
    executor = config["configurable"]["trip_executor"]
    result = await run_trip_window(state.get("dispatch_event") or "", state.get("dispatch_context"), executor)
    return _after_window(state, result)


def build_graph() -> CompiledStateGraph:
    graph = StateGraph(GraphState)
    graph.add_node("supervisor", _supervisor_node)
    graph.add_node("knowledge", _knowledge_node)
    graph.add_node("report", _report_node)
    graph.add_node("trip", _trip_node)

    graph.set_entry_point("supervisor")
    graph.add_conditional_edges(
        "supervisor", _route,
        {"knowledge": "knowledge", "report": "report", "trip": "trip", END: END},
    )
    graph.add_edge("knowledge", "supervisor")
    graph.add_edge("report", "supervisor")
    graph.add_edge("trip", "supervisor")

    return graph.compile()
