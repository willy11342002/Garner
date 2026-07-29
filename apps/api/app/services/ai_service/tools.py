"""Generic streaming tool-calling loop for one-shot agentic tasks (e.g. trip/report AI FAB)."""
import logging

from google.genai import types

from ._client import (
    _chunk_parts,
    _sse,
    generate_stream,
    model_turn,
    tool_results,
    user_turn,
)

logger = logging.getLogger("garner.chat")


async def stream_tool_loop(
    system: str,
    user_message: str,
    tools: list[types.FunctionDeclaration],
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
    messages: list[types.Content] = []
    for turn in history or []:
        role, content = turn.get("role"), turn.get("content")
        if not content:
            continue
        if role == "user":
            messages.append(user_turn(content))
        elif role == "assistant":
            messages.append(model_turn(text=content))
    messages.append(user_turn(user_message))

    for _round in range(max_rounds):
        accumulated_text = ""
        calls: list[tuple[str, dict]] = []

        async for chunk in generate_stream(messages, system=system, tools=tools):
            for part in _chunk_parts(chunk):
                if part.text:
                    accumulated_text += part.text
                    yield _sse("delta", {"text": part.text})
                elif part.function_call:
                    fc = part.function_call
                    calls.append((fc.name, dict(fc.args or {})))

        if not calls:
            break

        messages.append(model_turn(accumulated_text or None, calls=calls))

        results: list[tuple[str, dict]] = []
        for name, args in calls:
            yield _sse("tool_call", {"name": name, **args})
            try:
                result = await execute_tool(name, args) or {}
            except Exception:
                logger.exception("stream_tool_loop tool %s failed", name)
                result = {"ok": False, "error": "tool execution failed"}
            yield _sse("tool_result", {"name": name, **result})
            # 底線開頭的 key 只給前端，不灌回模型脈絡（避免吃 token）
            results.append((name, {k: v for k, v in result.items() if not k.startswith("_")}))

        messages.append(tool_results(*results))

    yield _sse("done", {})
