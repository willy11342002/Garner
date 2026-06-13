# Landmark Detection & Map View — 規格文件

> Map View 的前置條件。從 Instagram Reels / YouTube Shorts 的 metadata 與 AI 分析中抽取地標，存入 DB 後供地圖 Tab 呈現。

---

## 背景與目標

使用者收藏大量景點推薦類 Reels / Shorts，希望能在首頁 Map View 看到「我存了哪裡的資訊」。一支影片可能提及多個景點，每個景點都應在地圖上獨立標記。

---

## 地標資料來源

### 優先順序

```
1. IG metadata（raw_data.locationName）  →  最可靠，使用者自己打的
2. AI 從 combined text 抽取              →  補充，成本為零（已有 analyze_content 步驟）
```

### 各平台說明

| 平台 | metadata 地標 | 說明 |
|------|--------------|------|
| Instagram Reels | `raw_data.locationName` / `locationId` | 有打標才有，座標 Instagram 已限制，拿不到 |
| YouTube Shorts | `raw_data.location`（極少） | 需上傳者手動標記，幾乎沒有 |
| 文章 | 無 | 僅靠 AI 抽取 |

### AI 抽取說明

現有 pipeline 在 Stage 4（Analyzing）的 `analyze_content()` 已同時接收：
- caption / description 文字
- `describe_video()` / `describe_images()` 產生的視覺理解文字

因此地標抽取可直接加入 `analyze_content()` 的輸出，**不需要額外 AI 呼叫**。

AI 抽取原則：只抽「影片/貼文中實際出現或拜訪的具體地點」，排除口頭提及但與內容地點無關的地名。

---

## 資料模型

### `content_locations` 表（已建立，migration 0037 + 0040）

```python
class ContentLocation(Base):
    __tablename__ = "content_locations"

    id: UUID (PK)
    user_item_id: UUID (FK → user_items, ON DELETE CASCADE)  # 0040 從 content_id 改為此
    name: str          # 地點名稱，如 "台北101"
    lat: float | None  # Geocoding 成功後填入
    lng: float | None
    source: str        # "metadata" | "ai"
    order_index: int   # 在影片中出現的順序（從 0 開始）
    created_at: datetime
```

> **注意**：`confirmed` 欄位已在 migration 0039 移除。

### 索引

- `(user_item_id)` — 查詢單一 item 的所有地點
- `(lat, lng)` — 地圖範圍查詢（bounding box）

---

## AI 輸出格式變更

`analyze_content()` 新增 `locations` 欄位：

```json
{
  "summary_md": "...",
  "embed_text": "...",
  "tags": [...],
  "locations": [
    { "name": "台北101", "order": 0 },
    { "name": "大安森林公園", "order": 1 },
    { "name": "饒河夜市", "order": 2 }
  ]
}
```

若無可辨識的具體地點則回傳空陣列 `[]`。

---

## Geocoding

### 服務選擇

**Google Maps Geocoding API**

- 費用：$5 / 1,000 次，內含 $200/月免費額度（≈ 40,000 次/月）
- 選擇原因：對亞洲地點、非正式地名（IG 風格）命中率顯著優於 Nominatim

### 呼叫時機

- 在 `content_locations` 寫入後非同步執行
- 每個 `name` 打一次，結果更新回 `lat` / `lng`
- Geocoding 失敗（找不到地點）：保留該筆記錄但 `lat` / `lng` 維持 `null`，不在地圖顯示

### 費用估算

個人知識庫使用情境下，每月 geocoding 次數預計遠低於 1,000 次，實際費用為零。

---

## Process Item Pipeline 變更

在現有 **Stage 4（Analyzing）** 中：

```
analyze_content(combined_text)
  舊輸出：summary_md, embed_text, tags
  新輸出：summary_md, embed_text, tags, locations ← 新增
```

Stage 4 完成後新增 geocoding 子步驟：

```
for location in locations:
    lat, lng = geocode(location.name)  # 呼叫 Google Geocoding API
    insert ContentLocation(user_item_id, name, lat, lng, source, order_index)
```

---

## API 端點

### 取得單一 item 的地點列表

```
GET /items/{item_id}/locations
```

回傳：

```json
[
  {
    "id": "uuid",
    "name": "台北101",
    "lat": 25.0339,
    "lng": 121.5645,
    "source": "ai",
    "confirmed": false,
    "order_index": 0
  }
]
```

### 確認 / 刪除地點

```
PATCH /items/{item_id}/locations/{location_id}   # 確認（confirmed=true）或修改名稱
DELETE /items/{item_id}/locations/{location_id}  # 刪除錯誤地點
```

### 地圖範圍查詢（Map View 用）

```
GET /locations?bounds={sw_lat},{sw_lng},{ne_lat},{ne_lng}&confirmed=true
```

回傳該範圍內所有地點與對應的 item 摘要，供地圖渲染使用。

---

## 前端 Map View

### 地圖套件

- **底圖**：Leaflet.js + OpenStreetMap（免費）
- **Geocoding**：Google Maps Geocoding API（後端處理，前端不接觸 API Key）

### Marker 樣式

| 狀態 | 樣式 |
|------|------|
| `confirmed=false` | 半透明 marker |
| `confirmed=true` | 實心 marker |
| 同地點多筆 item | Cluster marker，顯示數量 |

### 互動行為

- 點擊 marker → 右側抽屜顯示該地點對應的 item 卡片列表
- 同一 item 的多個地點以數字標記（1, 2, 3...），可選擇是否畫路線連線
- 地圖元件以 `<KeepAlive>` 包住，避免切換 View 時重新初始化（節省 map load 費用）

### 沒有地點資訊的 Items

不顯示於地圖，在地圖下方顯示「X 筆內容尚無地點資訊」，提供手動新增地點的入口。

---

## Tasks

### Backend

- [x] **DB Migration**：新增 `content_locations` 表與索引（migration 0037 + 0040）
- [ ] **Schema**：新增 `ContentLocationRead` Pydantic schema
- [ ] **AI**：修改 `analyze_content()` prompt，新增 `locations` 輸出欄位與 Pydantic 解析
- [ ] **Geocoding**：新增 `geocoding_service.py`，封裝 Google Maps Geocoding API 呼叫
- [ ] **Worker**：在 `process_item.py` Stage 4 後加入地點寫入與 geocoding 子步驟
- [ ] **CRUD**：新增 `crud/locations.py`（list by user_item_id、delete、bounding box query）
- [ ] **Router**：新增 `/items/{item_id}/locations` 端點（GET、PATCH、DELETE）
- [ ] **Router**：新增 `/locations` 地圖範圍查詢端點
- [ ] **Config**：新增 `GOOGLE_MAPS_API_KEY` 至 `core/config.py`

### Frontend

- [ ] **元件**：實作 `HomeMapView.vue`（取代現有空殼）
- [ ] **套件**：安裝 `leaflet` + `@vue-leaflet/vue-leaflet`
- [ ] **地圖渲染**：載入底圖、根據 API 回傳的地點資料放置 markers
- [ ] **Cluster**：同地點多筆 item 合併為 cluster marker
- [ ] **抽屜**：點擊 marker 顯示 item 卡片側邊抽屜
- [ ] **KeepAlive**：確認地圖元件被 `<KeepAlive>` 包住
- [ ] **無地點 items**：地圖下方顯示無地點資訊的 item 列表與手動新增入口
- [ ] **Marker 確認 UI**：半透明 / 實心 marker 樣式區分，提供確認與刪除操作

### 環境設定

- [ ] 申請 Google Maps Platform 帳號，啟用 Geocoding API
- [ ] GCP Console 設定 budget alert（建議上限 $1/月）
- [ ] 將 `GOOGLE_MAPS_API_KEY` 加入後端 `.env` 與部署環境變數

---

## 尚未決定的事項

- 使用者手動新增地點的 UX 流程（輸入地名 → 搜尋 → 確認？）
- 是否支援「只看已確認地點」的地圖篩選切換
- 路線連線（同一 item 的多個地點按 order_index 連線）是否預設開啟
