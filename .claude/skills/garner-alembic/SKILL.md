---
name: garner-alembic
description: 執行 Garner 專案的 Alembic 資料庫 migration 指令。當用戶提到 alembic、資料庫遷移、schema migration、upgrade、downgrade、revision、migrate、rollback、migration 歷程、migration stamp 時觸發。也在用戶要建立新 migration、套用 pending migration、查看目前 migration 狀態、或查看 migration 歷程時觸發。Use this skill whenever the user mentions alembic commands, database migrations, schema changes, or wants to create/apply/rollback migrations in the Garner project.
---

# Garner Alembic Migration Helper

處理 Garner 專案所有 Alembic 資料庫 migration 操作。

## 專案設定

- **所有指令必須在 `apps/api/` 目錄下執行**
- Config：`apps/api/alembic.ini`
- Migration 檔案：`apps/api/alembic/versions/`
- 命名慣例：`XXXX_description.py`（四位數字前綴，例如 `0002_add_user_avatar.py`）
- 使用 async SQLAlchemy + pgvector

## 執行流程

1. 解析用戶請求，判斷要執行哪個指令
2. 顯示即將執行的完整指令
3. 危險操作（downgrade、stamp）需先確認才執行
4. 執行後顯示輸出結果並說明影響

## 指令參考

### upgrade（套用 migration）

```bash
# 套用全部 pending migration（最常用）
cd apps/api && alembic upgrade head

# 只升一個版本
cd apps/api && alembic upgrade +1

# 升到指定版本
cd apps/api && alembic upgrade 0002
```

### downgrade（回滾）

```bash
# 回滾一個版本
cd apps/api && alembic downgrade -1

# 回滾到最初（完全清空 schema）
cd apps/api && alembic downgrade base
```

downgrade 會修改 DB schema，**一律要求用戶確認後才執行**。

### revision（建立新 migration）

```bash
cd apps/api && alembic revision -m "XXXX_描述"
```

**重要：禁止使用 `--autogenerate`**，一律手動撰寫 migration 內容。

#### 序號規則

1. 先查看現有最大序號：
   ```bash
   ls apps/api/alembic/versions/
   ```
2. 新序號 = 現有最大序號 + 1，補零至四位（例如最大是 `0017`，新的就是 `0018`）
3. 建立後**立即將檔案重新命名**為 `XXXX_description.py` 格式（alembic 預設產生隨機 hash 檔名）

#### 建立流程

```bash
# 1. 查看現有序號
ls apps/api/alembic/versions/

# 2. 建立空白 migration（不加 --autogenerate）
cd apps/api && alembic revision -m "描述"

# 3. 找到剛產生的檔案（在 alembic/versions/ 下，hash 開頭）
# 4. 重新命名為 XXXX_description.py
# 5. 在檔案內手動撰寫 upgrade() 和 downgrade() 函式
```

- 如果用戶沒有提供描述訊息，詢問：「這個 migration 要叫什麼名稱？（例如：add_user_avatar_url）」
- 建立後提醒用戶：
  - 新檔案在 `apps/api/alembic/versions/` 下，已重新命名為正確格式
  - **需要手動填寫 `upgrade()` 和 `downgrade()` 函式**
  - 建議先審查 migration 內容，再執行 `upgrade head`

### 查詢狀態

```bash
# 目前套用的版本
cd apps/api && alembic current

# 完整 migration 歷程（含詳細資訊）
cd apps/api && alembic history --verbose

# 所有 head 版本（正常應該只有一個）
cd apps/api && alembic heads
```

查詢類指令無需確認，直接執行。

### stamp（標記版本，不跑 migration）

```bash
# 標記為最新版本
cd apps/api && alembic stamp head

# 標記到指定版本
cd apps/api && alembic stamp 0001
```

stamp 用於：Supabase dashboard 直接建好 schema 後想跳過 migration、或修復卡住的 migration 狀態。**執行前要確認**，因為這會讓 alembic 認為 migration 已跑過。

## 確認規則

| 指令 | 需要確認 |
|------|---------|
| `upgrade head` / `upgrade +1` | 否，直接執行 |
| `downgrade -1` / `downgrade base` | **是**，明確說明會回滾哪個 migration |
| `stamp` | **是**，說明這不會修改 schema 只是更新版本記錄 |
| `current` / `history` / `heads` | 否，唯讀 |
| `revision`（不加 `--autogenerate`） | 否，只產生空白檔案不改 DB |

## 輸出格式

執行後：
- 顯示原始輸出
- `upgrade`/`downgrade`：說明哪些 migration 被套用或回滾
- `revision`：顯示新檔案路徑，提醒用戶填寫 `upgrade()` / `downgrade()` 後再執行 upgrade
- 發生錯誤（連線失敗、env 未設定）：清楚說明錯誤，建議檢查 `apps/api/.env` 和 `DATABASE_URL` 設定

## Windows 注意事項

在 Windows 環境，使用 Bash tool 執行 alembic 指令（而非 PowerShell），路徑使用正斜線：

```bash
cd apps/api && alembic upgrade head
```
