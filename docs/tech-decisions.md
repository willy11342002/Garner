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
AI 服務（OpenRouter → Claude + OpenAI Embedding）
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
        1. 抓縮圖（YouTube API / og:image）
        2. 呼叫 Claude API 產生摘要 + 標籤
        3. 呼叫 OpenAI Embedding API
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

### Object Storage（Cloudflare R2）

- 用於快取縮圖
- 比 Supabase Storage 便宜，無出流量費用

---

## 認證：Supabase Auth

- 包含 Google / GitHub SSO
- 免費方案：50,000 月活用戶（MAU）
- 前 100 個用戶完全免費

---

## 訂閱付費：Stripe

- 無月費，每筆交易抽 2.9% + $0.30
- 沒有用戶付費就沒有成本
- Webhook 整合訂閱狀態同步到 Supabase

---

## AI 服務：OpenRouter

**為什麼用 OpenRouter 而不是直連各家 API？**

- 一個 API key 存取 Claude（摘要）+ OpenAI Embedding
- 不需要分別申請 Anthropic 和 OpenAI 帳號
- MVP 階段 $19 額度夠用來驗證產品

**已知限制：**
- 充值有 5.5% 手續費
- 2025-2026 有三次斷線記錄（每次約 35-50 分鐘）
- 沒有 SLA 保證
- 斷線時會回傳 401 錯誤（容易誤判為自己的程式問題）

**升級時機：** 每月 AI 成本超過 $50，或有付費用戶之後，考慮換直連 Anthropic API。Code 只需改一行 endpoint。

**模型分工：**

| 用途 | 模型 |
|------|------|
| 摘要 + 標籤生成 | Claude（via OpenRouter）|
| Embedding 向量化 | OpenAI text-embedding-3-small（1536 維）|

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
| FastAPI 後端 | Railway 或 Fly.io | Railway 設定較簡單；Fly.io 彈性較高 |
| Nuxt 3 前端 | Vercel | 與 Nuxt 3 官方整合最佳 |
| PostgreSQL + Auth | Supabase | 免費方案起步 |
| Redis | Upstash | 免費方案起步 |

---

## 監控

- 錯誤監控：Sentry（FastAPI + Nuxt 3 都有 SDK）
- 使用者行為分析：PostHog

---

## MVP 階段成本估算

| 服務 | 免費額度 | 付費觸發點 |
|------|---------|-----------|
| Supabase | 500MB / 50K MAU | 超量或需要更多功能 |
| Vercel | 100GB 流量 | 商業用途需升級 |
| Railway | $5 免費額度/月 | 用完後按量計費 |
| Stripe | 無月費 | 每筆交易 2.9% + $0.30 |
| OpenRouter | $19 已有額度 | 用完後按量充值（+5.5% 手續費）|

**唯一從第一天就計費的是 AI API 呼叫。** 前 100 個用戶預估每月 $3–10 美金。

---

## Chrome Extension

- 框架：Plasmo（支援 Vue，內建 Manifest V3，HMR 開發體驗）
- 功能：偵測頁面 → 抓 og:image → 呼叫 FastAPI 存入