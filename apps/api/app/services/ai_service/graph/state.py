"""GraphState — 分層 chat 架構（A 監督者 + B/C/D 窗口）的共用狀態。

只放可序列化資料；db / user_id / background_tasks / 各窗口 executor 一律走
RunnableConfig["configurable"]，不進 state（LangGraph 慣例，也避免 state 帶不可序列化物件）。

sources / process_log 的累積（seen_ids / all_sources / process_steps）不放在這裡 ——
那是 chat_service.py 透過 closure 累積的 session 狀態（跟現有 agentic_chat_stream 的作法一致），
graph 本身只管「派工給哪個窗口、拿到什麼、要不要收工」。
"""
from typing import TypedDict


class GraphState(TypedDict):
    # A（監督者）自己的原生 tool-calling 對話紀錄（OpenAI-format messages，不含 system）。
    # 初始值＝跨輪對話歷史 + 本輪 user 訊息；每輪 A 呼叫／窗口回覆都會 append 上去。
    messages: list[dict]

    context_summary: str | None

    round: int
    max_rounds: int

    # 本輪 A 剛決定要派工的目標與參數；由 supervisor 節點寫入，由條件邊讀取路由。
    dispatch_target: str | None  # "knowledge" | "report" | "trip" | None（None＝收工）
    dispatch_tool_call_id: str | None
    dispatch_event: str | None  # A 生成的獨立事件敘述（B/C/D 只看得到這個，看不到 messages）
    dispatch_context: dict | None  # 最近一個窗口回傳的原始結構化結果（原封不動，不摘要改寫），自動轉發給下一個窗口

    # 收工時的最終回覆文字。
    final_reply: str
    finished: bool
