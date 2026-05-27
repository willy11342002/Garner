# Contributing

開發規範文件。

---

## 分支策略（Git Flow）

```
main        # 生產環境，只接受來自 release/* 的 merge
develop     # 整合分支，所有 feature 從這裡開
feature/*   # 新功能
release/*   # 準備上線
hotfix/*    # 緊急修復，從 main 開
```

### 分支命名

```
feature/item-save-flow
feature/search-semantic
release/1.2.0
hotfix/openrouter-401-handling
```

---

## Commit Message

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
<type>(<scope>): <description>

feat(api): add background task for item processing
fix(web): correct tag color rendering on dark mode
chore(extension): update plasmo to 0.90.0
docs(api): update env variable list
refactor(api): extract ai_service from item_service
```

**type 清單：**

| type | 用途 |
|------|------|
| `feat` | 新功能 |
| `fix` | 修 bug |
| `refactor` | 重構（不影響功能） |
| `docs` | 文件 |
| `chore` | 依賴更新、設定調整 |
| `test` | 測試 |
| `perf` | 效能改善 |

**scope** 填服務名稱：`api`、`web`、`extension`、`types`

---

## 版本號（Semantic Versioning）

各服務獨立維護，格式 `MAJOR.MINOR.PATCH`：

- `PATCH`：bug fix
- `MINOR`：新功能，向下相容
- `MAJOR`：breaking change

版本號位置：
- `apps/web/package.json`
- `apps/api/pyproject.toml`
- `apps/extension/package.json`

---

## Pull Request

- PR 目標分支：`develop`（hotfix 例外，目標為 `main`）
- PR 標題格式同 commit message
- Merge 前需通過 CI
- 使用 **Squash and merge**
