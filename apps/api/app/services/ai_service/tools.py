"""Generic streaming tool-calling loop for one-shot agentic tasks (e.g. trip/report AI FAB)."""
import json
import logging

from ._client import _gemini_generate_stream, _oi_tools_to_sdk, _to_gemini_contents, _sse, _make_config, _get_client, _llm

logger = logging.getLogger("garner.chat")


async def stream_tool_loop(
    system: str,
    user_message: str,
    tools: list[dict],
    execute_tool,
    max_rounds: int = 12,
    history: list[dict] | None = None,
):
    """通用、串流的 native tool-calling 迴圈，yield SSE 字串。

    給「逐動作即時反映到畫面」的一次性 agentic 任務用（例如 trips/report 的 AI 修改懸浮球）。
    工具結果中以底線開頭的 key（例如 _item）只回傳給前端、不灌回模型脈絡（避免吃 token）。
    history 為先前的純文字對話（[{role, content}]），讓多輪追問有記憶。

    Emits: delta | tool_call | tool_result | done
    """
    messages: list[dict] = [{"role": "system", "content": system}]
    for turn in history or []:
        role = turn.get("role")
        content = turn.get("content")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})

    for _round in range(max_rounds):
        accumulated_text = ""
        tool_calls_list: list[dict] = []

        async for chunk in _gemini_generate_stream(messages, tools=tools):
            for part in (chunk.candidates[0].content.parts if chunk.candidates else []):
                if part.text:
                    accumulated_text += part.text
                    yield _sse("delta", {"text": part.text})
                elif part.function_call:
                    fc = part.function_call
                    tool_calls_list.append({"name": fc.name, "args": dict(fc.args or {})})

        if not tool_calls_list:
            break

        assistant_msg: dict = {"role": "assistant", "content": accumulated_text or None, "tool_calls": []}
        for i, tc in enumerate(tool_calls_list):
            assistant_msg["tool_calls"].append({
                "id": f"call_{_round}_{i}",
                "type": "function",
                "function": {"name": tc["name"], "arguments": json.dumps(tc["args"], ensure_ascii=False)},
            })
        messages.append(assistant_msg)

        for i, tc in enumerate(tool_calls_list):
            name = tc["name"]
            args = tc["args"]
            tc_id = f"call_{_round}_{i}"
            yield _sse("tool_call", {"name": name, **args})
            try:
                result = await execute_tool(name, args) or {}
            except Exception:
                logger.exception("stream_tool_loop tool %s failed", name)
                result = {"ok": False, "error": "tool execution failed"}
            yield _sse("tool_result", {"name": name, **result})
            model_result = {k: v for k, v in result.items() if not k.startswith("_")}
            messages.append({
                "role": "tool",
                "tool_call_id": tc_id,
                "content": json.dumps(model_result, ensure_ascii=False),
            })

    yield _sse("done", {})
