# Vela 前端串接任務清單

> 後端 CRUD API 已完成，前端依序完成以下任務。

---

## 基礎建設

- [x] **T01** `apps/web/types/api.ts` — 定義 TypeScript interface：`Item`、`Tag`、`Collection`、`CollectionDetail`、`User`
- [x] **T02** `apps/web/utils/apiFetch.ts` — 建立帶 Supabase JWT `Authorization: Bearer` header 的通用 fetch wrapper（封裝 `$fetch` / `useFetch`）

---

## Auth

- [x] **T03** `apps/web/stores/useAuthStore.ts` — 補齊：登入後呼叫 `GET /auth/me`，將 `{ id, email }` 存入 store；提供 `init()` action
- [x] **T04** `apps/web/middleware/auth.global.ts` — global middleware，只守 `/app/**`，未登入導向 `/login`

---

## Items

- [x] **T05** `apps/web/composables/useItems.ts` — 補齊所有方法：
  - `listItems()` → `GET /items/`
  - `createItem(data)` → `POST /items/`（body: `{ url, title?, raw_content? }`）
  - `getItem(id)` → `GET /items/{id}`
  - `updateItem(id, data)` → `PATCH /items/{id}`（body: `{ title }`）
  - `deleteItem(id)` → `DELETE /items/{id}`
  - `getItemTags(id)` → `GET /items/{id}/tags`
  - `attachTag(id, name)` → `POST /items/{id}/tags`（body: `{ name }`）
  - `detachTag(itemId, tagId)` → `DELETE /items/{id}/tags/{tag_id}`
- [ ] **T06** `apps/web/stores/useItemStore.ts` — 補齊：持有 `items: Item[]`，提供 `load()`、`add()`、`remove()`、`patch()` action，由 composable 呼叫

---

## Tags

- [ ] **T07** `apps/web/composables/useTags.ts` — 新建，包含：
  - `listTags()` → `GET /tags/`
  - `createTag(name)` → `POST /tags/`
  - `updateTag(id, name)` → `PATCH /tags/{id}`
  - `deleteTag(id)` → `DELETE /tags/{id}`
- [ ] **T08** `apps/web/stores/useTagStore.ts` — 補齊：持有 `tags: Tag[]`，提供 `load()`、`add()`、`remove()`、`patch()` action

---

## Collections

- [ ] **T09** `apps/web/composables/useCollections.ts` — 新建，包含：
  - `listCollections()` → `GET /collections/`
  - `createCollection(data)` → `POST /collections/`（body: `{ title, visibility, slug }`）
  - `getCollection(id)` → `GET /collections/{id}`（回傳含 items 的 detail）
  - `updateCollection(id, data)` → `PATCH /collections/{id}`
  - `deleteCollection(id)` → `DELETE /collections/{id}`
  - `addItem(collectionId, itemId)` → `POST /collections/{id}/items?item_id={item_id}`
  - `removeItem(collectionId, itemId)` → `DELETE /collections/{id}/items/{item_id}`
- [ ] **T10** `apps/web/stores/useCollectionStore.ts` — 新建：持有 `collections: Collection[]`，提供對應 action

---

## Search

- [ ] **T11** `apps/web/composables/useSearch.ts` — 新建：
  - `search(query)` → `GET /search/?q={query}`，回傳 `Item[]`

---

## 完成標準

每個任務完成後在 `[ ]` 改為 `[x]`。

**建議順序**：T01 → T02 → T03 → T04 → T05 → T06 → T07 → T08 → T09 → T10 → T11
