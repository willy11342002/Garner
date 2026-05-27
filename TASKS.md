# Vela Backend 實作任務清單

> 按照依賴順序排列，從底層往上實作。
> 完成一項就在 [ ] 改成 [x]。

---

## 階段一：Schema 補齊

- [x] **S1** `apps/api/app/schemas/collection.py` — 新建，定義 `CollectionCreate`、`CollectionRead`、`CollectionReadDetail`、`CollectionUpdate`

---

## 階段二：CRUD 層

> 只做 DB 讀寫，不放業務邏輯。

- [x] **C1** `apps/api/app/crud/users.py` — `get_by_id(db, user_id)`、`get_or_create(db, user_id, email, username)`
- [x] **C2** `apps/api/app/crud/items.py` — `get_all(db, user_id)`、`get_one(db, user_id, item_id)`、`create(db, user_id, content)`、`soft_delete(db, user_item)`
- [x] **C3** `apps/api/app/crud/tags.py` — `get_all`、`get_one`、`get_or_create`、`update`、`delete_tag`、`attach_tag`、`detach_tag`
- [x] **C4** `apps/api/app/crud/collections.py` — 新建，`get_all`、`get_one`、`create`、`update`、`delete_collection`、`add_item`、`remove_item`

---

## 階段三：Worker

- [x] **W1** `apps/api/app/workers/process_item.py` — 補齊 `process_item()`：將 summary + embedding 寫回 `content_objects`，更新 thumbnail URL

---

## 階段四：Service 層

> 業務邏輯唯一出口，呼叫 crud 與外部 API。

- [x] **SV1** `apps/api/app/services/item_service.py` — `create_item`（建立 content_object + user_item，觸發 background task）、`list_items`、`get_item`、`update_item`、`delete_item`
- [x] **SV2** `apps/api/app/services/search_service.py` — `semantic_search`：embed query → pgvector cosine similarity 查詢 content_objects

---

## 階段五：Router 層

> 只做參數接收與回傳，業務邏輯呼叫 service。

- [x] **R1** `apps/api/app/routers/auth.py` — `GET /auth/me`：回傳當前用戶資訊（需 auth）
- [x] **R2** `apps/api/app/routers/items.py` — 完整 CRUD + tag 附加/移除：
  - `GET /items/` — 列出用戶所有 items
  - `POST /items/` — 新增 item（觸發 background task）
  - `GET /items/{item_id}` — 取得單一 item
  - `PATCH /items/{item_id}` — 更新 item title
  - `DELETE /items/{item_id}` — 軟刪除
  - `GET /items/{item_id}/tags` — 列出 item 的 tags
  - `POST /items/{item_id}/tags` — 為 item 附加 tag
  - `DELETE /items/{item_id}/tags/{tag_id}` — 移除 item 的 tag
- [x] **R3** `apps/api/app/routers/tags.py` — Tag 管理：
  - `GET /tags/` — 列出用戶所有 tags
  - `POST /tags/` — 新增 tag
  - `PATCH /tags/{tag_id}` — 更新 tag 名稱
  - `DELETE /tags/{tag_id}` — 刪除 tag
- [x] **R4** `apps/api/app/routers/collections.py` — Collection 管理：
  - `GET /collections/` — 列出用戶所有 collections
  - `POST /collections/` — 新增 collection
  - `GET /collections/{collection_id}` — 取得 collection（含 items）
  - `PATCH /collections/{collection_id}` — 更新 title / visibility
  - `DELETE /collections/{collection_id}` — 刪除 collection
  - `POST /collections/{collection_id}/items` — 將 item 加入 collection
  - `DELETE /collections/{collection_id}/items/{item_id}` — 從 collection 移除 item
- [x] **R5** `apps/api/app/routers/search.py` — `GET /search/?q=` — 語意搜尋，回傳相關 items

---

## 完成條件

- [x] 所有 endpoint 有 auth guard（除了 health check）
- [x] 所有操作只能看到 / 修改自己的資料（user_id 隔離）
- [x] soft delete 正確：`deleted_at` 有值的 item 不出現在列表

---

## 備註

- `ai_service.embed()` 已修正為透過 OpenRouter 的 OpenAI-compatible endpoint，不需要額外 `OPENAI_API_KEY`
- `ItemCreate` 新增 `raw_content` 欄位（optional），Extension 可傳頁面內文加速摘要
- `ItemRead` 新增 `thumbnail_url` 欄位，`created_at` 改為 `saved_at`（對應 `user_items.saved_at`）
