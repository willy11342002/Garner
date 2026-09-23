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
├── docs/             # architecture / tech-decisions / agentic-chat-harness
├── .github/workflows # CI 與部署
├── .githooks/        # pre-commit（模組地圖同步、extension 升版號檢查）
├── CLAUDE.md
├── CONTRIBUTING.md
├── README.md
└── .gitignore
```

> 沒有 `packages/`。共用型別目前各自維護（前端在 `apps/web/types/api.ts`，
> 後端在 `apps/api/app/schemas/`），要改成共用 package 是還沒做的決定，不是現況。

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

## AI 外掛協作規則（superpowers / gstack / CE）

> 本專案裝了三套 agent 外掛，它們的 plan / review / debug 技能高度重疊。以下規則決定誰負責哪一段，避免互搶觸發。
> superpowers 與 compound-engineering 是 **project scope**（只在本專案生效，宣告於 `.claude/settings.json`）；gstack 是全域安裝（`~/.claude/skills/gstack`，所有專案都看得到）。

**最高優先**：本文件的分層規則與上方「開發新功能前強制流程」**優先於任何外掛的內建流程**。外掛的建議與本文件衝突時，一律以本文件為準。

**階段分工**（每一段只由一套負責，其餘不要重複觸發）

| 階段 | 用 | 不要用 |
|---|---|---|
| 想清楚要不要做 | gstack `/office-hours`、`/spec` | `/ce-ideate`、`/ce-brainstorm` |
| 拆計畫 | superpowers `/write-plan` | `/ce-plan`、gstack `/autoplan` |
| 寫碼 | superpowers TDD + `/execute-plan` | `/ce-work` |
| 除錯 | superpowers `systematic-debugging` | gstack `/investigate`、`/ce-debug` |
| 驗 UI | gstack `/qa`、`/browse` | `/ce-test-browser` |
| Code review | gstack `/review` | `/ce-code-review` |
| 出貨 | gstack `/ship`、`/land-and-deploy` | `/ce-commit-push-pr` |
| 收尾沉澱 | CE `/ce-compound` | gstack `/learn` |

改 API 時建議先 `/freeze apps/api`，避免 monorepo 誤傷 web。

**CE 的 compound 產出要導回這裡**：`/ce-compound` 預設寫進 `docs/solutions/`。本專案的單一真相來源是下方「現有模組地圖」——跑完 compound 後，若本輪新增了 service / composable / component，**必須回頭更新模組地圖**，不要讓 `docs/solutions/` 長成第二份真相來源。

**成本提醒**：`/ce-plan`（~38k tok）、`/ce-babysit-pr`（~30k）、`/ce-compound`（~26k）、`/ce-code-review`（~20k）、superpowers `subagent-driven-development`（~10k）單次呼叫很貴，非必要不要順手打。

---

## 現有模組地圖（動工前先掃，避免重造輪子）

> 以實際 codebase 為準（非理想範本）。一句話描述職責，找相近的就擴充。

### API services（`apps/api/app/services/`）
- `item_service` — Item 建立與處理流程主入口
- `ai_service/` — **⚠️ AI provider 是混用的，不要假設全部都是 Gemini**：LLM（chat 對話、摘要、標籤等文字生成）已全面改用 **Gemini native API**（`google-genai` SDK），但 **embedding 至今仍是 OpenRouter**（`text-embedding-3-small`，1536d，走 OpenAI-compatible SDK），兩者是不同 provider、不同 SDK、不同 API key。拆成子模組：`_client`（Gemini 呼叫基礎。對話內容一律用原生 `types.Content`/`types.Part`，**不要再手刻 OpenAI 格式的 dict**；統一用 `user_turn()`/`model_turn()`/`tool_results()`/`image_part()` 這幾個 builder 組，再交給 `generate()`/`generate_stream()`。內部有 `_llm()`/`_emb()` 兩個各自的 model getter，對應上述兩個 provider）、`chat`（只剩 `compress_memory`：session 記憶壓縮。舊的單一 agent 版 chat_stream/synthesize_*/agentic_chat_stream 已被 `graph/` 取代並刪除）、`embed`（embedding，走 OpenRouter）、`ingest`（內容分析/標籤/摘要，走 Gemini）、`report`（報告產生）、`chain`（關聯鏈分析）、`segment`（jieba 中文斷詞，字典打包在 pip 套件內、從本地磁碟載入、零網路請求，供 BM25 全文檢索用。**不要改回 CKIP**：ckip-transformers 每次冷啟動都會打好幾輪 HuggingFace API 做 revision 檢查，在 Fly 的 shared-cpu-1x 單核機上會卡死整個 event loop，連 /health 都回不了）、`rerank`（FlashRank 自架 cross-encoder 重排，多語模型，非雲端 API）、`graph/`（LangGraph 分層 agent：A 監督者 `supervisor.py` 派工給 `windows/knowledge.py`(B)／`windows/report.py`(C)／`windows/trip.py`(D) 三個窗口，見 `docs/agentic-chat-harness.md`。**chat 與行程／報告頁的 AI 懸浮球都走這一套，能力完全相同** —— D 窗口能操作任何一份行程、C 窗口能操作任何一份報告、B 窗口只讀。工具全部收 `trip_id`／`report_id`／`card_id`，流程是「search → get → 改」。`GraphState["scope"]`（使用者畫面上開著哪一份）**不是權限機制**，只是給 A 的提示讓指稱有對象；**權限一律在資料層擋**（每個寫入函式自己帶 user_id 查一次，`_get_accessible_trip(required_role="editor")` / `crud_reports.get_one(db, user_id, ...)`））
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
- `quick_meta` — `POST /items/` 建立當下同步跑的輕量 metadata 前置步驟（在背景 ingest pipeline 之前跑,讓 201/203 回應時 title/thumbnail 就正確）：YouTube/TikTok 用平台原生 oEmbed；IG/Facebook 沒有可用的官方 oEmbed（需 Meta App Review），改用 `facebookexternalhit` User-Agent 直接抓貼文頁面的 og:title/og:description/og:image（IG/FB 官方連結預覽爬蟲會放行、跳過登入牆);Article 直接重用現有單次 Apify 呼叫（本來就快，同時拿到 title + 全文）。逾時/失敗回退成 title=null + API 回 203，交給背景 pipeline 補正。**它寫進 `thumbnail_url` 的是平台的短期簽名網址，只是第一眼的暫時值**，背景 pipeline 快取完成後一定會覆寫（`ingest_graph._fetch_core`）。
- `thumbnail_service` — 縮圖在 Supabase Storage 的快取層：路徑慣例（`thumbnails/{item_id}.{ext}`）、
  上傳、公開網址、查既有檔案，providers / `item_service` / backfill 都走這支，不要各自拼路徑。
  **平台給的縮圖網址是短期簽名網址**（IG/FB 的 scontent 帶 `oe=`、TikTok 帶 `x-expires`），
  幾小時到幾天就失效，只有這裡回傳的 Storage 公開網址能長期存進 DB

### API providers（`apps/api/app/providers/`）
> ingest pipeline 的**內容來源策略層**，不是 service 也不是 crud。新增支援平台請擴充這裡，
> 不要在 `item_service` 或 `apify_service` 內塞 if/else 判斷網址。

- `base` — `ContentProvider` 抽象基底（`matches` / `fetch_info` / `fetch_content` 三個方法）
  與 `FetchInfo` dataclass；另提供共用的 `_resolve_thumbnail`（下載平台縮圖 → 丟給
  `thumbnail_service` 快取，回傳 `(url, cached)`；快取失敗才退回平台網址）與 `_download_bytes`。
  `FetchInfo.thumbnail_cached` 就是那個 `cached`，**寫回 DB 的判斷靠它**，不要改成只看欄位空不空
- `__init__` — `get_provider(url)` 註冊表，依序比對 YouTube → Instagram → TikTok →
  Facebook → Article → Default，第一個 `matches()` 命中者勝出
- `youtube` · `instagram` · `tiktok` · `facebook` — 各平台的網址正規化
  （`normalize_*_url`）＋ 抓取邏輯
- `article` — 一般網頁文章（`fetch_info` 就會帶回 `raw_content`，因此跳過 `fetch_content`）
- `default` — 都沒命中時的保底

### API routers（`apps/api/app/routers/`）
`items` · `articles` · `tags` · `search` · `chat` · `reports` · `auth` · `billing` · `quota` · `notifications` · `locations` · `admin` · `trips` · `trip_tags`

### API crud（`apps/api/app/crud/`）
`items` · `tags` · `users` · `chat` · `reports` · `chunks` · `places` · `locations` · `notifications` · `trips` · `quota`

> `quota` 是 `/quota/me` 的彙總查詢（一次 round-trip 撈齊 plan／用量／限制的手寫 SQL）。
> 跟 `quota_depends` 的 ORM 逐項查詢刻意分開：後者是進 API 時判斷單一限制，前者是給前端畫面一次拿齊。

### API workers（`apps/api/app/workers/`）
> BackgroundTasks 的實際工作函式。router 只負責驗證與排程，批次／長流程邏輯放這裡。

- `process_item` — ingest pipeline 的 stage 函式與 DAG 編排
- `ingest_graph` — ingest 的 LangGraph 流程
- `backfill` — 一次性 backfill（`backfill_search_zh`：補齊既有資料的中文斷詞欄位；
  `backfill_thumbnails`：把還指向平台 CDN 的 `thumbnail_url` 換回 Storage 永久網址）
- `maintenance` — 每日排程維護

### API 其他（`apps/api/app/` 根目錄）
- `dependencies` — 共用 `Depends`：DB session、`get_current_user`（只認 Supabase JWT，
  PAT 機制已於 2026-08 整套下架）
- `quota_depends` — 以 `Depends` 注入的配額檢查（`SaveQuota` / `ChatQuota` / `SearchAccess`）。
  只處理「進 API 時就能判斷」的限制；影片長度這種要到 background task 才知道的，
  在 `item_service.create_item()` 內查 plan 處理

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
- `useTripTags` — 旅遊行程的標籤目錄：清單、重新命名、刪除、看板欄位的拖曳排序與新增。
  排序只存 localStorage（後端沒欄位），載入後要 `applyStoredTagOrder()`
- `useTripItemEditor` — 行程卡片編輯器：表單狀態與「每個欄位各自 PATCH」的自動儲存
  （樂觀更新 + 失敗回滾，備註去抖動 700ms）。簽章 `(current, trips, availableTags)`
- `useEmojiPicker` — emoji 選擇器（含中文關鍵字對照表）與依觸發按鈕定位的浮層
- `useItemMap` — ItemDetailModal 地圖分頁的全部邏輯（地點載入、marker 渲染、地點搜尋
  與新增、geocoding 輪詢、資訊／地圖分頁切換時的 gmap claim/release）。
  簽章是 `useItemMap(itemId, activeTab)`，`activeTab` 由元件持有再傳進去
- `useItemPolling` — ItemDetailModal 的重新分析與初始分析輪詢（含 retryIngest）。
  輪詢請求都帶 `skipWhenHidden`
- `useSwipeToClose` — 手機版底部面板的「向下拖曳關閉」手勢（`panelRef` + 三個 touch handler）。
  trips 的卡片編輯 modal 與 ItemDetailModal 共用，不要再各寫一份
- `useImageFallback` — 縮圖載入失敗的共用回退（`isBroken(url)` / `markBroken(url)`，模組層級共享的失敗 URL 集合）。`<img>` 一律寫成 `v-if="url && !isBroken(url)"` + `@error="markBroken(url)"`，失敗時退回原本「沒有圖片」的 placeholder 分支，不要留破圖 icon

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
- `trip/` — TripAiFab（旅遊行程頁的 AI 修改懸浮球：可拖曳左右停靠、SSE 串流逐動作 emit card-added/updated/deleted 給頁面即時更新。**呼叫 chat 的端口**，不是專屬 API —— `POST /chat/sessions` 開一條 session、`POST /chat/sessions/{id}/messages` 帶 `scope={kind:'trip',id}`、`GET .../stream` 訂閱，跟首頁 chat 完全一樣；多輪追問靠後端 session 歷史，不自己帶 history）；TripShareModal（行程共用管理：成員列表、email 邀請、邀請連結產生/撤銷，owner 限定管理，viewer/editor 唯讀查看）
- 根目錄 — BaseFab（通用懸浮球容器：可拖曳、側邊停靠、badge、icon、panel slot、支援多球同時共存 multi-FAB），TiptapEditor, BubbleMenuBar, CodeBlockView, ProcessingStatus, SourceListModal（跨頁共用：列出來源收藏，點選後 emit select(id) 供開啟詳情）, ToastList（全域 toast 容器，掛在 default layout，搭配 useToast）, OfflineBanner（PWA 離線提示條，偵測 navigator.onLine 事件，掛在 default layout）

### Web utils（`apps/web/utils/`）
- `apiFetch` — 統一 API 呼叫封裝（前端 fetch 一律走這裡）
- `text` — 文字處理工具
- `apiError` — 把 apiFetch 拋出的錯誤分類（`classifyApiError`）供 UI 顯示有意義的訊息。
  後端 `HTTPException(detail=...)` 的字串優先直接顯示，其餘依 status 分成
  network / server / forbidden / notFound / quota / validation 六類，
  對應的 i18n key 在 `API_ERROR_I18N_KEYS`。**不要再寫「操作失敗」這種吞掉錯誤的 toast**
- `item` — 收藏項目的顯示用純函式：`cardTitle`、`domainFromUrl`、`tagColor` / `TAG_COLORS`、
  `sourceKindFromUrl`（網址 → 平台種類）與三組文案對照表（`SOURCE_I18N_KEYS` 走 i18n、
  `SOURCE_DISPLAY_NAMES` 未翻譯、`SOURCE_LABELS` 對應後端 source_type 欄位）
- `itemStatus` — 判斷 item 的 ingest pipeline 是否「中斷」（`!parsed_at` 且 `updated_at` 超過 5 分鐘沒更新）或「失敗」（任一 stage `_status === 'error'`），供卡片/詳情頁顯示重試 badge

---

## Tech Stack

| 層 | 技術 |
|---|---|
| 前端 | Nuxt 3 + Vue 3 + Pinia |
| 後端 | FastAPI (Python) |
| 資料庫 | Supabase PostgreSQL + pgvector |
| 認證 | Supabase Auth（Google / GitHub SSO）|
| AI — LLM | **Gemini native API**（`google-genai` SDK）：對話、摘要、標籤、報告 |
| AI — Embedding | **OpenRouter**（OpenAI `text-embedding-3-small`，1536d，走 OpenAI-compatible SDK）|
| AI — Agent | LangGraph（`langgraph` + `langgraph-checkpoint-postgres`），分層 supervisor 架構 |
| Object Storage | Supabase Storage（縮圖快取，bucket 由 `STORAGE_BUCKET` 指定）|
| 付費 | Gumroad |
| Extension | Plasmo（Manifest V3）|
| 部署 | Vercel（前端）/ Fly.io（後端）|
| 監控 | Sentry（`sentry-sdk`，見 `app/core/tracing.py`）|

> **LLM 與 embedding 是兩個不同 provider、不同 SDK、不同 API key，不要混為一談。**
> 這張表以前寫成「OpenRouter → Claude」，跟下方模組地圖自相矛盾，已於 2026-08 更正。
>
> **Cloudflare R2 沒有在用**：縮圖實際上傳 Supabase Storage
> （`services/thumbnail_service.py`，由 `providers/base.py` 與 `item_service.py` 呼叫）。
>
> **PostHog 目前沒有接**：不是依賴、沒有 plugin、沒有任何載入程式碼。
> 但 `apps/web/pages/privacy.vue` 的隱私政策仍聲明有用 PostHog 收集匿名行為事件——
> 這是對外聲明與實作不符，待處理（要嘛真的接上、要嘛移除該段聲明）。

> **延伸閱讀**（屬同步對象，改到相關內容時一併更新）：
> - 技術選型理由、成本、部署 → `docs/tech-decisions.md`
> - 產品定位、商業模式、整體架構 → `docs/architecture.md`
> - 最新訂閱方案與價格（單一真相來源）→ `apps/web/pages/pricing.vue`

---

## Health Stack

品質檢查的完整指令。CI（`.github/workflows/ci.yml`）跑的就是這幾條，本機請跑同一組：

- lint: `cd apps/web && pnpm lint`
- typecheck: `cd apps/web && pnpm typecheck`
- test: `cd apps/api && uv run pytest`

三件事要知道：

1. **`pnpm install` 的 postinstall 會跑 `nuxt prepare`**，產生 `.nuxt/eslint.config.mjs`
   與型別定義。`eslint.config.mjs` 與 `typecheck` 都依賴它，乾淨環境不能跳過 install。
2. **CI 同時掛 `push` 與 `pull_request`**。本專案實際流程是直接推 main，
   只掛 `pull_request` 等於 CI 從來不會跑——2026-08 之前就是這樣，
   `pnpm lint` 壞了（缺 eslint.config.mjs、exit 2）好幾個月沒人發現。
3. **`deploy-api` / `deploy-web` 各自有前置 job**，測試或型別沒過就不部署。
   不要為了趕上線加 `continue-on-error`——那正是 pytest 當年沒真的跑過的原因。

前端目前**沒有任何自動化測試**，lint 與 typecheck 是唯一的自動防線，
所以動到 `.vue` 的行為時要自己在瀏覽器走一遍。

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
│   ├── quota_depends.py     # 配額檢查 Depends（SaveQuota / ChatQuota / SearchAccess）
│   ├── routers/             # 路由層：只做參數接收與回傳，不放業務邏輯
│   │   ├── items.py
│   │   ├── tags.py
│   │   ├── search.py
│   │   └── auth.py
│   ├── services/            # 業務邏輯層：所有核心運算放這裡（完整清單見上方「現有模組地圖」）
│   │   ├── item_service.py
│   │   ├── ai_service/      # LLM 走 Gemini native、embedding 走 OpenRouter（兩個 provider）
│   │   ├── search_service.py
│   │   └── ...              # chat / place / geocoding / billing / gumroad / apify
│   ├── providers/           # 內容來源策略層：依網址挑 provider 抓取（見上方模組地圖）
│   │   ├── base.py          # ContentProvider ABC + FetchInfo
│   │   ├── youtube.py
│   │   └── ...              # instagram / tiktok / facebook / article / default
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
│   │   ├── tracing.py       # Sentry span helper
│   │   └── database.py      # Supabase 連線、session factory
│   └── workers/             # BackgroundTasks 的實際工作函式
│       ├── process_item.py
│       └── ingest_graph.py
├── alembic/                 # migration（指令見 .claude/skills/garner-alembic）
├── tests/
│   ├── test_items.py
│   └── test_search.py
├── .env
├── pyproject.toml
├── uv.lock                  # 依賴的唯一真相，CI / 部署一律 --locked
└── Dockerfile
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

### 依賴管理（uv，**禁止 pip**）

**任何情況都不准用 `pip`。** 這不是偏好問題：`pip install -e .` 會無視 `uv.lock` 重新解析依賴，
CI／部署／Docker 三邊各解出一組版本，測的跟跑的就不是同一組。2026-08 之前 CI 的 pytest
長期是 command not found（`pip install -e .` 不含 dev 依賴），再被 `continue-on-error: true`
蓋掉，156 個測試從來沒真的跑過——就是這樣來的。

| 要做的事 | 指令 |
|---|---|
| 安裝／同步依賴 | `uv sync`（預設含 dev group） |
| 生產環境安裝 | `uv sync --locked --no-dev` |
| 跑任何 Python 指令 | `uv run <cmd>`（`uv run pytest`、`uv run alembic upgrade head`） |
| 新增依賴 | `uv add <pkg>`（自動更新 `uv.lock`） |
| 新增 dev 依賴 | `uv add --dev <pkg>` |

- dev 依賴放 `[dependency-groups]`（PEP 735），**不要放 `[project.optional-dependencies]`**：
  `uv sync` 預設就會裝前者，後者得多打 `--extra dev`——這是踩過的坑。
- `uv.lock` 進版控，是依賴的唯一真相。CI 與部署一律加 `--locked`（lock 與 pyproject 不一致就讓它失敗）。
- uv 版本釘在三處：`apps/api/Dockerfile`、`.github/workflows/ci.yml`、`.github/workflows/deploy-api.yml`。
  要升級就三處一起升，不要只動一處。
- 映像內的 venv 放 `/opt/venv`（靠 `UV_PROJECT_ENVIRONMENT`），**不要用預設的 `/app/.venv`**：
  `docker-compose.yml` 會把 `./apps/api` 掛載成 `/app`，預設路徑會被主機 venv 整個蓋掉，
  容器裡就找不到 `alembic` / `uvicorn`。
- `apps/api/.dockerignore` 必須排除 `.venv` 與 `.env`（`.env` 有真實金鑰，不能烤進映像）。
- `apps/api/entrypoint.sh` **不是死檔**，`docker-compose.yml` 的 api service 靠它啟動
  （本機 compose 專用：對 compose 內的 pgvector 跑 migration + `--reload`）。
  生產的 migration 走 `deploy-api.yml`，兩者是不同環境、不重複。

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

### 依賴管理（pnpm，版本釘在 `packageManager`）

- pnpm 版本由 `apps/web/package.json` 的 `packageManager` 欄位決定。Dockerfile 只跑
  `corepack enable`（**不要用 `corepack prepare pnpm@latest`**，那等於每次建置抓當下最新版）；
  GitHub Actions 的 `pnpm/action-setup` 要帶 `package_json_file: apps/web/package.json`
  （repo 根目錄沒有 package.json，不指定會找不到版本）。
- pnpm 10+ 的設定一律放 `apps/web/pnpm-workspace.yaml`，**不是** package.json 的 `pnpm` 欄位，
  也不是 `.npmrc`（後者現在只讀 auth / registry）。
- 依賴的 build script 預設不執行，且 pnpm 11 的 `strictDepBuilds` 預設為 true——沒放行就是
  建置失敗。放行寫在 `allowBuilds`，**它是 map 不是 list**：
  `esbuild: true`，寫成 `- esbuild` 陣列不會生效也不會報錯。舊的 `onlyBuiltDependencies`
  在 pnpm 11 已移除。
- `apps/web/Dockerfile` 必須把 `pnpm-workspace.yaml` 跟 package.json、lock 一起 COPY，
  否則 install 當下讀不到 `allowBuilds`。
- `nuxt.config.ts` 釘的是 `preset: 'vercel'`（生產走 Vercel），產物在 `.vercel/output`。
  Docker 映像要的是 `.output`，靠 Dockerfile 內的 `NITRO_PRESET=node-server` 覆寫，
  **不要去改 nuxt.config.ts**。
- `apps/web/.dockerignore` 必須排除 `node_modules`（pnpm 的 symlink 會讓 docker 打包
  build context 失敗）與 `.env`。

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
├── background/          # Service worker（整個擴充只有這一支）
│   └── index.ts
├── assets/
├── .env
└── package.json
```

- **Extension 不接觸後端**：點 toolbar icon → `chrome.tabs.create` 開新分頁到 `${PLASMO_PUBLIC_WEB_URL}/app/quick-add?url=<當前分頁網址>`，由網頁版（`apps/web/pages/app/quick-add.vue`）負責呼叫 API、認證、顯示結果。非 http(s) 的分頁（`chrome://` 等）改開 `/app`。iOS 捷徑走的是同一條路徑。
- **不要把 API base 寫回擴充**：後端網址是 build-time 寫死的，一改就得重送 Chrome Web Store 審核（審核要等幾天）。2026-08 後端從 Railway 搬到 Fly.io 就是這樣讓線上版整個掛掉。擴充只認前端網域，後端搬家與擴充無關。
- 擴充沒有 UI（無 popup / sidepanel / options）也沒有 content script。權限只有 `activeTab` + `storage`（storage 僅用於升級時清掉舊版殘留的 PAT），沒有 `host_permissions`。
- 認證由網頁版處理：未登入時 `middleware/auth.global.ts` 會導去 `/login?redirect=...`，登入後自動回到 quick-add 繼續新增。
- **PAT（personal access token）機制已於 2026-08 整套移除**（router / crud / model / `personal_access_tokens` 表 / `dependencies` 的 PAT 驗證分支全刪，migration `0058`）。它原本只服務擴充與 iOS 捷徑，兩者改走 quick-add 後就沒有用途了。`get_current_user` 現在只認 Supabase JWT，不要再引入長期有效的 token。
- **部署前必須先升版號**：Chrome Web Store 要求每次上傳的版本必須大於已發布版本，否則會報 `Invalid version number` 錯誤。每次發布前請先更新 `apps/extension/package.json` 的 `version` 欄位（遵循 semver，patch release 改第三位即可）。

---

## 重要技術決策（禁止在未討論前更改）

- Python 依賴一律走 uv（`uv sync` / `uv run`），**禁止任何形式的 pip**；`uv.lock` 是唯一真相，CI 與部署用 `--locked`（細節見上方「依賴管理」）
- BackgroundTasks 異步處理：MVP 階段不引入 Celery
- Embedding 維度：1536（OpenAI text-embedding-3-small），不得更改，改了要 re-embed 全部資料
- 軟刪除：`deleted_at` 欄位 + 排程硬刪除，禁止直接 hard delete
- OpenRouter 401：捕捉並回傳 503（service unavailable），不要讓前端誤判為 auth 錯誤
- 知識 vs AI 產出分層：知識（`user_items`，含手寫筆記 `source_type='note'`）進語料、可搜尋；AI 報告（`reports` 表）是產出層，**不 embed、不進語料、無 promote 回知識**。要把報告變知識只能手動新增文章重打（人的判斷是知識的唯一入口）。報告刪除採**直接硬刪除**（產出可重生，不走全站的軟刪除規範）。
