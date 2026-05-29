# 提案：集合 Description + Embedding 語意搜尋

> 狀態：待實作
> 提案日期：2026-05-29

---

## 背景

目前 `GET /explore/browse` 的搜尋邏輯只對 `Collection.title` 做 `ILIKE '%q%'` 比對，無法處理語意相近但用詞不同的查詢（例如輸入「學習程式」找不到標題叫「Code Journey」的集合）。

---

## 提案內容

在 `collections` 資料表新增 `description` 欄位，並對 `description`（或 fallback 至 `title`）產生 embedding，用於公開集合的語意搜尋。

---

## Embedding 觸發時機

**每次用戶按下「儲存集合」時觸發**，包含：

- 建立新集合
- 更新集合標題或 description
- 更新集合內容（新增/移除 items）

流程：
```
用戶儲存集合
  → collection_service 呼叫 ai_service.embed_text()
  → 取得 1536 維向量
  → 寫入 collections.description_embedding
```

Embed 的文字來源：
- 有 description → embed `description`
- 無 description → fallback embed `title`

---

## 優點

- 搜尋品質大幅提升：語意對上就能命中，不依賴精確關鍵字
- 多語言友好：中文查詢能匹配英文集合
- description 本身對 share 頁也有展示價值

## 缺點 / 風險

- 每次儲存都呼叫 OpenAI Embedding API，增加延遲與費用
- 冷啟動：舊有集合需要一次性 backfill embedding
- description 為空的集合 fallback 至 title，語意覆蓋率有限
- pgvector 向量搜尋比 `ILIKE` 慢，需要建立 `ivfflat` index

---

## 改動範圍

### 後端

| 檔案 | 改動內容 |
|---|---|
| `alembic/` | 新增 migration：`collections` 加 `description TEXT`、`description_embedding VECTOR(1536)` |
| `app/models/collection.py` | 加 `description`、`description_embedding` 兩個欄位 |
| `app/schemas/collection.py` | `CollectionCreate`、`CollectionUpdate`、`CollectionRead` 加 `description` |
| `app/schemas/explore.py` | `PublicCollectionRead` 加 `description` |
| `app/services/collection_service.py` | 建立/更新集合時呼叫 `ai_service.embed_text()`，寫入 embedding |
| `app/services/ai_service.py` | 新增 `embed_text(text: str) -> list[float]`，呼叫 OpenAI text-embedding-3-small |
| `app/crud/collections.py` | `list_public` 新增向量搜尋分支：有 `q` 時先 embed query，再用 `<=>` cosine distance 排序 |

### 前端

| 檔案 | 改動內容 |
|---|---|
| `apps/web/types/api.ts` | `PublicCollectionRead` 加 `description?: string` |
| 建立/編輯集合的表單元件 | 加 description textarea 輸入欄位 |
| `apps/web/pages/share/[slug].vue` | 顯示 description |
| `apps/web/pages/app/explore/browse.vue` | 無需改動（搜尋切換邏輯在後端） |

### 資料庫

```sql
-- migration
ALTER TABLE collections ADD COLUMN description TEXT;
ALTER TABLE collections ADD COLUMN description_embedding VECTOR(1536);

-- index（待資料量足夠後建立）
CREATE INDEX ON collections USING ivfflat (description_embedding vector_cosine_ops) WITH (lists = 100);
```

### Backfill Script

現有集合需一次性補跑 embedding，以 `title` 作為 embed 來源，確保所有集合都有向量覆蓋。

---

## 實作順序建議

1. DB migration + ORM model
2. `ai_service.embed_text()` + 單元測試
3. `collection_service` 接入 embed 觸發
4. Backfill script（對現有集合補算）
5. `crud/collections.py` 向量搜尋邏輯
6. 前端 description 欄位 UI
7. share 頁顯示 description
