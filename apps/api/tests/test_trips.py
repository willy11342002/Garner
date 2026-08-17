"""旅遊行程的 service 層測試。

trips 功能先前完全沒有測試，於是一個「新增卡片必定回 500」的 bug
（trip_service.add_item 讀了 TripItemCreate 上不存在的 tag_ids 欄位）
從功能第一版活到 2026-08 才被發現。
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.schemas.trip import TripItemCreate
from app.services import trip_service

TRIP_ID = uuid4()
USER_ID = uuid4()
ITEM_ID = uuid4()


def _fake_item():
    """夠用的 TripItem 替身：_build_item_read 只讀這些欄位。"""
    item = MagicMock()
    item.id = ITEM_ID
    item.item_tags = []
    item.user_item_id = None
    return item


async def test_add_item_does_not_touch_fields_missing_from_schema():
    """回歸測試：add_item 不可以讀 TripItemCreate 上沒有的欄位。

    原本的 `if data.tag_ids:` 會拋 AttributeError（TripItemCreate 沒有 tag_ids，
    只有 TripItemUpdate 有），而且 create_item 在那之前就 commit 了——所以卡片
    有進資料庫，但 API 回 500、前端不把它加進畫面，要重整才看得到。

    這裡刻意用真的 TripItemCreate（不是 MagicMock），MagicMock 對任何屬性都會
    回傳一個 mock，正好會把這個 bug 蓋掉。
    """
    data = TripItemCreate(title="未命名", order_index=16)
    db = AsyncMock()
    item = _fake_item()

    with (
        patch.object(trip_service, "_get_accessible_trip", new=AsyncMock(return_value=(MagicMock(), "editor"))),
        patch("app.crud.trips.create_item", new=AsyncMock(return_value=item)),
        patch("app.crud.trips.get_item", new=AsyncMock(return_value=item)),
        patch.object(trip_service, "_build_item_source_map", new=AsyncMock(return_value={})),
        patch.object(trip_service, "_build_item_read", new=MagicMock(return_value="ok")),
    ):
        result = await trip_service.add_item(db, USER_ID, TRIP_ID, data)

    assert result == "ok"


async def test_add_item_returns_none_when_not_editor():
    """viewer 或查無此行程 → 回 None，router 據此回 404。"""
    data = TripItemCreate(title="未命名")
    with patch.object(trip_service, "_get_accessible_trip", new=AsyncMock(return_value=None)):
        assert await trip_service.add_item(AsyncMock(), USER_ID, TRIP_ID, data) is None


def test_trip_item_create_has_no_tag_ids():
    """把 schema 的現況釘住。

    add_item 曾經假設 TripItemCreate 有 tag_ids。若日後真的要支援「建立時帶標籤」，
    這條測試會失敗，提醒你同時檢查 service 端有沒有一併處理，而不是讓兩邊再次不同步。
    """
    assert "tag_ids" not in TripItemCreate.model_fields
    from app.schemas.trip import TripItemUpdate
    assert "tag_ids" in TripItemUpdate.model_fields


@pytest.mark.parametrize("field", ["title", "order_index", "place_name", "lat", "lng"])
def test_add_item_reads_only_existing_schema_fields(field):
    """add_item 會讀的欄位都必須真的存在於 TripItemCreate。"""
    assert field in TripItemCreate.model_fields
