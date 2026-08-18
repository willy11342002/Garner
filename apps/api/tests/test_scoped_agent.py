"""分層 agent 的能力與權限測試。

設計前提（這份檔案就是在守這件事）：
**一套 agent、一套工具、到處都一樣。** 不管使用者是從首頁 chat、行程頁懸浮球、還是
報告頁懸浮球進來，能做的事完全相同 —— D 窗口能操作任何一份行程、C 窗口能操作任何一份
報告、B 窗口只讀。

scope（使用者畫面上開著哪一份）**不是權限機制**，只是給 A 的一句提示，讓「把這個行程
改短」有所指。權限一律由資料層擋：每個寫入函式自己帶 user_id 查一次。
"""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from app.services import chat_service
from app.services.ai_service import _client
from app.services.ai_service._client import user_turn
from app.services.ai_service.graph import supervisor as sup
from app.services.ai_service.graph.windows import _loop

TRIP_ID = UUID("00000000-0000-0000-0000-00000000aaa1")
OTHER_TRIP_ID = UUID("00000000-0000-0000-0000-00000000aaa2")
REPORT_ID = UUID("00000000-0000-0000-0000-00000000bbb1")
CARD_ID = UUID("00000000-0000-0000-0000-00000000ccc1")
USER_ID = UUID(int=1)

TRIP_SCOPE = {
    "kind": "trip", "id": str(TRIP_ID),
    "brief": f"行程「大阪4天」（trip_id={TRIP_ID}）\n目前卡片：\n- 道頓堀（card_id={CARD_ID}）",
}
REPORT_SCOPE = {
    "kind": "report", "id": str(REPORT_ID),
    "brief": f"報告「京都指南」（report_id={REPORT_ID}）",
}


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


class _FakeBackgroundTasks:
    def __init__(self):
        self.tasks = []

    def add_task(self, func, *args, **kwargs):
        self.tasks.append((func, args, kwargs))


async def _run(script, *, scope=None, executors=None):
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
                AsyncMock(), USER_ID, [user_turn("把第一天改短一點")], run, scope=scope,
            )
        ]
    return events, run, fake


def _tool(module_tools, name):
    return next(t for t in module_tools if t.name == name)


def _params(tool):
    return tool.parameters.properties or {}


# ── 能力對稱：工具收 id，任何入口都能操作任何一份 ─────────────────────────────

@pytest.mark.parametrize("tool_name", ["get_trip", "add_card", "update_card", "delete_card"])
def test_every_trip_tool_takes_an_explicit_trip_id(tool_name):
    """工具收 trip_id 才可能「在任何位置都做得到同樣的事」。

    舊設計刻意不給 trip_id、只能動 scope 那一份，結果 chat 查得到行程卻改不了。
    """
    from app.services.ai_service.graph.windows.trip import _TOOLS

    tool = _tool(_TOOLS, tool_name)
    assert "trip_id" in _params(tool)
    assert "trip_id" in (tool.parameters.required or [])


@pytest.mark.parametrize("tool_name", ["update_card", "delete_card"])
def test_card_tools_take_a_real_card_id_not_a_display_index(tool_name):
    from app.services.ai_service.graph.windows.trip import _TOOLS

    tool = _tool(_TOOLS, tool_name)
    assert "card_id" in _params(tool)
    assert "card_no" not in _params(tool)


# ── 欄位對稱：能新增的欄位就一定能改回去 ───────────────────────────────────────

def test_add_card_and_update_card_expose_the_same_fields():
    """兩支工具共用 _CARD_FIELDS，欄位集合必須完全一致（除了各自的 id）。

    以前兩邊各自列欄位，結果 update 有 booked、add 有 source_item_ids，
    兩邊都沒有 end_time／kind／tags —— 使用者叫 AI 改某個欄位就是改不動。
    """
    from app.services.ai_service.graph.windows.trip import _TOOLS

    add = set(_params(_tool(_TOOLS, "add_card"))) - {"trip_id"}
    update = set(_params(_tool(_TOOLS, "update_card"))) - {"trip_id", "card_id"}

    # clear_fields 只有 update 有 —— 剛建好的卡片沒有東西可清
    assert update - add == {"clear_fields"}
    assert add - update == set()


def test_card_tools_cover_every_writable_trip_item_column():
    """工具欄位要蓋滿 TripItem 的可寫欄位，漏一個就是 AI 改不動那一格。

    刻意不開放的三個衍生欄位（lat／lng／geocoding_status）由 place_name 的背景
    geocoding 決定，模型自己填只會蓋掉正確座標。
    """
    from app.models.trip import TripItem
    from app.services.ai_service.graph.windows.trip import _CARD_FIELDS

    derived = {"lat", "lng", "geocoding_status"}
    internal = {"id", "trip_id", "user_item_id", "created_at", "updated_at"}
    writable = {c.name for c in TripItem.__table__.columns} - derived - internal

    # tags / source_item_ids 走關聯表，不是 TripItem 的欄位，但都要能改
    assert writable <= set(_CARD_FIELDS)
    assert {"tags", "source_item_ids"} <= set(_CARD_FIELDS)


@pytest.mark.parametrize("tool_name", ["get_report", "update_report"])
def test_every_report_tool_takes_an_explicit_report_id(tool_name):
    from app.services.ai_service.graph.windows.report import _TOOLS

    tool = _tool(_TOOLS, tool_name)
    assert "report_id" in _params(tool)
    assert "report_id" in (tool.parameters.required or [])


def test_knowledge_window_has_no_tool_that_modifies_existing_knowledge():
    """B 窗口只讀 —— search 查詢、save_url 新增，沒有任何改寫／刪除既有知識的工具。"""
    from app.services.ai_service.graph.windows.knowledge import _TOOLS

    names = {t.name for t in _TOOLS}
    assert names == {"search", "save_url"}


async def test_card_tools_work_without_any_scope():
    """首頁 chat（無 scope）也要能改任何一份行程 —— 這是「功能全開」的核心。"""
    updated = AsyncMock(return_value={"ok": True, "title": "改過的", "_item": {}})
    executor = chat_service._build_trip_executor(AsyncMock(), USER_ID, set())

    with patch.object(chat_service.trip_service, "update_card_from_chat", new=updated):
        result = await executor(
            "update_card",
            {"trip_id": str(OTHER_TRIP_ID), "card_id": str(CARD_ID), "title": "改過的"},
        )

    assert result["ok"] is True
    _db, _uid, trip_id, card_id, _args = updated.await_args.args
    assert (trip_id, card_id) == (OTHER_TRIP_ID, CARD_ID)


async def test_update_report_works_without_any_scope():
    updated = AsyncMock(return_value={"ok": True, "_report": {}})
    executor = chat_service._build_report_executor(AsyncMock(), USER_ID, set())

    with patch.object(chat_service.report_service, "update_report_from_chat", new=updated):
        result = await executor("update_report", {"report_id": str(REPORT_ID), "body_md": "# 新內容"})

    assert result["ok"] is True
    assert updated.await_args.args[2] == REPORT_ID


@pytest.mark.parametrize("tool, args", [
    ("get_trip", {"trip_id": "not-a-uuid"}),
    ("add_card", {"trip_id": None, "title": "x"}),
    ("update_card", {"trip_id": str(TRIP_ID), "card_id": "garbage"}),
    ("delete_card", {"card_id": str(CARD_ID)}),
])
async def test_trip_tools_reject_unparseable_ids(tool, args):
    executor = chat_service._build_trip_executor(AsyncMock(), USER_ID, set())

    result = await executor(tool, args)

    assert result["ok"] is False


# ── 權限在資料層，不在工具簽章 ─────────────────────────────────────────────────

async def test_updating_a_card_in_someone_elses_trip_is_refused():
    """模型可以送任意 trip_id，資料層要擋下來。

    _ai_update_card 原本沒有這道檢查（只有 FAB 會呼叫，端口已先驗過）。開放 trip_id
    給模型之後，少了它就是 IDOR。
    """
    from app.services import trip_service

    with patch.object(trip_service, "_get_accessible_trip", new=AsyncMock(return_value=None)):
        result = await trip_service._ai_update_card(
            AsyncMock(), USER_ID, OTHER_TRIP_ID, CARD_ID, {"title": "亂改"}
        )

    assert result == {"ok": False, "error": "trip not found"}


async def test_adding_a_card_requires_editor_not_just_membership():
    """viewer 不該能透過 AI 新增卡片，行為要跟 delete_item 一致。"""
    from app.services import trip_service

    accessible = AsyncMock(return_value=None)
    with patch.object(trip_service, "_get_accessible_trip", new=accessible):
        result = await trip_service.add_card_from_chat(
            AsyncMock(), USER_ID, TRIP_ID, {"title": "偷加的"}
        )

    assert result == {"ok": False, "error": "trip not found"}
    assert accessible.await_args.kwargs["required_role"] == "editor"


async def test_reading_someone_elses_trip_is_refused():
    from app.services import trip_service

    with patch.object(trip_service, "_get_accessible_trip", new=AsyncMock(return_value=None)):
        assert await trip_service.get_trip_detail_for_chat(
            AsyncMock(), USER_ID, OTHER_TRIP_ID
        ) is None


async def test_update_card_filters_source_ids_it_never_retrieved():
    """update_card 也要過 seen_ids 這一關 —— 以前只有 add_card 有，等於同一個漏洞的側門。"""
    updated = AsyncMock(return_value={"ok": True, "_item": {}})
    executor = chat_service._build_trip_executor(AsyncMock(), USER_ID, {CARD_ID})

    with patch.object(chat_service.trip_service, "update_card_from_chat", new=updated):
        await executor("update_card", {
            "trip_id": str(TRIP_ID), "card_id": str(CARD_ID),
            "source_item_ids": [str(CARD_ID), str(OTHER_TRIP_ID), "not-a-uuid"],
        })

    assert updated.await_args.args[4]["source_item_ids"] == [str(CARD_ID)]


async def test_card_args_without_source_ids_are_left_alone():
    """沒給 source_item_ids 就不要補空陣列 —— 資料層會把空陣列當成「清空關聯」。"""
    updated = AsyncMock(return_value={"ok": True, "_item": {}})
    executor = chat_service._build_trip_executor(AsyncMock(), USER_ID, set())

    with patch.object(chat_service.trip_service, "update_card_from_chat", new=updated):
        await executor("update_card", {
            "trip_id": str(TRIP_ID), "card_id": str(CARD_ID), "title": "改名",
        })

    assert "source_item_ids" not in updated.await_args.args[4]


# ── 欄位解析 ──────────────────────────────────────────────────────────────────

def test_card_dates_are_absolute_and_need_no_trip_level_anchor():
    """卡片日期就是卡片自己的絕對日期，不依賴 trips.start_date。

    這裡曾經有一組 day／end_day（第幾天），要拿 trips.start_date 當錨點換算 ——
    行程沒填出發日時整組靜默失效，卡片全躺在「未排程」，模型還一路回報成功。
    """
    from datetime import date
    from app.services.trip_service import _card_args_to_kwargs

    kwargs, _extras = _card_args_to_kwargs(
        {"start_date": "2026-07-28", "end_date": "2026-07-30"}
    )

    assert kwargs["start_date"] == date(2026, 7, 28)
    assert kwargs["end_date"] == date(2026, 7, 30)


# ── 卡片日期：要嘛都有、要嘛都沒有 ────────────────────────────────────────────

def test_a_lone_start_date_gets_mirrored_to_end_date():
    from datetime import date
    from app.services.trip_service import _mirror_card_dates

    kwargs = {"start_date": date(2026, 8, 22)}
    _mirror_card_dates(kwargs)

    assert kwargs["end_date"] == date(2026, 8, 22)


def test_a_lone_end_date_gets_mirrored_to_start_date():
    from datetime import date
    from app.services.trip_service import _mirror_card_dates

    kwargs = {"end_date": date(2026, 8, 22)}
    _mirror_card_dates(kwargs)

    assert kwargs["start_date"] == date(2026, 8, 22)


def test_a_real_multi_day_span_is_left_alone():
    from datetime import date
    from app.services.trip_service import _mirror_card_dates

    kwargs = {"start_date": date(2026, 8, 22), "end_date": date(2026, 8, 25)}
    _mirror_card_dates(kwargs)

    assert (kwargs["start_date"], kwargs["end_date"]) == (date(2026, 8, 22), date(2026, 8, 25))


def test_partial_update_keeps_the_existing_span():
    """住宿卡片 8/22–8/25，只改 start_date 不該把 end_date 洗掉。

    判斷要看「合併後」的狀態，不能只看這次送進來的欄位。
    """
    from datetime import date
    from types import SimpleNamespace
    from app.services.trip_service import _mirror_card_dates

    existing = SimpleNamespace(start_date=date(2026, 8, 22), end_date=date(2026, 8, 25))
    kwargs = {"start_date": date(2026, 8, 23)}
    _mirror_card_dates(kwargs, existing)

    assert "end_date" not in kwargs  # 沿用既有的 8/25


def test_clearing_only_the_end_date_shortens_to_a_single_day():
    """住宿改成只住一晚：清掉 end_date，會被補成跟 start_date 同一天，而不是變未排程。"""
    from datetime import date
    from types import SimpleNamespace
    from app.services.trip_service import _mirror_card_dates

    existing = SimpleNamespace(start_date=date(2026, 8, 22), end_date=date(2026, 8, 25))
    kwargs = {"end_date": None}
    _mirror_card_dates(kwargs, existing)

    assert kwargs["end_date"] == date(2026, 8, 22)


def test_clearing_both_dates_makes_the_card_unscheduled():
    from datetime import date
    from types import SimpleNamespace
    from app.services.trip_service import _mirror_card_dates

    existing = SimpleNamespace(start_date=date(2026, 8, 22), end_date=date(2026, 8, 22))
    kwargs = {"start_date": None, "end_date": None}
    _mirror_card_dates(kwargs, existing)

    assert kwargs == {"start_date": None, "end_date": None}


def test_a_card_with_no_dates_at_all_stays_that_way():
    from app.services.trip_service import _mirror_card_dates

    kwargs = {"title": "還沒排"}
    _mirror_card_dates(kwargs)

    assert kwargs == {"title": "還沒排"}


def test_relative_day_fields_are_gone():
    """day／end_day 不該再出現在工具簽章裡，免得模型以為還能用。"""
    from app.services.ai_service.graph.windows.trip import _CARD_FIELDS

    assert "day" not in _CARD_FIELDS
    assert "end_day" not in _CARD_FIELDS


def test_only_supplied_fields_are_written_back():
    """update_card 是部分更新：沒填的欄位不能出現在 kwargs，否則會把既有值蓋成 None。"""
    from app.services.trip_service import _card_args_to_kwargs

    kwargs, extras = _card_args_to_kwargs({"title": "新名字"})

    assert kwargs == {"title": "新名字"}
    assert extras == {}


def test_empty_values_mean_untouched_not_cleared():
    """空字串／空陣列＝模型沒有要動這個欄位，不是要清空。

    Gemini 會把宣告過的參數整組帶出來、沒話說的填 "" 或 []。曾經把那當成「清空」，
    結果模型改一張卡片就順手洗掉其他欄位——實測看到日期被清成 null 只剩時間、
    標籤整組消失。
    """
    from app.services.trip_service import _card_args_to_kwargs

    kwargs, extras = _card_args_to_kwargs({
        "title": "大阪生活今昔館", "start_time": "10:00",
        "start_date": "", "end_date": "", "end_time": "",
        "note": "", "emoji": "", "ticket_url": "", "category": "",
        "place_name": "", "tags": [], "source_item_ids": [],
    })

    assert set(kwargs) == {"title", "start_time"}
    assert extras == {}


def test_falsy_but_meaningful_values_still_count():
    """False 與 0 是有意義的值，不能被空值判斷吃掉。"""
    from app.services.trip_service import _card_args_to_kwargs

    kwargs, _extras = _card_args_to_kwargs({"booked": False, "order_index": 0})

    assert kwargs == {"booked": False, "order_index": 0.0}


def test_clear_fields_is_the_only_way_to_erase():
    from app.services.trip_service import _card_args_to_kwargs

    kwargs, extras = _card_args_to_kwargs(
        {"clear_fields": ["note", "start_date", "tags"]}
    )

    assert kwargs["note"] is None
    assert kwargs["start_date"] is None
    assert extras["tag_names"] == []


def test_unparseable_date_is_skipped_and_reported_back_to_the_model():
    """解析失敗不要靜默略過 —— 那正是「agent 說改好了、畫面沒變」的來源。"""
    from app.services.trip_service import _card_args_to_kwargs

    kwargs, extras = _card_args_to_kwargs({"start_date": "2026/07/28"})

    assert "start_date" not in kwargs
    assert any("start_date" in w for w in extras["warnings"])


async def test_reading_someone_elses_report_is_refused():
    from app.services import report_service

    with patch.object(report_service.crud_reports, "get_one", new=AsyncMock(return_value=None)):
        assert await report_service.get_report_for_chat(
            AsyncMock(), USER_ID, REPORT_ID
        ) is None


# ── scope：只是提示 ────────────────────────────────────────────────────────────

async def test_scope_brief_reaches_supervisor_system_prompt():
    _, _, fake = await _run([[_part(text="好的")]], scope=TRIP_SCOPE)

    system = fake.calls[0]["config"].system_instruction
    assert "目前正在編輯的項目" in system
    assert "大阪4天" in system and str(TRIP_ID) in system


async def test_no_scope_leaves_prompt_unchanged():
    _, _, fake = await _run([[_part(text="好的")]])

    assert "目前正在編輯的項目" not in fake.calls[0]["config"].system_instruction


@pytest.mark.parametrize("scope, target, should_forward", [
    (TRIP_SCOPE, "trip", True),
    (REPORT_SCOPE, "report", True),
    (TRIP_SCOPE, "report", False),
    (REPORT_SCOPE, "trip", False),
    (TRIP_SCOPE, "knowledge", False),
])
def test_scope_only_forwards_to_matching_window(scope, target, should_forward):
    ctx = sup._resolve_dispatch_context(target, {}, [], scope)

    assert bool(ctx and ctx.get("scope")) is should_forward


def test_scope_renders_as_prose_not_json_in_window_prompt():
    rendered = _loop._fmt_context({"scope": TRIP_SCOPE})

    assert "【目前正在編輯的行程】" in rendered
    assert "道頓堀" in rendered
    assert "\\n" not in rendered


async def test_resolve_scope_delegates_to_the_domain_service():
    from app.services import trip_service

    with patch.object(trip_service, "build_trip_scope", new=AsyncMock(return_value=TRIP_SCOPE)):
        assert await chat_service.resolve_scope(
            AsyncMock(), USER_ID, {"kind": "trip", "id": str(TRIP_ID)}
        ) == TRIP_SCOPE


@pytest.mark.parametrize("raw, why", [
    (None, "首頁 chat 沒有 scope"),
    ({}, "空 dict"),
    ({"kind": "trip"}, "缺 id"),
    ({"kind": "trip", "id": "not-a-uuid"}, "id 不是 UUID"),
    ({"kind": "什麼鬼", "id": str(TRIP_ID)}, "不認得的 kind"),
])
async def test_resolve_scope_returns_none_for_unusable_input(raw, why):
    assert await chat_service.resolve_scope(AsyncMock(), USER_ID, raw) is None, why


# ── `_` 前綴 payload：給前端、不給模型 ──────────────────────────────────────────

def test_underscore_keys_are_stripped_before_feeding_the_model():
    visible = _loop._model_visible({
        "ok": True, "title": "道頓堀",
        "_item": {"id": "x", "note": "很長的 markdown" * 100},
    })

    assert visible == {"ok": True, "title": "道頓堀"}


# ── 收尾：改過哪些行程 ─────────────────────────────────────────────────────────

def test_edited_trip_ids_collects_every_trip_the_agent_actually_touched():
    """模型一輪可能動好幾份行程，收尾不能再假設「就是使用者開著的那一份」。"""
    run = chat_service.AgentRun(process_steps=[
        {"toolCall": {"name": "add_card", "trip_id": str(TRIP_ID)}, "toolResult": {"ok": True}},
        {"toolCall": {"name": "update_card", "trip_id": str(OTHER_TRIP_ID)}, "toolResult": {"ok": True}},
        {"toolCall": {"name": "add_card", "trip_id": str(TRIP_ID)}, "toolResult": {"ok": True}},
        {"toolCall": {"name": "delete_card", "trip_id": str(TRIP_ID)}, "toolResult": {"ok": False}},
        {"toolCall": {"name": "search_trips", "query": "x"}, "toolResult": {"ok": True}},
    ])

    assert chat_service._edited_trip_ids(run) == [TRIP_ID, OTHER_TRIP_ID]


# ── 端到端 ─────────────────────────────────────────────────────────────────────

async def test_end_to_end_search_read_then_edit_a_trip_that_is_not_open():
    """完整的「查 → 讀 → 改」，而且改的**不是**使用者畫面上開著的那份。

    這正是舊設計做不到、使用者要求補上的能力。
    """
    from app.crud import chat as crud_chat
    from app.services import trip_service

    async def trip_executor(name, args):
        if name == "search_trips":
            return [{"id": str(OTHER_TRIP_ID), "title": "京都3天"}]
        if name == "get_trip":
            return {"ok": True, "id": str(OTHER_TRIP_ID), "title": "京都3天",
                    "cards": [{"card_id": str(CARD_ID), "title": "清水寺"}]}
        if name == "update_card":
            return {"ok": True, "title": "清水寺（改）", "_item": {"id": str(CARD_ID)}}
        return {}

    fake = ScriptedGemini([
        [_part(fc=("dispatch_trip_desk", {"event": "把京都行程的清水寺改一下"}))],
        [_part(fc=("search_trips", {"query": "京都"}))],
        [_part(fc=("get_trip", {"trip_id": str(OTHER_TRIP_ID)}))],
        [_part(fc=("update_card", {"trip_id": str(OTHER_TRIP_ID), "card_id": str(CARD_ID),
                                   "title": "清水寺（改）"}))],
        [],
        [_part(text="改好了。")],
    ])
    session = SimpleNamespace(messages=[], context_summary=None)
    marked = AsyncMock()

    with patch.object(_client, "_get_client", return_value=fake), \
         patch.object(trip_service, "build_trip_scope", new=AsyncMock(return_value=TRIP_SCOPE)), \
         patch.object(trip_service, "mark_ai_edited", new=marked), \
         patch.object(chat_service, "_get_search_cutoff", new=AsyncMock(return_value=0.45)), \
         patch.object(chat_service, "_build_trip_executor", return_value=trip_executor), \
         patch.object(chat_service, "_build_knowledge_executor", return_value=AsyncMock(return_value={})), \
         patch.object(chat_service, "_build_report_executor", return_value=AsyncMock(return_value={})), \
         patch.object(crud_chat, "get_session_with_messages", new=AsyncMock(return_value=session)), \
         patch.object(crud_chat, "add_message", new=AsyncMock()), \
         patch.object(crud_chat, "touch_session", new=AsyncMock()), \
         patch.object(crud_chat, "count_messages", new=AsyncMock(return_value=2)):
        events = [
            ev async for ev in chat_service.stream_reply(
                AsyncMock(), UUID(int=7), USER_ID, "把京都行程的清水寺改一下",
                _FakeBackgroundTasks(),
                scope={"kind": "trip", "id": str(TRIP_ID)},   # 畫面上開的是大阪那份
            )
        ]

    results = [
        json.loads(ev.split("data: ", 1)[1])
        for ev in events if ev.startswith("event: tool_result")
    ]
    assert [r["name"] for r in results] == ["search_trips", "get_trip", "update_card"]

    updated = results[-1]
    assert updated["ok"] is True
    assert updated["_item"] == {"id": str(CARD_ID)}   # 前端據此即時更新卡片

    # 收尾標記的是「實際被改的那份」，不是 scope 那份
    marked.assert_awaited_once()
    assert marked.await_args.args[2] == OTHER_TRIP_ID
