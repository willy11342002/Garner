"""即時推流輔助：讓 A / B / C / D 內部（含窗口裡的工具執行過程）能在跑到一半時
就把片段送出去，不用等整個節點/窗口跑完。

用 LangGraph 的 stream_mode="custom" 機制：呼叫 get_stream_writer() 拿到的 writer
在沒有外層 astream(..., stream_mode="custom") 消費時是 no-op，可以放心呼叫。
外層（chat_service.py）用既有 _sse() 把 (event, data) 格式化成 SSE 字串，維持前端事件協議不變。
"""
from langgraph.config import get_stream_writer


def emit(event: str, data) -> None:
    writer = get_stream_writer()
    writer({"event": event, "data": data})
