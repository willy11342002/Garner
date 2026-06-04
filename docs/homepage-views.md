# Homepage Views — 設計規格

> 首頁將支援三種維度觀測知識庫，透過 View Switcher 切換。本文件記錄各 View 的定義、資料來源與 UI 規格。

---

## 總體架構

首頁移除原有的 Hero Gallery（Today's Revisit + 本週趨勢兩個 slides），改為以 **View Switcher** 為核心導覽，讓使用者選擇以哪種維度瀏覽知識庫。

三種 View 共用的元素：
- Pending Review 列表（新知識待確認標籤）
- View Switcher 切換列
- 各 View 的實際內容區塊

---

## View 1 — Tag View（標籤資料夾）

**定位**：以標籤為主角的知識庫瀏覽，類似資料夾結構。

**資料來源**：現有的 `tagGroups` computed（已依 item 數量降序排列）

**UI 規格**：
- Tag 以卡片形式展示，顯示 tag 名稱、item 數量、最近新增時間
- 點擊 Tag 卡片展開該 tag 下的內容列表（horizontal scroll card row），或導向 `/app/tag/:id`
- 未分類內容（untaggedItems）放在最下方或獨立區塊
- 支援「查看全部」連結跳至 tag 頁

**現有實作**：基本邏輯已存在（tagrow + card），UI 需重新設計成更明確的「資料夾感」視覺。

---

## View 2 — Timeline View（時間軸）

**定位**：以時間順序觀測知識的積累，反映「學習歷程」或「世界事件脈絡」。

**時間維度**（兩種可切換）：
- `saved_at`：使用者儲存時間 → 反映「我的學習歷程」
- `published_at`：內容發布時間 → 反映「世界上發生的順序」（注意：並非所有 item 都有此欄位）

**排序**：API 端加上 `sort_by=saved_at|published_at`，降序（最新在上）

**UI 規格**：
- 依日期分組，每天或每週為一個區段
- 每個時間區段內列出該時間範圍的 items（card 形式或清單形式）
- 時間切換器（saved / published）放在 View Switcher 右側或 section header
- 沒有 `published_at` 的 item 在 published 模式下歸入「日期未知」分組

**技術注意**：
- `published_at` 來自 AI 解析，需確認 API 是否已支援此欄位
- 分組邏輯在前端做（依 date string group by）

---

## View 3 — Map View（地圖）

**定位**：以地理位置為主軸，瀏覽帶有地標資訊的知識內容。特別適合景點推薦、餐廳、旅遊 Reels 等地點相關內容。

**核心場景**：使用者收藏大量 Instagram Reels 的景點推薦，透過地圖一眼看出「我存了哪裡的資訊」、「某個地點有幾篇推薦」、「出發前集中查看某區域的內容」。

**資料來源**：
- Items 的地點 entity（目前 AI pipeline 尚未抽取，需新增）
- 欄位設計：`location_name`、`lat`、`lng`（從 AI 摘要中抽取，或使用者手動標記）

**UI 規格**：
- 全寬地圖（Google Maps 或 Mapbox）
- 地圖上以 pin 標記有地點資訊的 items，同一地點多筆時顯示 cluster
- 點擊 pin 展開該地點的 item 清單（側邊抽屜或 popup）
- 沒有地點資訊的 items 在地圖模式下不顯示（或在下方顯示「無地點資訊」清單）

**前置條件（尚未完成）**：
- AI pipeline 新增地點 entity 抽取
- DB 新增 `lat`、`lng`、`location_name` 欄位
- 地圖 API 整合（費用評估）

**狀態**：規劃中，待 View 1 & 2 完成後實作。

---

## UI 實作策略

### View Switcher 設計

```
[ Tags ]  [ Timeline ]  [ Map ]
```

- 放在首頁 header 區域，Pending Review 下方
- 狀態存在 URL query param：`/app?view=tags`（預設）、`/app?view=timeline`、`/app?view=map`
- 好處：瀏覽器前進後退可切換、可分享連結、刷新不掉狀態

### 元件結構

```
pages/app/index.vue          # 薄殼：讀 ?view 參數，渲染對應 View 元件
components/home/
  HomeViewSwitcher.vue       # 切換列
  HomeTagView.vue            # View 1 — Tag 資料夾
  HomeTimelineView.vue       # View 2 — 時間軸
  HomeMapView.vue            # View 3 — 地圖（placeholder 先留著）
  HomePendingSection.vue     # Pending Review（所有 View 共用）
```

### 開發順序

1. 重構 `index.vue`：移除 Hero Gallery，抽出 Pending Section 元件
2. 加入 View Switcher + URL query param 邏輯
3. 將現有 tagrow 邏輯搬進 `HomeTagView.vue` 並改版 UI
4. 實作 `HomeTimelineView.vue`（API 加排序參數）
5. `HomeMapView.vue` 先放空殼（顯示「地圖功能開發中」）
