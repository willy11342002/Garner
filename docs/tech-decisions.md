# Garner — 技術選型決策文件

> 最後更新：2026-05-27

---

## 架構總覽

```
前端（Nuxt 3）
    ↓
後端（FastAPI）
    ↓
資料層（Supabase PostgreSQL + pgvector）
    ↓
AI 服務（Gemini native → LLM；OpenRouter → OpenAI Embedding）
```

一個前端 server + 一個後端 server。

---

## 前端：Nuxt 3

**為什麼不是純 Vue 3 + Vite？**

Nuxt 3 本身就是建在 Vue 3 + Vite 之上，寫法一樣，但多了 SSR 支援。公開集合頁面需要 SSR 才能被 Google 索引，這是 SEO 飛輪的技術基礎。用 Nuxt 3 只需要啟動一個前端 server 就同時搞定 SPA 和 SSR。

**路由渲染模式設定：**

```ts
// nuxt.config.ts
routeRules: {
  '/explore/**': { ssr: true },   // 公開探索頁，SEO 需要
  '/share/**':   { ssr: true },   // 分享頁，SEO 需要
  '/app/**':     { ssr: false },  // 登入後所有頁面，純 SPA
}
```

**配套：**
- 狀態管理：Pinia（標籤選中狀態、批次操作）
- 路由：Nuxt 內建 file-based routing

---

## 後端：FastAPI（Python）

**核心功能：**
- JWT 認證
- WebSocket（存入後即時回饋給前端）
- BackgroundTasks 異步處理（FastAPI 內建，MVP 階段不需要 Celery）

**存入流程（異步）：**

```
用戶存入 URL
    → FastAPI 立刻回傳 202（已接收）
    → BackgroundTasks 背景執行：
        1. 抓縮圖（依網址挑 provider，見 app/providers/）
        2. 呼叫 Gemini 產生摘要 + 標籤
        3. 呼叫 OpenAI Embedding API（via OpenRouter）
        4. 寫入 PostgreSQL + pgvector
    → WebSocket 推回前端（toast 通知）
```

```python
@app.post("/items")
async def save_item(url: str, background_tasks: BackgroundTasks):
    item_id = create_item_record(url)  # 立刻寫入 DB（pending 狀態）
    background_tasks.add_task(process_item, item_id, url)
    return {"id": item_id, "status": "processing"}

async def process_item(item_id, url):
    thumbnail = fetch_thumbnail(url)
    summary, tags = call_claude(url)
    embedding = call_openai_embedding(summary)
    update_item(item_id, thumbnail, summary, tags, embedding)
    # 推 WebSocket 通知前端
```

存入後即時回饋（toast.html 的那個動畫效果）靠 WebSocket 實現，不是同步等待。

**升級時機：** 任務失敗率高、或需要監控隊列狀態時，再引入 Celery + Redis。

---

## 資料層

### Supabase PostgreSQL + pgvector

- 關聯式資料和向量搜尋在同一個資料庫，不需要另接 Pinecone
- pgvector 支援 HNSW index，10 萬筆向量以內查詢速度夠用
- Row Level Security (RLS) 對應 ER 的 user 資料隔離
- 免費方案：500MB 資料庫空間，前 1000 個用戶不會超標
- 軟刪除狀態機（active → archived → deleted）直接在 PostgreSQL 管理

### Object Storage（Supabase Storage）

- 用於快取縮圖，bucket 由 `STORAGE_BUCKET` 指定（預設 `thumbnails`）
- 實作在 `app/providers/base.py:_cache_thumbnail` 與 `app/services/item_service.py`
- 曾規劃改用 Cloudflare R2（更便宜、無出流量費用），**但一直沒有實作**。
  repo 內沒有任何 R2 設定或程式碼，需要時再評估。

---

## 認證：Supabase Auth

- 包含 Google / GitHub SSO
- 免費方案：50,000 月活用戶（MAU）
- 前 100 個用戶完全免費

---

## 訂閱付費：Gumroad

- Merchant of Record：代為處理全球 VAT / 稅務，個人開發者免去稅務申報負擔
- 無月費，按筆交易抽成；沒有用戶付費就沒有成本
- Webhook 整合訂閱狀態同步到後端（見 `gumroad_service.py` / `billing_service.py`）
- **最新方案與價格以前端為單一真相來源**：`apps/web/pages/pricing.vue` → `components/pricing/PricingPlans.vue`

---

## AI 服務：Gemini（LLM）+ OpenRouter（Embedding）

**現況是兩個 provider 並存，不是一個。** 兩者用不同 SDK、不同 API key，
在 `app/services/ai_service/_client.py` 內分別由 `_llm()` 與 `_emb()` 取得。

| 用途 | Provider / 模型 | SDK |
|------|------|------|
| 對話、摘要、標籤、報告 | Gemini native API | `google-genai` |
| Embedding 向量化 | OpenRouter → OpenAI `text-embedding-3-small`（1536 維）| `openai`（OpenAI-compatible）|

**為什麼 LLM 從 OpenRouter → Claude 改成 Gemini native？**

原本走 OpenRouter 是為了「一個 key 打天下」，但 agentic chat 需要原生的
function calling 與 `types.Content` 結構化訊息，隔一層 OpenAI-compatible 介面
會失真（工具呼叫格式、多模態 part 都要手動轉）。改成 native 之後
`_client.py` 統一用 `user_turn()` / `model_turn()` / `tool_results()` / `image_part()`
組訊息，**不要再手刻 OpenAI 格式的 dict**。

**為什麼 embedding 還留在 OpenRouter？**

1536 維是寫死的架構決策（見下方「不可更改」），換 provider 就要 re-embed 全部資料。
沒有足夠理由承擔這個成本，所以維持現狀。

**OpenRouter 的已知限制（仍適用於 embedding）：**
- 充值有 5.5% 手續費
- 2025-2026 有三次斷線記錄（每次約 35-50 分鐘）
- 沒有 SLA 保證
- 斷線時會回傳 401 錯誤（容易誤判為自己的程式問題）→ 後端捕捉後轉 503

---

## 縮圖服務（免費）

```
YouTube：
https://img.youtube.com/vi/{VIDEO_ID}/maxresdefault.jpg

網頁文章：
<meta property="og:image" content="...">
```

不需要任何 API key，不需要付費。IG 縮圖是第二階段再處理。

---

## 部署

| 服務 | 平台 | 備註 |
|------|------|------|
| FastAPI 後端 | **Fly.io**（app: `garner-api`）| 2026-08 從 Railway 搬過來，已定案 |
| Nuxt 3 前端 | Vercel | 與 Nuxt 3 官方整合最佳 |
| PostgreSQL + Auth | Supabase | 免費方案起步 |
| 縮圖 Object Storage | Supabase Storage | bucket 由 `STORAGE_BUCKET` 指定 |

> 搬離 Railway 時踩過的坑：Chrome Extension 曾把後端網址寫死在 build 裡，
> 一搬家就整個掛掉，且改回來要重送 Chrome Web Store 審核。
> 現在擴充只認前端網域（走 `/app/quick-add`），後端搬家與擴充無關。

---

## 監控

- 錯誤監控：**Sentry**（`sentry-sdk[fastapi]`，span helper 在 `app/core/tracing.py`）
- 使用者行為分析：**尚未接**。`apps/web/pages/privacy.vue` 的隱私政策目前聲明
  有用 PostHog 收集匿名行為事件，但 repo 內沒有 posthog 依賴、沒有 plugin、
  沒有任何載入程式碼。這是對外聲明與實作不符，要嘛補上整合、要嘛移除該段聲明。

---

## MVP 階段成本估算

| 服務 | 免費額度 | 付費觸發點 |
|------|---------|-----------|
| Supabase | 500MB / 50K MAU | 超量或需要更多功能 |
| Vercel | 100GB 流量 | 商業用途需升級 |
| Fly.io | 小型機器有免費額度 | 超量按量計費（目前 shared-cpu-1x 單核）|
| Gumroad | 無月費 | 每筆交易抽成 |
| Gemini API | 有免費層級 | LLM 呼叫（對話 / 摘要 / 標籤 / 報告）|
| OpenRouter | $19 已有額度 | 只剩 embedding 在用（+5.5% 手續費）|

**唯一從第一天就計費的是 AI API 呼叫。** 前 100 個用戶預估每月 $3–10 美金。

---

## Chrome Extension

- 框架：Plasmo（支援 Vue，內建 Manifest V3，HMR 開發體驗）
- 功能：偵測頁面 → 抓 og:image → 呼叫 FastAPI 存入