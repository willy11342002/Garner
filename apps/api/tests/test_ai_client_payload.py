"""_client 送進 Gemini SDK 的 payload 特徵測試（重寫前的安全網）。

刻意**不**測 `_to_gemini_contents` 這個函式本身 —— 它即將被刪掉，測它等於測一個
要消失的實作細節。這裡改成斷言「最終交到 SDK 手上的 contents / config 長什麼樣」，
這個介面在「OpenAI dict → 轉換」和「直接建 types.Content」兩種寫法下都必須一致，
所以整份測試可以原封不動跨過原生化重寫，成為真正的迴歸網。

比較方式：把 contents 一律正規化成 types.Content.model_dump()。dict 形式與原生
types.Content 形式的 model_dump 結果完全相同（含 base64 編碼），故可直接比對。
"""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai import types

from app.services.ai_service import _client


# ── 測試替身 ────────────────────────────────────────────────────────────────────

def _part(text: str | None = None, fc: tuple[str, dict] | None = None):
    """做一個 SDK 串流 part 替身：text 與 function_call 恰有一個非 None。"""
    return SimpleNamespace(
        text=text,
        function_call=SimpleNamespace(name=fc[0], args=fc[1]) if fc else None,
    )


def _chunk(*parts):
    return SimpleNamespace(
        candidates=[SimpleNamespace(content=SimpleNamespace(parts=list(parts) or None))]
    )


class ScriptedGemini:
    """假的 genai client：按腳本回傳串流內容，並錄下每次呼叫的 kwargs。

    script 的每個元素代表「一次 LLM 呼叫要吐出的 parts」，元素本身是 part 的 list。
    每個 part 各自包成一個 chunk（模擬逐塊串流），最後再補一個 parts=None 的
    收尾 chunk —— 真實 Gemini 串流的最後一塊常常就是 None，_chunk_parts 必須擋住。
    """

    def __init__(self, script: list[list]):
        self.script = list(script)
        self.calls: list[dict] = []
        self.aio = SimpleNamespace(models=SimpleNamespace(
            generate_content_stream=self._stream,
            generate_content=self._once,
        ))

    async def _stream(self, **kwargs):
        self.calls.append(kwargs)
        parts = self.script.pop(0) if self.script else []

        async def gen():
            for p in parts:
                yield _chunk(p)
            yield _chunk()  # parts=None 收尾塊

        return gen()

    async def _once(self, **kwargs):
        self.calls.append(kwargs)
        parts = self.script.pop(0) if self.script else []
        return SimpleNamespace(text="".join(p.text or "" for p in parts))


def _normalize(contents) -> list[dict]:
    """把 contents（dict 或 types.Content 混雜）正規化成可比較的 dict list。"""
    out = []
    for c in contents:
        obj = types.Content.model_validate(c) if isinstance(c, dict) else c
        out.append(obj.model_dump(exclude_none=True, mode="json"))
    return out


async def _drain(agen):
    return [c async for c in agen]


# ── contents 轉換：golden payload ───────────────────────────────────────────────

async def _capture(messages, tools=None) -> tuple[list[dict], object]:
    """跑一次串流呼叫，回傳 (正規化後的 contents, config)。"""
    fake = ScriptedGemini([[_part(text="ok")]])
    with patch.object(_client, "_get_client", return_value=fake):
        await _drain(_client._gemini_generate_stream(messages, tools=tools))
    call = fake.calls[0]
    return _normalize(call["contents"]), call["config"]


async def test_system_messages_go_to_system_instruction_not_contents():
    contents, config = await _capture([
        {"role": "system", "content": "你是助理"},
        {"role": "user", "content": "哈囉"},
    ])
    assert config.system_instruction == "你是助理"
    assert contents == [{"role": "user", "parts": [{"text": "哈囉"}]}]


async def test_multiple_system_messages_are_joined():
    _, config = await _capture([
        {"role": "system", "content": "第一段"},
        {"role": "system", "content": "第二段"},
        {"role": "user", "content": "x"},
    ])
    assert config.system_instruction == "第一段\n\n第二段"


async def test_assistant_text_becomes_model_role():
    contents, _ = await _capture([
        {"role": "user", "content": "問"},
        {"role": "assistant", "content": "答"},
    ])
    assert contents == [
        {"role": "user", "parts": [{"text": "問"}]},
        {"role": "model", "parts": [{"text": "答"}]},
    ]


async def test_tool_calls_become_function_call_parts_with_decoded_args():
    """assistant.tool_calls 的 arguments 是 JSON 字串，必須解回 dict 再送出。"""
    contents, _ = await _capture([
        {"role": "user", "content": "查一下"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "c1", "type": "function",
                "function": {
                    "name": "search",
                    "arguments": json.dumps({"query": "台北美食", "limit": 6}, ensure_ascii=False),
                },
            }],
        },
    ])
    assert contents[1] == {
        "role": "model",
        "parts": [{"function_call": {"name": "search", "args": {"query": "台北美食", "limit": 6}}}],
    }


async def test_tool_result_resolves_function_name_from_tool_call_id():
    """tool 訊息只帶 tool_call_id，name 必須從先前的 assistant.tool_calls 對回來。"""
    contents, _ = await _capture([
        {"role": "user", "content": "查"},
        {
            "role": "assistant", "content": None,
            "tool_calls": [{
                "id": "c1", "type": "function",
                "function": {"name": "search", "arguments": "{}"},
            }],
        },
        {"role": "tool", "tool_call_id": "c1", "content": json.dumps({"count": 2})},
    ])
    assert contents[2] == {
        "role": "user",
        "parts": [{"function_response": {"name": "search", "response": {"count": 2}}}],
    }


async def test_multimodal_image_url_becomes_inline_data():
    """describe_images 走的路徑：data: URL → inlineData（base64 原樣搬運）。"""
    contents, _ = await _capture([{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,QUJD"}},
            {"type": "text", "text": "描述這張圖"},
        ],
    }])
    assert contents == [{
        "role": "user",
        "parts": [
            {"inline_data": {"mime_type": "image/jpeg", "data": "QUJD"}},
            {"text": "描述這張圖"},
        ],
    }]


async def test_consecutive_user_messages_are_merged_into_one_content():
    """Gemini 不接受連續同 role 的 content，相鄰 user 訊息要合併。"""
    contents, _ = await _capture([
        {"role": "user", "content": "第一句"},
        {"role": "user", "content": "第二句"},
    ])
    assert contents == [{"role": "user", "parts": [{"text": "第一句"}, {"text": "第二句"}]}]


async def test_malformed_tool_call_arguments_degrade_to_empty_args():
    contents, _ = await _capture([{
        "role": "assistant", "content": None,
        "tool_calls": [{
            "id": "c1", "type": "function",
            "function": {"name": "f", "arguments": "{不是 JSON"},
        }],
    }])
    assert contents[0]["parts"][0]["function_call"] == {"name": "f", "args": {}}


async def test_non_json_tool_result_is_wrapped_rather_than_dropped():
    contents, _ = await _capture([
        {
            "role": "assistant", "content": None,
            "tool_calls": [{"id": "c1", "type": "function",
                            "function": {"name": "f", "arguments": "{}"}}],
        },
        {"role": "tool", "tool_call_id": "c1", "content": "純文字不是 JSON"},
    ])
    assert contents[1]["parts"][0]["function_response"]["response"] == {"result": "純文字不是 JSON"}


async def test_tools_are_declared_as_function_declarations():
    _, config = await _capture(
        [{"role": "user", "content": "x"}],
        tools=[{
            "type": "function",
            "function": {
                "name": "search",
                "description": "搜尋知識庫",
                "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
            },
        }],
    )
    assert len(config.tools) == 1
    decl = config.tools[0].function_declarations[0]
    assert decl.name == "search"
    assert decl.description == "搜尋知識庫"


# ── _chunk_parts None 防護 ──────────────────────────────────────────────────────

@pytest.mark.parametrize("chunk, expected_len", [
    (SimpleNamespace(candidates=None), 0),
    (SimpleNamespace(candidates=[]), 0),
    (SimpleNamespace(candidates=[SimpleNamespace(content=None)]), 0),
    (SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=None))]), 0),
    (SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[1, 2]))]), 2),
])
def test_chunk_parts_survives_every_none_shape(chunk, expected_len):
    """Gemini 串流收尾塊常常 content.parts 是 None，每一層都要當作可能是 None。"""
    assert len(_client._chunk_parts(chunk)) == expected_len


# ── _parse_json ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw, expected", [
    ('{"a": 1}', {"a": 1}),
    ('```json\n{"a": 1}\n```', {"a": 1}),
    ('```\n{"a": 1}\n```', {"a": 1}),
])
def test_parse_json_strips_code_fences(raw, expected):
    assert _client._parse_json(raw) == expected
