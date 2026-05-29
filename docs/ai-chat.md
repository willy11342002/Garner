# AI Chat 功能設計

> Vela 探索頁右側的 AI 對話功能，補完 RAG 開發弱項。

---

## 功能目標

| 功能 | 說明 |
|---|---|
| 對話式 RAG 查詢 | 回答「我存過關於 X 的內容，重點是什麼？」，並附上 source items |
| Session 記憶 | 同一對話內的追問有連貫性（conversation history） |
| 長期記憶 | 記住用戶問過的主題，壓縮存入 `memory_summary` |
| Session 資料夾 | 讓用戶整理自己的對話 session |

---

## 資料庫 Schema

### `chat_folders`
```sql
id          UUID PK
user_id     UUID FK users
name        Text
created_at  Timestamp
```

### `chat_sessions`
```sql
id          UUID PK
user_id     UUID FK users
folder_id   UUID FK chat_folders (nullable)  -- 未分類放 NULL
title       Text                              -- 第一則訊息自動產生
created_at  Timestamp
updated_at  Timestamp                         -- 用來排序
```

### `chat_messages`
```sql
id              UUID PK
session_id      UUID FK chat_sessions
role            Enum (user | assistant)
content         Text
cited_item_ids  UUID[]   -- RAG 引用的 user_item id
created_at      Timestamp
```

### 長期記憶
不另開表，直接加在 `users` 表：
```sql
memory_summary  Text nullable
```
每隔 10 則訊息，由 background task 把對話摘要壓縮進此欄位。

---

## API 端點

### Folders
```
GET    /chat/folders
POST   /chat/folders
PATCH  /chat/folders/{id}
DELETE /chat/folders/{id}
```

### Sessions
```
GET    /chat/sessions           -- 列出所有（含 folder_id）
POST   /chat/sessions
GET    /chat/sessions/{id}      -- 含完整 messages
PATCH  /chat/sessions/{id}      -- 改 title / folder
DELETE /chat/sessions/{id}
```

### Messages（核心）
```
POST   /chat/sessions/{id}/messages   -- streaming response
```

---

## RAG 查詢流程（`POST /messages` 後端邏輯）

```
1. 用戶輸入 → embedding
2. pgvector 搜尋用戶的 user_items（top-k = 5）
3. 組 prompt：
   - system prompt：你是 Vela 知識助理，以下是用戶的相關收藏...
   - memory_summary：用戶長期記憶（若有）
   - 最近 N 則對話（session memory）
   - retrieved items 的摘要 + title + URL
   - user message
4. OpenRouter → Claude streaming 回覆
5. 回覆含 cited_item_ids，前端顯示 source cards
6. 每 10 則訊息 → background task 壓縮更新 memory_summary
```

---

## 前端 UI 佈局

```
[Explore 頁面]
┌──────────────────────────┬──────────────────┐
│  探索內容區               │  AI Chat 側邊欄   │
│                          │                  │
│                          │  📁 我的對話      │
│                          │  ├ 未分類         │
│                          │  ├ 📁 Python 學習 │
│                          │  └ 📁 設計研究    │
│                          │                  │
│                          │  [Session 列表]  │
│                          │  ─────────────   │
│                          │  [訊息串]         │
│                          │  [輸入框]         │
└──────────────────────────┴──────────────────┘
```

---

## 實作順序

1. DB migration — 3 張表 + `users.memory_summary` 欄位
2. 後端 chat service — RAG 查詢 + streaming + memory 壓縮
3. API 路由 — folders / sessions / messages
4. 前端側邊欄 UI — 資料夾樹 + session 列表
5. 前端對話 UI — 訊息串 + source item cards + streaming 顯示
