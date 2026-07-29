"""_client 送進 Gemini SDK 的 payload 特徵測試。

這份測試是「OpenAI dict IR → 原生 types.Content」重寫的安全網。作法是斷言
「最終交到 SDK 手上的 contents / config 長什麼樣」，而不是測轉換函式本身。

重寫時**只有輸入側改寫**（從手刻 OpenAI dict 換成 _client 的 builder），
下面每一條的 expected 值一字未動 —— 這就是原生 builder 產生的 wire format
與舊轉換器完全等價的證據。

比較方式：contents 一律正規化成 types.Content.model_dump()。
"""
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from google.genai import types

from app.services.ai_service import _client
from app.services.ai_service._client import (
    image_part,
    model_turn,
    tool_results,
    user_turn,
)


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
    """把 contents 正規化成可比較的 dict list。

    dict 形式與原生 types.Content 形式的 model_dump 結果完全相同（含 base64 編碼），
    所以這個比較基準在重寫前後都成立。
    """
    out = []
    for c in contents:
        obj = types.Content.model_validate(c) if isinstance(c, dict) else c
        out.append(obj.model_dump(exclude_none=True, mode="json"))
    return out


async def _drain(agen):
    return [c async for c in agen]


async def _capture(contents, *, system=None, tools=None) -> tuple[list[dict], object]:
    """跑一次串流呼叫，回傳 (正規化後的 contents, config)。"""
    fake = ScriptedGemini([[_part(text="ok")]])
    with patch.object(_client, "_get_client", return_value=fake):
        await _drain(_client.generate_stream(contents, system=system, tools=tools))
    call = fake.calls[0]
    return _normalize(call["contents"]), call["config"]


# ── contents 轉換：golden payload ───────────────────────────────────────────────

async def test_system_prompt_goes_to_system_instruction_not_contents():
    contents, config = await _capture([user_turn("哈囉")], system="你是助理")

    assert config.system_instruction == "你是助理"
    assert contents == [{"role": "user", "parts": [{"text": "哈囉"}]}]


async def test_model_text_becomes_model_role():
    contents, _ = await _capture([user_turn("問"), model_turn(text="答")])

    assert contents == [
        {"role": "user", "parts": [{"text": "問"}]},
        {"role": "model", "parts": [{"text": "答"}]},
    ]


async def test_tool_calls_become_function_call_parts_with_dict_args():
    """工具參數全程保持 dict —— 不再 dumps 成 JSON 字串再 loads 回來。"""
    contents, _ = await _capture([
        user_turn("查一下"),
        model_turn(calls=[("search", {"query": "台北美食", "limit": 6})]),
    ])

    assert contents[1] == {
        "role": "model",
        "parts": [{"function_call": {"name": "search", "args": {"query": "台北美食", "limit": 6}}}],
    }


async def test_tool_result_carries_function_name_directly():
    """functionResponse 自帶 name，不需要 tool_call_id → name 的對照表。"""
    contents, _ = await _capture([
        user_turn("查"),
        model_turn(calls=[("search", {})]),
        tool_results(("search", {"count": 2})),
    ])

    assert contents[2] == {
        "role": "user",
        "parts": [{"function_response": {"name": "search", "response": {"count": 2}}}],
    }


async def test_model_turn_can_carry_text_and_calls_together():
    contents, _ = await _capture([
        model_turn(text="我查一下", calls=[("search", {"query": "x"})]),
    ])

    assert contents[0]["parts"] == [
        {"text": "我查一下"},
        {"function_call": {"name": "search", "args": {"query": "x"}}},
    ]


async def test_image_bytes_become_inline_data():
    """describe_images 走的路徑：bytes 直接進 SDK，不用先組 data: URL 再拆回來。"""
    contents, _ = await _capture([user_turn(image_part(b"ABC"), "描述這張圖")])

    assert contents == [{
        "role": "user",
        "parts": [
            {"inline_data": {"mime_type": "image/jpeg", "data": "QUJD"}},
            {"text": "描述這張圖"},
        ],
    }]


async def test_consecutive_same_role_turns_are_merged():
    """Gemini 不接受連續同 role 的 content，相鄰的要合併。"""
    contents, _ = await _capture([user_turn("第一句"), user_turn("第二句")])

    assert contents == [{"role": "user", "parts": [{"text": "第一句"}, {"text": "第二句"}]}]


async def test_empty_turns_are_dropped():
    """parts 為空的 content 會被 SDK 拒絕，送出前要濾掉。"""
    contents, _ = await _capture([user_turn("有內容"), model_turn(), user_turn("也有內容")])

    assert contents == [{"role": "user", "parts": [{"text": "有內容"}, {"text": "也有內容"}]}]


async def test_call_without_args_degrades_to_empty_args():
    contents, _ = await _capture([model_turn(calls=[("f", None)])])

    assert contents[0]["parts"][0]["function_call"] == {"name": "f", "args": {}}


async def test_tool_result_with_non_json_types_is_stringified_not_fatal():
    """UUID / datetime 這類值必須先轉成字串，否則 SDK 序列化會整條串流炸掉。

    舊的 OpenAI-dict 路徑是靠 json.dumps(default=str) 順手擋掉的，原生化後要明確補回來。
    """
    from datetime import datetime
    from decimal import Decimal
    from uuid import UUID

    contents, _ = await _capture([
        model_turn(calls=[("search", {})]),
        tool_results(("search", {
            "id": UUID("00000000-0000-0000-0000-00000000000a"),
            "saved_at": datetime(2024, 1, 1, 12, 30),
            "score": Decimal("0.5"),
            "nested": [{"item_id": UUID("00000000-0000-0000-0000-00000000000b")}],
        })),
    ])

    assert contents[1]["parts"][0]["function_response"]["response"] == {
        "id": "00000000-0000-0000-0000-00000000000a",
        "saved_at": "2024-01-01 12:30:00",
        "score": "0.5",
        "nested": [{"item_id": "00000000-0000-0000-0000-00000000000b"}],
    }


async def test_empty_string_produces_no_part():
    """空字串不能變成一個空的 text part —— 那會讓整個 content 變成無效內容。"""
    contents, _ = await _capture([user_turn(""), user_turn("有內容")])

    assert contents == [{"role": "user", "parts": [{"text": "有內容"}]}]


async def test_non_dict_tool_result_is_wrapped_rather_than_dropped():
    """工具回了 list 或字串時要包成 dict，否則 SDK 拒收。"""
    contents, _ = await _capture([
        model_turn(calls=[("f", {})]),
        tool_results(("f", "純文字不是 JSON")),
    ])

    assert contents[1]["parts"][0]["function_response"]["response"] == {"result": "純文字不是 JSON"}


async def test_tools_are_declared_as_function_declarations():
    _, config = await _capture(
        [user_turn("x")],
        tools=[types.FunctionDeclaration(
            name="search",
            description="搜尋知識庫",
            parameters={"type": "object", "properties": {"query": {"type": "string"}}},
        )],
    )

    assert len(config.tools) == 1
    decl = config.tools[0].function_declarations[0]
    assert decl.name == "search"
    assert decl.description == "搜尋知識庫"


async def test_no_system_and_no_tools_sends_no_config():
    _, config = await _capture([user_turn("x")])

    assert config is None


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


# ── 便利包裝 ────────────────────────────────────────────────────────────────────

async def test_llm_call_sends_a_single_user_turn():
    fake = ScriptedGemini([[_part(text="回覆")]])
    with patch.object(_client, "_get_client", return_value=fake):
        result = await _client._llm_call("這是 prompt")

    assert result == "回覆"
    assert _normalize(fake.calls[0]["contents"]) == [
        {"role": "user", "parts": [{"text": "這是 prompt"}]}
    ]
