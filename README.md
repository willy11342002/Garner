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
├── packages/
│   └── types/        # 共用 TypeScript 型別定義
├── CLAUDE.md
├── CONTRIBUTING.md
└── README.md
```

---

## 環境需求

| 工具 | 版本 |
|------|------|
| Node.js | 20+ |
| Python | 3.12+ |
| pnpm | 9+ |

---

## 快速開始

### 1. Clone repo

```bash
git clone https://github.com/your-org/garner.git
cd garner
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
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload  # http://localhost:8000
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
- **AI**：OpenRouter（Claude + OpenAI Embedding）
- **Extension**：Plasmo（Manifest V3）
- **部署**：Vercel / Railway / Supabase
