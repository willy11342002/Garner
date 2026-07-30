"""行程／報告頁 AI 懸浮球走完整分層 agent 的測試。

懸浮球跟 chat 現在共用同一顆引擎（chat_service.run_agent → A 監督者 → B/C/D 窗口），
差別只在多帶一個 scope（使用者正在編輯的項目）。這裡守的是統一之後最容易壞掉的幾件事：

1. scope 進得去 A 的 prompt、也轉發得到對應窗口，但**不會**轉發到別類窗口
2. 目標實體完全由程式碼決定 —— 工具簽章沒有 trip_id/report_id，模型無法指定要寫哪一份
3. 前端即時更新用的 `_` 前綴 payload 傳得到前端、但不會灌回模型脈絡
4. 前端 tool_result 的欄位契約（name / ok / _item / _deleted_id / _report）沒被改掉
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from app.services import chat_service
from app.services.ai_service import _client
from app.services.ai_service._client import user_turn
from app.services.ai_service.graph import supervisor as sup
from app.services.ai_service.graph.windows import _loop

TRIP_ID = UUID("00000000-0000-0000-0000-0000000000t1".replace("t", "a"))
REPORT_ID = UUID("00000000-0000-0000-0000-0000000000r1".replace("r", "b"))
CARD_ID = UUID("00000000-0000-0000-0000-0000000000c1".replace("c", "c"))

TRIP_SCOPE = {"kind": "trip", "id": str(TRIP_ID), "brief": "行程標題：大阪4天\n\n目前卡片：\n1. 道頓堀"}
REPORT_SCOPE = {"kind": "report", "id": str(REPORT_ID), "brief": "報告標題：京都指南\n\n目前內文：\n# 京都"}


def _part(text=None, fc=None):
    return SimpleNamespace(
        text=text,
        function_call=SimpleNamespace(name=fc[0], args=fc[1]) if fc else None,
    )


def _chunk(*parts):
    return SimpleNamespace(
        candidates=[SimpleNamespace(content=SimpleNamespace(parts=list(parts) or None))]
    )


class ScriptedGemini:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []
        self.aio = SimpleNamespace(models=SimpleNamespace(generate_content_stream=self._stream))

    async def _stream(self, **kwargs):
        self.calls.append(kwargs)
        parts = self.script.pop(0) if self.script else []

        async def gen():
            for p in parts:
                yield _chunk(p)
            yield _chunk()

        return gen()


async def _run(script, *, scope=None, scope_trip=None, scope_report_id=None, executors=None):
    """跑一次 run_agent，回傳 (SSE 字串 list, AgentRun, 假 client)。"""
    fake = ScriptedGemini(script)
    run = chat_service.AgentRun()
    execs = executors or {}
    with patch.object(_client, "_get_client", return_value=fake), \
         patch.object(chat_service, "_get_search_cutoff", new=AsyncMock(return_value=0.45)), \
         patch.object(chat_service, "_build_knowledge_executor",
                      return_value=execs.get("knowledge", AsyncMock(return_value={}))), \
         patch.object(chat_service, "_build_report_executor",
                      return_value=execs.get("report", AsyncMock(return_value={}))), \
         patch.object(chat_service, "_build_trip_executor",
                      return_value=execs.get("trip", AsyncMock(return_value={}))):
        events = [
            ev async for ev in chat_service.run_agent(
                AsyncMock(), UUID(int=1), [user_turn("把第一天改短一點")], run,
                scope=scope, scope_trip=scope_trip, scope_report_id=scope_report_id,
            )
        ]
    return events, run, fake


# ── scope 進得去 A 的 prompt ────────────────────────────────────────────────────

async def test_scope_brief_reaches_supervisor_system_prompt():
    """A 必須看得到當前狀態，否則它無從判斷該派什麼工作。"""
    _, _, fake = await _run([[_part(text="好的")]], scope=TRIP_SCOPE)

    system = fake.calls[0]["config"].system_instruction
    assert "目前正在編輯的項目" in system
    assert "大阪4天" in system and "道頓堀" in system


async def test_no_scope_leaves_prompt_unchanged():
    _, _, fake = await _run([[_part(text="好的")]])

    assert "目前正在編輯的項目" not in fake.calls[0]["config"].system_instruction


@pytest.mark.parametrize("scope, target, should_forward", [
    (TRIP_SCOPE, "trip", True),
    (REPORT_SCOPE, "report", True),
    (TRIP_SCOPE, "report", False),    # 在行程頁派工給 C，報告窗口不該拿到行程內容
    (REPORT_SCOPE, "trip", False),
    (TRIP_SCOPE, "knowledge", False),  # B 自己查，不需要 scope
])
def test_scope_only_forwards_to_matching_window(scope, target, should_forward):
    ctx = sup._resolve_dispatch_context(target, {}, [], scope)

    assert bool(ctx and ctx.get("scope")) is should_forward


def test_scope_renders_as_prose_not_json_in_window_prompt():
    """brief 是給模型讀的敘述（含換行），塞進 JSON 會被引號和 \\n 淹沒。"""
    rendered = _loop._fmt_context({"scope": TRIP_SCOPE})

    assert "【目前正在編輯的行程】" in rendered
    assert "1. 道頓堀" in rendered
    assert "\\n" not in rendered


def test_knowledge_results_still_render_as_json_alongside_scope():
    rendered = _loop._fmt_context({
        "scope": TRIP_SCOPE,
        "items": [{"id": "a", "title": "大阪美食"}],
    })

    assert "【目前正在編輯的行程】" in rendered
    assert "【上一個窗口傳來的結果】" in rendered
    assert '"大阪美食"' in rendered


# ── 目標實體由程式碼決定，模型說不上話 ─────────────────────────────────────────

def test_trip_tools_expose_no_trip_id_to_the_model():
    """卡片工具的參數裡不能有 trip_id —— 那是唯一能讓模型寫到別人資料的破口。"""
    from app.services.ai_service.graph.windows.trip import _TOOLS

    card_tools = [t for t in _TOOLS if t.name in ("add_card", "update_card", "delete_card")]
    assert len(card_tools) == 3
    for tool in card_tools:
        assert "trip_id" not in (tool.parameters.properties or {}), tool.name


def test_report_update_tool_exposes_no_report_id_to_the_model():
    from app.services.ai_service.graph.windows.report import _TOOLS

    update = next(t for t in _TOOLS if t.name == "update_report")
    assert "report_id" not in (update.parameters.properties or {})


async def test_update_card_resolves_card_no_through_the_map():
    """模型給編號，程式碼查對照表換成真正的 item_id。"""
    updated = AsyncMock(return_value={"ok": True, "title": "改過的", "_item": {"id": str(CARD_ID)}})
    scope_trip = chat_service.TripScope(trip_id=TRIP_ID, card_map={1: CARD_ID}, start_date=None)
    executor = chat_service._build_trip_executor(AsyncMock(), UUID(int=1), set(), scope_trip)

    with patch.object(chat_service.trip_service, "update_card_from_chat", new=updated):
        result = await executor("update_card", {"card_no": 1, "title": "改過的"})

    assert result["ok"] is True
    # update_card_from_chat(db, user_id, trip_id, start_date, item_id, args)
    _db, _uid, trip_id, _start, item_id, _args = updated.await_args.args
    assert (trip_id, item_id) == (TRIP_ID, CARD_ID)


@pytest.mark.parametrize("args, reason", [
    ({"card_no": 99}, "不存在的編號"),
    ({"card_no": "abc"}, "不是數字"),
    ({}, "沒給編號"),
])
async def test_update_card_rejects_unresolvable_card_no(args, reason):
    scope_trip = chat_service.TripScope(trip_id=TRIP_ID, card_map={1: CARD_ID})
    executor = chat_service._build_trip_executor(AsyncMock(), UUID(int=1), set(), scope_trip)

    result = await executor("update_card", args)

    assert result["ok"] is False, reason


async def test_card_edits_refuse_when_there_is_no_scoped_trip():
    """chat 首頁沒有 scope 時，模型不能憑空改某張卡片。"""
    executor = chat_service._build_trip_executor(AsyncMock(), UUID(int=1), set(), None)

    for tool in ("update_card", "delete_card"):
        result = await executor(tool, {"card_no": 1})
        assert result["ok"] is False, tool


async def test_update_report_refuses_when_there_is_no_scoped_report():
    executor = chat_service._build_report_executor(AsyncMock(), UUID(int=1), set(), None)

    result = await executor("update_report", {"body_md": "# 亂改"})

    assert result["ok"] is False


async def test_update_report_rejects_empty_body():
    """整篇覆寫的工具，空內文會直接清空使用者的報告。"""
    executor = chat_service._build_report_executor(AsyncMock(), UUID(int=1), set(), REPORT_ID)

    result = await executor("update_report", {"body_md": "   "})

    assert result["ok"] is False


# ── `_` 前綴 payload：給前端、不給模型 ──────────────────────────────────────────

def test_underscore_keys_are_stripped_before_feeding_the_model():
    """整張卡片／整篇報告的 JSON 很吃 token，模型接下來的判斷也用不到。"""
    visible = _loop._model_visible({
        "ok": True, "title": "道頓堀",
        "_item": {"id": "x", "note": "很長的 markdown" * 100},
    })

    assert visible == {"ok": True, "title": "道頓堀"}


async def test_card_tool_result_keeps_frontend_payload_in_the_sse_event():
    """前端靠 tool_result 的 name / ok / _item 即時改畫面，這組欄位是對外契約。"""
    import json

    trip_executor = AsyncMock(return_value={
        "ok": True, "title": "道頓堀", "_item": {"id": str(CARD_ID), "title": "道頓堀"},
    })
    events, _, _ = await _run(
        [
            [_part(fc=("dispatch_trip_desk", {"event": "加一張卡"}))],
            [_part(fc=("add_card", {"title": "道頓堀"}))],
            [],
            [_part(text="加好了")],
        ],
        scope=TRIP_SCOPE,
        scope_trip=chat_service.TripScope(trip_id=TRIP_ID, card_map={}),
        executors={"trip": trip_executor},
    )

    payloads = [
        json.loads(ev.split("data: ", 1)[1])
        for ev in events if ev.startswith("event: tool_result")
    ]
    add = next(p for p in payloads if p.get("name") == "add_card")
    assert add["ok"] is True
    assert add["_item"] == {"id": str(CARD_ID), "title": "道頓堀"}
    assert add["title"] == "道頓堀"


async def test_delete_card_tool_result_carries_deleted_id():
    import json

    trip_executor = AsyncMock(return_value={"ok": True, "_deleted_id": str(CARD_ID)})
    events, _, _ = await _run(
        [
            [_part(fc=("dispatch_trip_desk", {"event": "刪一張卡"}))],
            [_part(fc=("delete_card", {"card_no": 1}))],
            [],
            [_part(text="刪好了")],
        ],
        scope=TRIP_SCOPE,
        scope_trip=chat_service.TripScope(trip_id=TRIP_ID, card_map={1: CARD_ID}),
        executors={"trip": trip_executor},
    )

    payloads = [
        json.loads(ev.split("data: ", 1)[1])
        for ev in events if ev.startswith("event: tool_result")
    ]
    deleted = next(p for p in payloads if p.get("name") == "delete_card")
    assert deleted == {"name": "delete_card", "ok": True, "_deleted_id": str(CARD_ID)}


# ── 懸浮球入口 ─────────────────────────────────────────────────────────────────

async def test_trip_fab_yields_error_when_trip_is_not_accessible():
    from app.services import trip_service

    with patch.object(trip_service, "build_trip_scope", new=AsyncMock(return_value=None)):
        events = [
            ev async for ev in trip_service.ai_edit_trip_stream(
                AsyncMock(), UUID(int=1), TRIP_ID, "改一下"
            )
        ]

    assert events == ['event: error\ndata: {"message": "trip not found"}\n\n']


async def test_report_fab_yields_error_when_report_is_not_found():
    from app.services import report_service

    with patch.object(report_service, "build_report_scope", new=AsyncMock(return_value=None)):
        events = [
            ev async for ev in report_service.ai_edit_report_stream(
                AsyncMock(), UUID(int=1), REPORT_ID, "改一下"
            )
        ]

    assert events == ['event: error\ndata: {"message": "Report not found"}\n\n']


async def test_trip_fab_end_to_end_emits_the_events_the_frontend_expects():
    """從懸浮球入口一路跑到 SSE 輸出，斷言前端實際會收到的事件序列。

    這條蓋住整條新路徑：ai_edit_trip_stream → build_trip_scope → run_scoped_agent_stream
    → A 派工 → D 窗口 → executor → emit → SSE。
    """
    import json
    from app.services import trip_service

    scope_fixture = (TRIP_SCOPE, {1: CARD_ID}, None)
    trip_executor = AsyncMock(return_value={
        "ok": True, "title": "黑門市場", "_item": {"id": str(CARD_ID), "title": "黑門市場"},
    })
    fake = ScriptedGemini([
        [_part(fc=("dispatch_trip_desk", {"event": "在第一天加上黑門市場"}))],
        [_part(fc=("add_card", {"day": 1, "title": "黑門市場"}))],
        [],
        [_part(text="已經加上黑門市場了。")],
    ])

    with patch.object(_client, "_get_client", return_value=fake), \
         patch.object(trip_service, "build_trip_scope", new=AsyncMock(return_value=scope_fixture)), \
         patch.object(trip_service, "_get_accessible_trip", new=AsyncMock(return_value=None)), \
         patch.object(chat_service, "_get_search_cutoff", new=AsyncMock(return_value=0.45)), \
         patch.object(chat_service, "_build_trip_executor", return_value=trip_executor), \
         patch.object(chat_service, "_build_knowledge_executor", return_value=AsyncMock(return_value={})), \
         patch.object(chat_service, "_build_report_executor", return_value=AsyncMock(return_value={})):
        events = [
            ev async for ev in trip_service.ai_edit_trip_stream(
                AsyncMock(), UUID(int=1), TRIP_ID, "在第一天加上黑門市場"
            )
        ]

    parsed = [
        (ev.split("\n")[0].removeprefix("event: "), json.loads(ev.split("data: ", 1)[1]))
        for ev in events
    ]
    assert [name for name, _ in parsed] == ["tool_call", "tool_result", "delta", "done"]

    _, call = parsed[0]
    assert call == {"name": "add_card", "day": 1, "title": "黑門市場"}

    _, result = parsed[1]
    assert result["name"] == "add_card" and result["ok"] is True
    assert result["_item"]["title"] == "黑門市場"   # 前端據此即時插入卡片

    assert parsed[2][1] == {"text": "已經加上黑門市場了。"}

    # 目標行程由程式碼指定，模型只給了 day/title
    assert trip_executor.await_args.args == ("add_card", {"day": 1, "title": "黑門市場"})


async def test_fab_history_becomes_multi_turn_context():
    """懸浮球的多輪追問靠前端帶回來的純文字 history。"""
    fake = ScriptedGemini([[_part(text="好")]])
    with patch.object(_client, "_get_client", return_value=fake), \
         patch.object(chat_service, "_get_search_cutoff", new=AsyncMock(return_value=0.45)):
        [ev async for ev in chat_service.run_scoped_agent_stream(
            AsyncMock(), UUID(int=1), "那再短一點", TRIP_SCOPE,
            history=[
                {"role": "user", "content": "把第一天改短"},
                {"role": "assistant", "content": "已經改好了"},
            ],
        )]

    texts = [
        "".join(p.text or "" for p in c.parts)
        for c in fake.calls[0]["contents"]
    ]
    assert texts == ["把第一天改短", "已經改好了", "那再短一點"]
