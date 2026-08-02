# Garner — CLAUDE.md

> 給 Claude Code 的專案說明文件。每次開啟對話請先讀這份文件。

---

## 專案簡介

**Garner** 是一個被動建立的個人知識庫。用戶透過 Chrome Extension 一鍵收集 YouTube 影片與網頁文章，系統自動產生摘要、標籤、語意關聯，讓知識庫隨時間自動成長。

---

## Monorepo 結構

```
garner/
├── apps/
│   ├── web/          # Nuxt 3 前端
│   ├── api/          # FastAPI 後端
│   └── extension/    # Plasmo Chrome Extension
├── packages/
│   └── types/        # 共用 TypeScript 型別定義
├── CLAUDE.md
├── README.md
└── .gitignore
```

每個服務獨立管理自己的 `.env`、版本號、依賴。

---

## 開發新功能前（強制流程）

> 本專案常發生「重造已有功能」與「沒按結構/分支開」。動工前務必先跑完以下檢查：

1. **先查地圖**：在下方「現有模組地圖」找有沒有相近的 service / composable / store / component。有 → 擴充它，不要新建。
2. **再 grep 兜底**：地圖可能過期。用關鍵字搜尋確認沒有重複實作（例：做搜尋前先 `grep -ri "search" apps/`）。
3. **確認分支**：從 `develop` 開 `feature/*`，不要直接在 `main` / `develop` 上改（分支規範見 `CONTRIBUTING.md`）。
4. **遵守分層**：API 走 `router → service → crud`；Web 業務邏輯放 composable / store，不要塞進 page 或 component。
5. **樣式**：global CSS 放 `assets/css/`，`.vue` 內只允許 `scoped`。

完成後若新增了模組，**請同步更新下方「現有模組地圖」**，否則下一次又會被誤導。

---

## 現有模組地圖（動工前先掃，避免重造輪子）

> 以實際 codebase 為準（非理想範本）。一句話描述職責，找相近的就擴充。

### API services（`apps/api/app/services/`）
- `item_service` — Item 建立與處理流程主入口
- `ai_service/` — **⚠️ AI provider 是混用的，不要假設全部都是 Gemini**：LLM（chat 對話、摘要、標籤等文字生成）已全面改用 **Gemini native API**（`google-genai` SDK），但 **embedding 至今仍是 OpenRouter**（`text-embedding-3-small`，1536d，走 OpenAI-compatible SDK），兩者是不同 provider、不同 SDK、不同 API key。拆成子模組：`_client`（Gemini 呼叫基礎。對話內容一律用原生 `types.Content`/`types.Part`，**不要再手刻 OpenAI 格式的 dict**；統一用 `user_turn()`/`model_turn()`/`tool_results()`/`image_part()` 這幾個 builder 組，再交給 `generate()`/`generate_stream()`。內部有 `_llm()`/`_emb()` 兩個各自的 model getter，對應上述兩個 provider）、`chat`（只剩 `compress_memory`：session 記憶壓縮。舊的單一 agent 版 chat_stream/synthesize_*/agentic_chat_stream 已被 `graph/` 取代並刪除）、`embed`（embedding，走 OpenRouter）、`ingest`（內容分析/標籤/摘要，走 Gemini）、`report`（報告產生）、`chain`（關聯鏈分析）、`segment`（CKIP ALBERT-tiny 中文斷詞，自架非雲端 API，供 BM25 全文檢索用）、`rerank`（FlashRank 自架 cross-encoder 重排，多語模型，非雲端 API）、`graph/`（LangGraph 分層 agent：A 監督者 `supervisor.py` 派工給 `windows/knowledge.py`(B)／`windows/report.py`(C)／`windows/trip.py`(D) 三個窗口，見 `docs/agentic-chat-harness.md`。**chat 與行程／報告頁的 AI 懸浮球都走這一套，能力完全相同** —— D 窗口能操作任何一份行程、C 窗口能操作任何一份報告、B 窗口只讀。工具全部收 `trip_id`／`report_id`／`card_id`，流程是「search → get → 改」。`GraphState["scope"]`（使用者畫面上開著哪一份）**不是權限機制**，只是給 A 的提示讓指稱有對象；**權限一律在資料層擋**（每個寫入函式自己帶 user_id 查一次，`_get_accessible_trip(required_role="editor")` / `crud_reports.get_one(db, user_id, ...)`））
- `search_service` — Hybrid 語意搜尋（`/search/semantic`）：向量（pgvector cosine）+ BM25-like 全文檢索（PostgreSQL `tsvector`/`ts_rank_cd`，中文先經 `ai_service.segment` 斷詞）各取候選 → RRF 融合 → `ai_service.rerank` cross-encoder 精排 → 分頁回傳；純關鍵字搜尋（`/search/` ILIKE）維持獨立、未套用 hybrid 邏輯
- `chat_service` — Agentic chat 對話處理。**分層 agent 的唯一引擎，也是唯一入口**：`stream_reply()` → `run_agent()`（跑 A 監督者 + B/C/D 窗口）。行程／報告頁的 AI 懸浮球**沒有專屬端口或專屬引擎** —— 它打的就是 `POST /chat/sessions/{id}/messages`，body 多帶 `scope={kind,id}`，`resolve_scope()` 在後端查權限與當前狀態（不信任前端送來的任何狀態）。三個窗口的 domain executor 也在這裡綁 db/user_id 後注入
- `stream_registry` — Chat SSE 串流管理：asyncio.Queue pub/sub，解耦 POST（產生）與 GET SSE（消費），支援斷線重連
- `report_service` — AI 產出層（報告）：生成 / revise / regenerate，與知識分離、不進語料
- `place_service` — 地點實體處理
- `geocoding_service` — 地理編碼（地址 ↔ 座標）
- `billing_service` — 訂閱 / 付費額度邏輯
- `gumroad_service` — Gumroad 金流串接
- `apify_service` — 外部內容抓取（Apify）：支援 YouTube、TikTok、Facebook。YouTube 用雙 actor 並行（`asyncio.gather`）：`streamers/youtube-scraper` 抓 metadata（title/duration/thumbnail）、`streamers/youtube-video-downloader` 下載影片檔（`downloadedFileUrl`，存 KVS 約 3 天過期），兩邊 merge 進 `raw_data`；影片連結對應集中在 `yt_video_url()`（provider 共用）
- `trip_service` — 旅遊行程（trips）業務邏輯：行程 CRUD、卡片 CRUD、排序、geocoding 觸發。**沒有 AI 專屬端口** —— 行程頁懸浮球走 chat，這裡只提供 `build_trip_scope`（組當前狀態＋card_no 對照給 `chat_service.resolve_scope`）與卡片寫入 helper（由 D 窗口的 executor 呼叫）
- `quick_meta` — `POST /items/` 建立當下同步跑的輕量 metadata 前置步驟（在背景 ingest pipeline 之前跑,讓 201/203 回應時 title/thumbnail 就正確）：YouTube/TikTok 用平台原生 oEmbed；IG/Facebook 沒有可用的官方 oEmbed（需 Meta App Review），改用 `facebookexternalhit` User-Agent 直接抓貼文頁面的 og:title/og:description/og:image（IG/FB 官方連結預覽爬蟲會放行、跳過登入牆);Article 直接重用現有單次 Apify 呼叫（本來就快，同時拿到 title + 全文）。逾時/失敗回退成 title=null + API 回 203，交給背景 pipeline 補正。

### API routers（`apps/api/app/routers/`）
`items` · `articles` · `tags` · `search` · `chat` · `reports` · `auth` · `billing` · `quota` · `notifications` · `locations` · `admin` · `pat`（personal access token）· `trips` · `trip_tags`

### API crud（`apps/api/app/crud/`）
`items` · `tags` · `users` · `chat` · `reports` · `chunks` · `places` · `locations` · `notifications` · `personal_access_tokens` · `trips`

### Web composables（`apps/web/composables/`）
- `useItems` / `useItemStore` — Item 資料與狀態
- `useArticles` — 文章（知識）資料：手動新增 / 編輯，存在 user_items
- `useReports` — AI 報告（產出層）資料：列表 / 編輯 / revise / regenerate / 刪除
- `useTrips` — 旅遊行程資料：行程 / 卡片 / 標籤 CRUD 與排序
- `useSearch` — 搜尋邏輯
- `useItemModal` — Item 詳情彈窗開關
- `useChain` — 關聯鏈
- `useGlobalMap` — 地圖狀態
- `useI18nContent` — 內容多語
- `useTheme` — 主題切換
- `useToast` — 全域 toast 通知（show(message, type)；搭配根目錄 ToastList 元件顯示）

### Web stores（`apps/web/stores/`）
`useAuthStore` · `useItemStore` · `useTagStore` · `useNotificationStore`

### Web components（按功能分資料夾 `apps/web/components/`）
- `chat/` — ChatReportCard, ChatTripCard（chat 產出的旅遊行程卡，連到 trips）, SessionRow, FolderRow（資料夾列：展開/行內改名/拖曳 drop target）
- `home/` — HomeChatFab, HomeChatPanel, HomeMapView, HomeSemanticSearchView, HomeTagView, HomeViewSwitcher
- `item/` — ItemDetailModal
- `layout/` — AppNav, GuestNav, AppFooter
- `place/` — PlaceInfoPanel
- `pricing/` — PricingPlans
- `report/` — ReportAiFab（報告頁的 AI 修改懸浮球，跟 TripAiFab 一樣呼叫 chat 的端口、帶 `scope={kind:'report',id}`）
- `trip/` — TripAiFab（旅遊行程頁的 AI 修改懸浮球：可拖曳左右停靠、SSE 串流逐動作 emit card-added/updated/deleted 給頁面即時更新。**呼叫 chat 的端口**，不是專屬 API —— `POST /chat/sessions` 開一條 session、`POST /chat/sessions/{id}/messages` 帶 `scope={kind:'trip',id}`、`GET .../stream` 訂閱，跟首頁 chat 完全一樣；多輪追問靠後端 session 歷史，不自己帶 history）；TripCardEditor 支援 touch-drag-to-close 關閉 modal（向上或向下快速拖曳自動關閉）；TripShareModal（行程共用管理：成員列表、email 邀請、邀請連結產生/撤銷，owner 限定管理，viewer/editor 唯讀查看）
- 根目錄 — BaseFab（通用懸浮球容器：可拖曳、側邊停靠、badge、icon、panel slot、支援多球同時共存 multi-FAB），TiptapEditor, BubbleMenuBar, CodeBlockView, ProcessingStatus, SourceListModal（跨頁共用：列出來源收藏，點選後 emit select(id) 供開啟詳情）, ToastList（全域 toast 容器，掛在 default layout，搭配 useToast）, OfflineBanner（PWA 離線提示條，偵測 navigator.onLine 事件，掛在 default layout）

### Web utils（`apps/web/utils/`）
- `apiFetch` — 統一 API 呼叫封裝（前端 fetch 一律走這裡）
- `text` — 文字處理工具
- `itemStatus` — 判斷 item 的 ingest pipeline 是否「中斷」（`!parsed_at` 且 `updated_at` 超過 5 分鐘沒更新）或「失敗」（任一 stage `_status === 'error'`），供卡片/詳情頁顯示重試 badge

---

## Tech Stack

| 層 | 技術 |
|---|---|
| 前端 | Nuxt 3 + Vue 3 + Pinia |
| 後端 | FastAPI (Python) |
| 資料庫 | Supabase PostgreSQL + pgvector |
| 認證 | Supabase Auth（Google / GitHub SSO）|
| AI | OpenRouter → Claude（摘要）+ OpenAI text-embedding-3-small（1536d）|
| Object Storage | Cloudflare R2（縮圖快取）|
| 付費 | Gumroad |
| Extension | Plasmo（Manifest V3）|
| 部署 | Vercel（前端）/ Railway 或 Fly.io（後端）|
| 監控 | Sentry + PostHog |

> **延伸閱讀**（屬同步對象，改到相關內容時一併更新）：
> - 技術選型理由、成本、部署 → `docs/tech-decisions.md`
> - 產品定位、商業模式、整體架構 → `docs/architecture.md`
> - 最新訂閱方案與價格（單一真相來源）→ `apps/web/pages/pricing.vue`

---

## 分支策略（Git Flow）

新功能一律從 `develop` 開 `feature/*`，**不要直接在 `main` / `develop` 上改**。
完整分支規範、命名範例、Commit message 格式為單一真相來源，見 `CONTRIBUTING.md`。

---

## 版本控管

每個服務獨立維護版本號，遵循 Semantic Versioning（MAJOR.MINOR.PATCH）：

- `apps/web/package.json` → Nuxt 版本
- `apps/api/pyproject.toml` → FastAPI 版本
- `apps/extension/package.json` → Extension 版本

---

## FastAPI 最佳實踐

### 目錄結構

```
apps/api/
├── app/
│   ├── main.py              # FastAPI app 初始化、lifespan、middleware
│   ├── dependencies.py      # 共用 Depends（db session、current user 等）
│   ├── routers/             # 路由層：只做參數接收與回傳，不放業務邏輯
│   │   ├── items.py
│   │   ├── tags.py
│   │   ├── search.py
│   │   └── auth.py
│   ├── services/            # 業務邏輯層：所有核心運算放這裡（完整清單見上方「現有模組地圖」）
│   │   ├── item_service.py
│   │   ├── ai_service.py    # OpenRouter 呼叫（摘要、embedding）
│   │   ├── search_service.py
│   │   └── ...              # chat / place / geocoding / billing / gumroad / apify
│   ├── crud/                # 資料庫操作層：只做 DB 讀寫，不放業務邏輯
│   │   ├── items.py
│   │   ├── tags.py
│   │   └── users.py
│   ├── schemas/             # Pydantic models：request / response 型別定義
│   │   ├── item.py
│   │   ├── tag.py
│   │   └── user.py
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── item.py
│   │   ├── tag.py
│   │   └── user.py
│   ├── core/                # 設定、安全、常數
│   │   ├── config.py        # 讀取 .env（用 pydantic-settings）
│   │   ├── security.py      # JWT encode/decode
│   │   └── database.py      # Supabase 連線、session factory
│   └── workers/             # BackgroundTasks 的實際工作函式
│       └── process_item.py
├── tests/
│   ├── test_items.py
│   └── test_search.py
├── .env
├── pyproject.toml
└── README.md
```

### 層級規則

- **routers/** → 只做：接收參數、呼叫 service、回傳 response。禁止放 SQL 或業務邏輯。
- **services/** → 業務邏輯的唯一出口。呼叫 crud、呼叫外部 API、處理商業規則。
- **crud/** → 只做 DB 讀寫。禁止放商業判斷。
- **schemas/** → 所有 request/response 都用 Pydantic model 定義，禁止用裸 dict 回傳。
- **core/config.py** → 所有環境變數透過 `pydantic-settings` 的 `BaseSettings` 讀取，禁止在程式任何地方直接 `os.getenv()`。

### 命名規則

- 檔案：`snake_case`
- Class：`PascalCase`
- 函式 / 變數：`snake_case`
- Pydantic schema 命名：`ItemCreate`、`ItemRead`、`ItemUpdate`（動作後綴）
- Router prefix：`/items`、`/tags`

### Async 規則

- 所有 route handler 都用 `async def`
- DB 操作使用 async session（`asyncpg`）
- 若呼叫同步 SDK，用 `asyncio.to_thread()` 包起來，不阻塞 event loop

### 錯誤處理

- 使用 `HTTPException` 回傳標準錯誤
- 在 `main.py` 註冊 global exception handler 處理未預期錯誤
- OpenRouter 401 錯誤需特別捕捉（可能是服務斷線，非 auth 問題）

---

## Nuxt 3 最佳實踐

### 目錄結構

```
apps/web/
├── pages/               # file-based routing，每個 .vue 對應一個路由
│   ├── index.vue        # 首頁（/）
│   ├── app/             # 登入後的 SPA 區域（ssr: false）
│   │   ├── index.vue
│   │   └── archive.vue
├── components/          # 可重用元件（完整清單見上方「現有模組地圖」）
│   ├── home/            # 首頁各檢視（Map / SemanticSearch / Tag / Chat 等）
│   ├── item/            # Item 相關元件（ItemDetailModal 等）
│   ├── chat/            # Chat 相關元件
│   ├── place/           # 地點相關元件
│   ├── pricing/         # 付費方案元件
│   └── layout/          # Layout 元件（AppNav、AppFooter 等）
├── composables/         # 可重用邏輯（useItems、useTags、useSearch）
├── stores/              # Pinia stores
│   ├── useItemStore.ts
│   ├── useTagStore.ts
│   └── useAuthStore.ts
├── server/              # Nitro server routes（若需要 BFF 層）
│   └── api/
├── assets/
│   └── css/
│       ├── garner.css        # base：tokens、reset、nav、buttons、cards、utilities
│       ├── selbar.css        # 共用 selbar 元件
│       ├── home.css          # app/index.vue 首頁
│       └── archive.css       # app/archive.vue 封存頁
├── public/              # 不需處理的靜態資源（favicon 等）
├── plugins/             # Nuxt plugins（初始化第三方 lib）
├── middleware/          # Route middleware（auth guard 等）
├── utils/               # 純函式工具（無 Vue 依賴）
├── types/               # TypeScript 型別定義
├── nuxt.config.ts
├── .env
└── package.json
```

### 渲染模式（已確定）

```ts
// nuxt.config.ts
routeRules: {
  '/app/**': { ssr: false },
}
```

### 層級規則

- **pages/** → 只做路由進入點，業務邏輯抽到 composables 或 store。
- **composables/** → 可重用的有狀態邏輯。命名：`use` 前綴（`useItems`、`useSearch`）。
- **stores/** → 跨元件共享狀態。命名：`use` 前綴（`useItemStore`）。
- **components/** → 按功能分資料夾（`home/`、`item/`、`chat/`、`place/`、`pricing/`、`layout/`），跨功能共用的原子元件放根目錄。
- **utils/** → 純函式，不依賴 Vue 響應式，可直接 import。

### CSS 規則

- **所有 global CSS 放 `assets/css/` 下**，在 `nuxt.config.ts` 的 `css[]` 陣列引入。
- **Vue 的 `<style>` 只允許 `scoped`**（元件局部樣式）。禁止在 `.vue` 檔案內用 unscoped `<style>` 寫全域樣式。
- 跨頁共用的元件樣式（例如 `.selbar`）獨立成一支 CSS 檔案。
- 每個頁面（`app/index.vue`、`app/archive.vue` 等）有對應的 CSS 檔案（`home.css`、`archive.css`）。

### 命名規則

- 元件檔案：`PascalCase`（`ItemCard.vue`）
- composable 檔案：`camelCase`（`useItems.ts`）
- store 檔案：`camelCase`（`useItemStore.ts`）
- pages 檔案：`kebab-case` 或 `camelCase`（Nuxt 慣例）
- 動態路由：`[id].vue`、`[slug].vue`

### 資料獲取

- 使用 `useFetch` / `useAsyncData`（支援 SSR hydration）
- 避免在 `onMounted` 裡 fetch 需要 SSR 的資料
- API base URL 統一從 `useRuntimeConfig().public.apiBase` 讀取

### 環境變數

- 伺服器端變數：`NUXT_` 前綴，只在 server 讀取
- 客戶端可見變數：`NUXT_PUBLIC_` 前綴
- 禁止在前端程式碼硬寫任何 API key

---

## Chrome Extension 最佳實踐（Plasmo）

```
apps/extension/
├── popup.vue            # Popup UI（存入成功提示）
├── contents/            # Content scripts（偵測頁面、抓 og:image）
│   └── detector.ts
├── background/          # Service worker
│   └── index.ts
├── assets/
├── .env
└── package.json
```

- Extension 功能邊界：偵測頁面 → 抓 og:image → 呼叫 FastAPI → Popup 顯示結果
- Popup 只顯示存入狀態（成功 / 處理中 / 失敗），不做複雜 UI
- API endpoint 從 `PLASMO_PUBLIC_API_BASE_URL` 讀取
- **部署前必須先升版號**：Chrome Web Store 要求每次上傳的版本必須大於已發布版本，否則會報 `Invalid version number` 錯誤。每次發布前請先更新 `apps/extension/package.json` 的 `version` 欄位（遵循 semver，patch release 改第三位即可）。

---

## 重要技術決策（禁止在未討論前更改）

- BackgroundTasks 異步處理：MVP 階段不引入 Celery
- Embedding 維度：1536（OpenAI text-embedding-3-small），不得更改，改了要 re-embed 全部資料
- 軟刪除：`deleted_at` 欄位 + 排程硬刪除，禁止直接 hard delete
- OpenRouter 401：捕捉並回傳 503（service unavailable），不要讓前端誤判為 auth 錯誤
- 知識 vs AI 產出分層：知識（`user_items`，含手寫筆記 `source_type='note'`）進語料、可搜尋；AI 報告（`reports` 表）是產出層，**不 embed、不進語料、無 promote 回知識**。要把報告變知識只能手動新增文章重打（人的判斷是知識的唯一入口）。報告刪除採**直接硬刪除**（產出可重生，不走全站的軟刪除規範）。
