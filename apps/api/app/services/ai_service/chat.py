"""Chat session 記憶壓縮。

分層 chat 的對話流程本身在 graph/（A 監督者 + B/C/D 窗口），這裡只剩把過長的
對話歷史壓成一段摘要，供下一輪當 context 用。

原本這支還有 chat_stream / synthesize_focus / synthesize_custom / agentic_chat_stream，
都是被 graph/ 取代後留下的死碼（全 codebase 無人呼叫），已刪除。
"""
import logging

from google.genai import types

from ._client import generate, user_turn

logger = logging.getLogger("garner.chat")

_COMPRESS_SYSTEM = """\
將以下對話摘要成 3-5 句話，保留這段對話中討論的主題、用戶的關鍵問題與結論。
只保留對繼續這段對話有用的脈絡，用繁體中文輸出。
"""

_ROLE_LABEL = {"user": "用戶", "model": "助理"}


def _render(messages: list[types.Content]) -> str:
    """把對話攤平成純文字。

    只取 text part —— function call／response 那些結構化 payload 對「這段對話在談什麼」
    沒有貢獻，卻很吃 token（一次知識查詢的結果就可能上千 token）。
    """
    lines = []
    for content in messages:
        text = "".join(p.text for p in (content.parts or []) if p.text)
        if text:
            lines.append(f"{_ROLE_LABEL.get(content.role, content.role)}：{text}")
    return "\n".join(lines)


async def compress_memory(
    current_summary: str | None,
    recent_messages: list[types.Content],
) -> str:
    prompt = f"現有摘要：\n{current_summary or '（無）'}\n\n新對話：\n{_render(recent_messages)}"
    return await generate([user_turn(prompt)], system=_COMPRESS_SYSTEM)
