"""分層 chat graph（A 監督者 + B/C/D 窗口）的行為測試（重寫前的安全網）。

斷言的都是「對外可觀察的行為」——派工路由、窗口內迴圈、emit 出去的 SSE 事件、
收工條件——而不是內部訊息格式，所以原生化重寫後這些測試應該原封不動繼續通過。
"""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.ai_service import _client
from app.services.ai_service.graph import supervisor as sup


def _part(text: str | None = None, fc: tuple[str, dict] | None = None):
    return SimpleNamespace(
        text=text,
        function_call=SimpleNamespace(name=fc[0], args=fc[1]) if fc else None,
    )


def _chunk(*parts):
    return SimpleNamespace(
        candidates=[SimpleNamespace(content=SimpleNamespace(parts=list(parts) or None))]
    )


class ScriptedGemini:
    """按腳本依序回應每一次 LLM 呼叫；script[i] 是第 i 次呼叫要吐的 parts。"""

    def __init__(self, script: list[list]):
        self.script = list(script)
        self.calls: list[dict] = []
        self.aio = SimpleNamespace(models=SimpleNamespace(
            generate_content_stream=self._stream,
        ))

    async def _stream(self, **kwargs):
        self.calls.append(kwargs)
        parts = self.script.pop(0) if self.script else []

        async def gen():
            for p in parts:
                yield _chunk(p)
            yield _chunk()  # 真實串流的收尾塊：parts=None

        return gen()


def _state(messages, *, max_rounds=8):
    return {
        "messages": messages,
        "context_summary": None,
        "round": 0,
        "max_rounds": max_rounds,
        "dispatch_target": None,
        "dispatch_tool_call_id": None,
        "dispatch_event": None,
        "dispatch_context": None,
        "final_reply": "",
        "finished": False,
    }


async def _run_graph(script, *, state=None, executors=None):
    """跑完整張圖，回傳 (custom 事件 list, updates list, 假 client)。"""
    from app.services.ai_service.graph import build_graph

    fake = ScriptedGemini(script)
    cfg = {"configurable": {
        "knowledge_executor": AsyncMock(return_value={}),
        "report_executor": AsyncMock(return_value={}),
        "trip_executor": AsyncMock(return_value={}),
        **(executors or {}),
    }}
    events, updates = [], []
    with patch.object(_client, "_get_client", return_value=fake):
        async for mode, chunk in build_graph().astream(
            state or _state([{"role": "user", "content": "台北有什麼好吃的"}]),
            config=cfg,
            stream_mode=["custom", "updates"],
        ):
            (events if mode == "custom" else updates).append(chunk)
    return events, updates, fake


# ── A：收工 vs 派工 ─────────────────────────────────────────────────────────────

async def test_supervisor_answers_directly_when_no_tool_call():
    """A 沒呼叫任何 dispatch 工具 → 直接收工，文字就是最終回覆。"""
    events, updates, _ = await _run_graph([[_part(text="這超出我的服務範圍。")]])

    final = [u["supervisor"] for u in updates if "supervisor" in u][-1]
    assert final["finished"] is True
    assert final["final_reply"] == "這超出我的服務範圍。"
    assert final["dispatch_target"] is None
    assert [e["event"] for e in events] == ["delta"]


async def test_supervisor_streams_text_deltas_as_custom_events():
    """A 的文字要逐塊 emit 成 delta，前端才有逐字效果。"""
    events, _, _ = await _run_graph([[_part(text="好的"), _part(text="，我查到了")]])

    assert [e["data"]["text"] for e in events if e["event"] == "delta"] == ["好的", "，我查到了"]


@pytest.mark.parametrize("tool_name, expected_target", [
    ("dispatch_knowledge_base", "knowledge"),
    ("dispatch_report_desk", "report"),
    ("dispatch_trip_desk", "trip"),
])
async def test_supervisor_routes_each_dispatch_tool_to_its_window(tool_name, expected_target):
    _, updates, _ = await _run_graph([
        [_part(fc=(tool_name, {"event": "做某件事"}))],   # A 派工
        [],                                                # 窗口：無工具呼叫，直接結束
        [_part(text="完成")],                              # A 收工
    ])

    dispatched = [u["supervisor"] for u in updates if "supervisor" in u][0]
    assert dispatched["dispatch_target"] == expected_target
    assert dispatched["dispatch_event"] == "做某件事"
    assert expected_target in {k for u in updates for k in u}


async def test_unknown_tool_name_finishes_instead_of_hanging():
    """A 呼叫了不認得的工具名 → 當作沒派工收工，不要卡住或炸掉。"""
    _, updates, _ = await _run_graph([[_part(text="嗯", fc=None), _part(fc=("不存在的工具", {}))]])

    final = [u["supervisor"] for u in updates if "supervisor" in u][-1]
    assert final["finished"] is True
    assert final["dispatch_target"] is None


async def test_max_rounds_forces_final_answer_without_tools():
    """達到輪數上限時，這一輪不得再帶工具給模型，必須逼出純文字答案。"""
    _, updates, fake = await _run_graph(
        [[_part(text="就這樣")]],
        state=_state([{"role": "user", "content": "x"}], max_rounds=0),
    )

    assert fake.calls[0]["config"] is None or not getattr(fake.calls[0]["config"], "tools", None)
    assert [u["supervisor"] for u in updates if "supervisor" in u][-1]["finished"] is True


# ── B：窗口內迴圈 ───────────────────────────────────────────────────────────────

async def test_knowledge_window_runs_tool_then_reports_back_to_supervisor():
    """完整一輪：A 派工 → B 呼叫 search → B 收工 → A 拿到結果後給最終答案。"""
    executor = AsyncMock(return_value={
        "items": [{"id": "item-1", "title": "台北小吃", "summary": "很多攤"}],
        "chunks": [{"item_id": "item-1", "text": "夜市"}],
    })
    events, updates, _ = await _run_graph(
        [
            [_part(fc=("dispatch_knowledge_base", {"event": "查台北美食"}))],
            [_part(fc=("search", {"query": "台北美食"}))],
            [],                       # B 沒有更多工具呼叫 → 收工
            [_part(text="找到 1 筆")],
        ],
        executors={"knowledge_executor": executor},
    )

    executor.assert_awaited_once_with("search", {"query": "台北美食"})

    kinds = [e["event"] for e in events]
    assert "tool_call" in kinds and "tool_result" in kinds
    tool_result = next(e["data"] for e in events if e["event"] == "tool_result")
    assert tool_result == {
        "tool": "search",
        "count": 1,
        "titles": [{"id": "item-1", "title": "台北小吃", "summary_preview": "很多攤"}],
    }

    assert [u["supervisor"] for u in updates if "supervisor" in u][-1]["final_reply"] == "找到 1 筆"


async def test_window_reporting_missing_info_returns_needs_input_to_supervisor():
    """窗口呼叫 report_missing_info → 立刻收工，把缺什麼交回 A。"""
    _, updates, _ = await _run_graph([
        [_part(fc=("dispatch_trip_desk", {"event": "規劃行程"}))],
        [_part(fc=("report_missing_info", {"missing": "沒有出發日期"}))],
        [_part(text="請問你哪天出發？")],
    ])

    trip_update = next(u["trip"] for u in updates if "trip" in u)
    window_result = json.loads(trip_update["messages"][-1]["content"])
    assert window_result == {"status": "needs_input", "missing": "沒有出發日期"}


async def test_window_can_call_the_same_tool_across_multiple_rounds():
    """窗口可以自行多輪換角度重試，不用每次都回報 A。"""
    executor = AsyncMock(return_value={"items": [], "chunks": []})
    await _run_graph(
        [
            [_part(fc=("dispatch_knowledge_base", {"event": "查"}))],
            [_part(fc=("search", {"query": "第一種角度"}))],
            [_part(fc=("search", {"query": "第二種角度"}))],
            [],
            [_part(text="查無結果")],
        ],
        executors={"knowledge_executor": executor},
    )

    assert [c.args[1]["query"] for c in executor.await_args_list] == ["第一種角度", "第二種角度"]


# ── A 選 id、程式碼搬資料 ───────────────────────────────────────────────────────

def _history_with_knowledge(items, chunks):
    return [
        {"role": "user", "content": "查一下"},
        {
            "role": "assistant", "content": None,
            "tool_calls": [{"id": "tc1", "type": "function",
                            "function": {"name": "dispatch_knowledge_base", "arguments": "{}"}}],
        },
        {"role": "tool", "tool_call_id": "tc1",
         "content": json.dumps({"items": items, "chunks": chunks}, ensure_ascii=False)},
    ]


def test_dispatch_context_expands_selected_ids_into_full_items_and_chunks():
    """A 只給 id，程式碼負責換成完整資料；沒被選到的不得混進來。"""
    messages = _history_with_knowledge(
        items=[{"id": "a", "title": "選中"}, {"id": "b", "title": "沒選中"}],
        chunks=[{"item_id": "a", "text": "A 的內容"}, {"item_id": "b", "text": "B 的內容"}],
    )

    ctx = sup._resolve_dispatch_context("report", {"item_ids": ["a"]}, messages)

    assert ctx == {
        "items": [{"id": "a", "title": "選中"}],
        "chunks": [{"item_id": "a", "text": "A 的內容"}],
        "saved": [],
    }


def test_knowledge_index_spans_the_whole_history_and_newer_wins():
    """A 要能引用『整個對話歷史』查過的知識，同 id 以較新的一次為準。"""
    messages = (
        _history_with_knowledge(items=[{"id": "a", "title": "舊標題"}], chunks=[])
        + _history_with_knowledge(items=[{"id": "a", "title": "新標題"}], chunks=[])
    )
    # 第二組的 tool_call_id 撞名，改掉才符合真實情況
    messages[4]["tool_calls"][0]["id"] = "tc2"
    messages[5]["tool_call_id"] = "tc2"

    items_by_id, _ = sup._build_knowledge_index(messages)

    assert items_by_id == {"a": {"id": "a", "title": "新標題"}}


def test_knowledge_index_ignores_results_from_non_knowledge_windows():
    """report/trip 窗口的回傳不是知識，不能被當成可引用的 item。"""
    messages = [
        {
            "role": "assistant", "content": None,
            "tool_calls": [{"id": "tc1", "type": "function",
                            "function": {"name": "dispatch_report_desk", "arguments": "{}"}}],
        },
        {"role": "tool", "tool_call_id": "tc1",
         "content": json.dumps({"items": [{"id": "should-not-appear"}]})},
    ]

    items_by_id, chunks = sup._build_knowledge_index(messages)

    assert items_by_id == {} and chunks == []


@pytest.mark.parametrize("target, args", [
    ("knowledge", {"item_ids": ["a"]}),   # B 自己會查，不需要 context
    ("report", {}),                        # 沒選任何 id
    ("report", {"item_ids": []}),
])
def test_dispatch_context_is_none_when_not_applicable(target, args):
    messages = _history_with_knowledge(items=[{"id": "a"}], chunks=[])
    assert sup._resolve_dispatch_context(target, args, messages) is None
