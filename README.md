# Garner

被動建立的個人知識庫。透過 Chrome Extension 一鍵收集 YouTube 影片與網頁文章，系統自動產生摘要、標籤與語意關聯。

---

## 專案結構

```
garner/
├── apps/
│   ├── web/          # Nuxt 3 前端
│   ├── api/          # FastAPI 後端
│   └── extension/    # Plasmo Chrome Extension
├── docs/             # 架構與技術決策
├── CLAUDE.md
├── CONTRIBUTING.md
└── README.md
```

---

## 環境需求

| 工具 | 版本 |
|------|------|
| Node.js | 22+ |
| Python | 3.12+ |
| pnpm | 由 `apps/web/package.json` 的 `packageManager` 決定（目前 11.3.0，用 `corepack enable`）|
| uv | 0.6.11（釘在 Dockerfile 與兩支 workflow，要升就三處一起升）|

---

## 快速開始

### 1. Clone repo

```bash
git clone https://github.com/willy11342002/Vela.git
cd Vela
```

### 2. 前端（Nuxt 3）

```bash
cd apps/web
cp .env.example .env   # 填入環境變數
pnpm install
pnpm dev               # http://localhost:3000
```

### 3. 後端（FastAPI）

```bash
cd apps/api
cp .env.example .env   # 填入環境變數
uv sync                # 依 uv.lock 建 .venv（預設含 dev 依賴）
uv run uvicorn app.main:app --reload  # http://localhost:8000
```

### 4. Chrome Extension（Plasmo）

```bash
cd apps/extension
cp .env.example .env   # 填入環境變數
pnpm install
pnpm dev
# 開啟 Chrome → 擴充功能 → 載入未封裝項目 → 選 build/chrome-mv3-dev
```

---

## 環境變數

每個服務有自己的 `.env`，參考各服務目錄下的 `.env.example`。

---

## Tech Stack

- **前端**：Nuxt 3 / Vue 3 / Pinia
- **後端**：FastAPI / Python 3.12
- **資料庫**：Supabase PostgreSQL + pgvector
- **認證**：Supabase Auth（Google / GitHub SSO）
- **AI**：Gemini native API（LLM）+ OpenRouter（OpenAI text-embedding-3-small，1536d）
  - **RAG**：pgvector 語意檢索（embedding 相似度搜尋）+ 關鍵字搜尋，供 chat / search 引用知識庫內容
  - **Agent 框架**：LangGraph（`langgraph` + `langgraph-checkpoint-postgres`）— chat 採分層 supervisor 架構：監督者派工給 knowledge / report / trip 三個窗口 agent
- **Object Storage**：Supabase Storage（縮圖快取）
- **付費**：Gumroad
- **Extension**：Plasmo（Manifest V3）
- **部署**：Vercel（前端）/ Fly.io（後端）/ Supabase
- **監控**：Sentry

---

## 品質檢查

```bash
cd apps/web && pnpm lint && pnpm typecheck
cd apps/api && uv run pytest
```

CI 跑的就是這幾條（`.github/workflows/ci.yml`，`push` 與 `pull_request` 都會觸發）。
