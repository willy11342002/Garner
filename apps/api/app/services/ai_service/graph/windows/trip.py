"""D — 旅遊窗口：根據 B 查出的知識內容加工，新增／修改旅遊行程，並擁有行程的查詢功能。

只看事件敘述 + 上一窗口（通常是 B）傳來的 context，看不到對話歷史。
"""
from typing import Awaitable, Callable

from google.genai import types

from ..emit import emit
from ._loop import run_window_loop

TripExecutor = Callable[[str, dict], Awaitable[dict]]

_SYSTEM = """\
你是「旅遊窗口」，負責根據提供的知識內容規劃或修改旅遊行程（trips），並能查詢既有行程。

今天日期：{today}

規則：
- 事件要「規劃行程／幾天幾夜／itinerary」時：先呼叫 create_trip 建立空行程，**create_trip 成功後立刻且連續呼叫 add_trip_card**，
  把所有卡片全部加完才算完成；不要在 add_trip_card 之間輸出大段文字，不要反問用戶，卡片才是行程的主體
- 每個景點／餐廳／交通／住宿各一張卡片，title 只放名稱、細節放 note；一天通常 3～6 張
- 跨日的卡片（住宿連住數晚、租車多日、多日票券）用 end_day 標出結束日：例如「前 3 天住 A 飯店」，day=1、end_day=3；別把同一間飯店每天各建一張
- 若「上一個窗口傳來的結果」裡有知識內容，且某張卡片的地點與某筆知識的「地點」相符，務必用 add_trip_card 的
  source_item_ids 帶上那筆知識的 id，讓卡片連回對應知識；沒有相符的就留空
- 事件提到「之前的行程」「上次的行程」或要修改既有行程：先呼叫 search_trips 找到 id，再呼叫 revise_trip；不要新建
- 若事件缺少關鍵資訊（例如沒有出發日期、沒有天數、沒有目的地），呼叫 report_missing_info 說明缺什麼，不要自己亂猜
"""

_TOOLS = [
    types.FunctionDeclaration(
        name="create_trip",
        description="建立一份『空的』旅遊行程，只設定標題與日期。先呼叫這個，再用 add_trip_card 逐張填卡片。",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "行程標題（繁體中文，例如「大阪4天3夜自由行」）"},
                "summary": {"type": "string", "description": "50 字以內的行程摘要"},
                "start_date": {"type": "string", "description": "出發日期 YYYY-MM-DD。只要事件有提到出發時間就務必推算並帶上，卡片才能正確排到每一天。"},
                "end_date": {"type": "string", "description": "回程日期 YYYY-MM-DD（依天數推算）"},
            },
            "required": ["title"],
        },
    ),
    types.FunctionDeclaration(
        name="add_trip_card",
        description="對先前 create_trip 建立的行程新增『一張』卡片（單一景點／餐廳／交通／住宿）。需要幾個點就呼叫幾次。",
        parameters={
            "type": "object",
            "properties": {
                "day": {"type": "integer", "description": "第幾天，從 1 開始"},
                "end_day": {"type": "integer", "description": "跨日卡片的結束日（含當天，從 1 開始）。單日項目不用填。"},
                "title": {"type": "string", "maxLength": 30, "description": "卡片名稱：單一景點／餐廳／活動名稱，簡短（≤20 字）"},
                "place_name": {"type": "string", "description": "純地點名稱（含城市），用於地圖定位。只放地名，不要放網址。"},
                "category": {"type": "string", "enum": ["景點", "美食", "交通", "住宿"], "description": "分類，可選"},
                "emoji": {"type": "string", "description": "代表性 emoji，可選"},
                "start_time": {"type": "string", "description": "建議時間 HH:MM，可選"},
                "note": {"type": "string", "description": "這張卡片的細節說明，用 markdown 格式撰寫。整段敘述放這裡，不要放進 title。"},
                "source_item_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "這張卡片對應的知識 id 陣列，依地點對應。沒有相符的知識就留空。",
                },
            },
            "required": ["day", "title"],
        },
    ),
    types.FunctionDeclaration(
        name="search_trips",
        description="語意搜尋用戶已建立的旅遊行程。事件提到「之前規劃的某個行程」或要修改行程時，先用此工具查出 trip_id。",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "查詢描述，例如「東京4天」；留空則列最近幾筆"},
                "limit": {"type": "integer", "description": "回傳筆數，預設 5"},
            },
        },
    ),
    types.FunctionDeclaration(
        name="revise_trip",
        description="依指示修改一份既有旅遊行程（新增、修改或刪除卡片）。trip_id 用 search_trips 查到的 id。",
        parameters={
            "type": "object",
            "properties": {
                "trip_id": {"type": "string", "description": "要修改的行程 id"},
                "instruction": {"type": "string", "description": "修改指示，例如「第一天改成先去淺草」"},
            },
            "required": ["trip_id", "instruction"],
        },
    ),
]


async def run_trip_window(
    event: str, context: dict | None, executor: TripExecutor
) -> dict:
    import datetime as _dt

    created_trip: dict | None = None
    cards_added = 0
    revised: dict | None = None
    found_trips: list[dict] | None = None

    async def dispatch(name: str, args: dict) -> dict:
        nonlocal created_trip, cards_added, revised, found_trips
        emit("tool_call", {"name": name, **args})
        result = await executor(name, args)

        if name == "create_trip":
            draft = result.get("draft")
            if draft:
                created_trip = draft
                emit("trip_draft", draft)
                tool_result_data = {"tool": name, "created": True, "trip_id": draft["id"], "title": draft["title"]}
            else:
                tool_result_data = {"tool": name, "created": False}
        elif name == "add_trip_card":
            if result.get("ok"):
                cards_added += 1
            tool_result_data = {"tool": name, "ok": bool(result.get("ok")), "title": result.get("title")}
        elif name == "search_trips":
            found_trips = result
            tool_result_data = {"tool": name, "count": len(result), "trips": result}
        elif name == "revise_trip":
            revised = result
            tool_result_data = {"tool": name, "ok": result is not None, **(result or {})}
        else:
            tool_result_data = {"tool": name}

        emit("tool_result", tool_result_data)
        return result

    missing = await run_window_loop(
        window_name="trip",
        system_prompt=_SYSTEM.format(today=_dt.date.today().isoformat()),
        tools=_TOOLS,
        dispatch=dispatch,
        event=event,
        context=context,
    )
    if missing:
        return {"status": "needs_input", "missing": missing}
    return {
        "created_trip": created_trip,
        "cards_added": cards_added,
        "revised": revised,
        "found_trips": found_trips,
    }
