"""D — 旅遊窗口：查詢、新增、修改使用者的任何一份旅遊行程。

只看事件敘述 + 上一窗口（通常是 B）傳來的 context，看不到對話歷史。

【能改哪一份？任何一份】
工具全部收 trip_id / card_id，能力不因入口而異 —— 從首頁 chat 進來、或從行程頁的
AI 懸浮球進來，做得到的事完全一樣。context["scope"] 只是「使用者畫面上開著哪一份」
的提示，讓「把這個行程改短」有所指，**不是權限機制**。

權限在資料層擋：每個寫入函式都自己用 user_id 查一次
（_get_accessible_trip(required_role="editor")），模型給別人的 trip_id 就是查不到。
"""
from typing import Awaitable, Callable

from google.genai import types

from ..emit import emit
from ._loop import run_window_loop

TripExecutor = Callable[[str, dict], Awaitable[dict]]

_SYSTEM = """\
你是「旅遊窗口」，負責查詢、規劃、修改用戶的旅遊行程（trips）。你可以操作用戶的**任何一份**行程。

今天日期：{today}

要改既有行程時的固定順序：
1. 不知道是哪一份 → search_trips 找出 trip_id（「目前正在編輯的行程」區塊已經給了 trip_id 的話就直接用，不用再查）
2. 要動卡片 → 先 get_trip 讀出該行程的卡片清單與各張的 card_id
3. 再用 add_card／update_card／delete_card，帶上 trip_id（改卡片還要 card_id）

其他規則：
- 要規劃**新**行程（「幫我排幾天幾夜」「規劃一趟…」）時：先呼叫 create_trip 建立空行程，
  **create_trip 成功後立刻且連續呼叫 add_card**（用回傳的 trip_id），把所有卡片全部加完才算完成；
  不要在 add_card 之間輸出大段文字，不要反問用戶，卡片才是行程的主體
- 若「目前正在編輯的行程」區塊存在，代表使用者正看著那一份：預設就改那一份，
  **不要呼叫 create_trip**，除非事件明確要求「另外開一份新的」
- update_card 只填要變更的欄位，未填的保持不變
- 每個景點／餐廳／交通／住宿各一張卡片，title 只放名稱、細節放 note；一天通常 3～6 張
- 跨日的卡片（住宿連住數晚、租車多日、多日票券）用 end_day 標出結束日：例如「前 3 天住 A 飯店」，day=1、end_day=3；別把同一間飯店每天各建一張
- 若 context 裡有知識內容，且某張卡片的地點與某筆知識的「地點」相符，務必用 add_card 的
  source_item_ids 帶上那筆知識的 id，讓卡片連回對應知識；沒有相符的就留空
- 只能用 search_trips／get_trip／create_trip 實際拿到的 trip_id 與 card_id，不要自己編
- 若事件缺少關鍵資訊（例如沒有出發日期、沒有天數、沒有目的地），呼叫 report_missing_info 說明缺什麼，不要自己亂猜
"""

_TRIP_ID_PARAM = {"type": "string", "description": "要操作的行程 id（來自 search_trips／get_trip／create_trip）"}

_CARD_FIELDS = {
    "day": {"type": "integer", "description": "第幾天，從 1 開始（行程有起始日才會排到該天）"},
    "end_day": {"type": "integer", "description": "跨日卡片的結束日（含當天，從 1 開始）。單日項目不用填；住宿／租車／多日票等才填，例如住前 3 天 day=1、end_day=3"},
    "title": {"type": "string", "maxLength": 30, "description": "卡片名稱：單一景點／餐廳／活動，簡短（≤20 字）"},
    "place_name": {"type": "string", "description": "純地點名稱（含城市，例如「大阪 道頓堀」），用於地圖定位，不要放網址"},
    "category": {"type": "string", "enum": ["景點", "美食", "交通", "住宿"], "description": "分類，可選"},
    "emoji": {"type": "string", "description": "代表性 emoji，可選"},
    "start_time": {"type": "string", "description": "建議時間 HH:MM，可選"},
    "note": {"type": "string", "description": "卡片細節（玩法、交通、提醒等），markdown 格式，可選"},
    "ticket_url": {"type": "string", "description": "票券／訂位連結（完整網址），可選"},
}

_TOOLS = [
    types.FunctionDeclaration(
        name="search_trips",
        description="語意搜尋用戶已建立的旅遊行程，取得 trip_id。要改某一份既有行程時的第一步。",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "查詢描述，例如「東京4天」；留空則列最近幾筆"},
                "limit": {"type": "integer", "description": "回傳筆數，預設 5"},
            },
        },
    ),
    types.FunctionDeclaration(
        name="get_trip",
        description="讀出一份行程的完整卡片清單與各張的 card_id。要修改或刪除卡片前必須先呼叫這個。",
        parameters={
            "type": "object",
            "properties": {"trip_id": _TRIP_ID_PARAM},
            "required": ["trip_id"],
        },
    ),
    types.FunctionDeclaration(
        name="create_trip",
        description="建立一份『空的』旅遊行程，只設定標題與日期。回傳 trip_id，接著用 add_card 逐張填卡片。",
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
        name="add_card",
        description="新增『一張』卡片（單一景點／餐廳／交通／住宿）到指定行程。需要幾個點就呼叫幾次。",
        parameters={
            "type": "object",
            "properties": {
                "trip_id": _TRIP_ID_PARAM,
                **_CARD_FIELDS,
                "source_item_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "這張卡片對應的知識 id 陣列，依地點對應。沒有相符的知識就留空。",
                },
            },
            "required": ["trip_id", "title"],
        },
    ),
    types.FunctionDeclaration(
        name="update_card",
        description="修改一張既有卡片。card_id 來自 get_trip。只填要變更的欄位，未填的保持不變。",
        parameters={
            "type": "object",
            "properties": {
                "trip_id": _TRIP_ID_PARAM,
                "card_id": {"type": "string", "description": "要修改的卡片 id（來自 get_trip）"},
                **_CARD_FIELDS,
                "booked": {"type": "boolean", "description": "是否已預定票券"},
            },
            "required": ["trip_id", "card_id"],
        },
    ),
    types.FunctionDeclaration(
        name="delete_card",
        description="刪除一張既有卡片。card_id 來自 get_trip。",
        parameters={
            "type": "object",
            "properties": {
                "trip_id": _TRIP_ID_PARAM,
                "card_id": {"type": "string", "description": "要刪除的卡片 id（來自 get_trip）"},
            },
            "required": ["trip_id", "card_id"],
        },
    ),
]


async def run_trip_window(
    event: str, context: dict | None, executor: TripExecutor
) -> dict:
    import datetime as _dt

    created_trip: dict | None = None
    cards_added = 0
    cards_updated = 0
    cards_deleted = 0
    found_trips: list[dict] | None = None

    async def dispatch(name: str, args: dict) -> dict:
        nonlocal created_trip, cards_added, cards_updated, cards_deleted, found_trips
        emit("tool_call", {"name": name, **args})
        result = await executor(name, args)
        # search_trips 回的是 list，其餘是 dict —— 別假設一定有 .get
        ok = bool(result.get("ok")) if isinstance(result, dict) else bool(result)

        if name == "create_trip":
            draft = result.get("draft")
            if draft:
                created_trip = draft
                emit("trip_draft", draft)
                event_data = {"created": True, "trip_id": draft["id"], "title": draft["title"]}
            else:
                event_data = {"created": False}
        elif name in ("add_card", "update_card", "delete_card"):
            if ok:
                if name == "add_card":
                    cards_added += 1
                elif name == "update_card":
                    cards_updated += 1
                else:
                    cards_deleted += 1
            # _item / _deleted_id 原樣帶給前端做即時畫面更新；run_window_loop 會在
            # 灌回模型脈絡前把底線開頭的 key 濾掉（整張卡片的 JSON 很吃 token）
            event_data = {k: v for k, v in result.items() if k != "ok"} if isinstance(result, dict) else {}
        elif name == "search_trips":
            found_trips = result if isinstance(result, list) else []
            event_data = {"count": len(found_trips), "trips": found_trips}
        elif name == "get_trip" and isinstance(result, dict):
            event_data = {"title": result.get("title"), "count": len(result.get("cards") or [])}
        else:
            event_data = {}

        emit("tool_result", {"name": name, "ok": ok, **event_data})
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
        "cards_updated": cards_updated,
        "cards_deleted": cards_deleted,
        "found_trips": found_trips,
    }
