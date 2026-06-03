# AI 版本化設計

> 當 AI 模型或 Prompt 更新時，如何處理既有用戶資料。

---

## 問題背景

Vela 使用 AI 對 item 做摘要、標籤、embedding。未來若更換模型或調整 prompt，識別結果會改變。需要決定：
- 舊 item 的識別結果要不要動？
- 新用戶 vs 舊用戶的體驗如何一致？
- 是否讓用戶自行決定重跑？

---

## 建議方案：版本標記 + 用戶自選重跑（MVP 先做 A，預留 B）

### 策略 A：Freeze 舊資料（預設）

改了 prompt/模型後，只對**新進來的 item** 用新版本處理，舊 item 保持原樣。

- 優點：零干擾，用戶不會突然發現摘要變了
- 缺點：同一個人的知識庫新舊混雜（品質落差）

### 策略 B：用戶自選重跑

在 item detail 頁提供「使用最新 AI 重新分析」按鈕，覆蓋舊結果並更新版本號。

### 策略 C：批次升級（未來考慮）

Background job 慢慢把所有 item 升到新版本，舊結果存 history 可回退。工程量較大，MVP 不做。

---

## 資料庫設計

在 `items` 表加版本欄位：

```sql
ai_summary_version    VARCHAR  -- e.g. "summary_v1", "summary_v2"
ai_tags_version       VARCHAR
ai_embedding_version  VARCHAR
```

或用獨立的 log 表（更靈活）：

```sql
CREATE TABLE ai_processing_log (
    item_id          UUID REFERENCES items(id),
    component        VARCHAR,  -- 'summary', 'tags', 'embedding'
    model_version    VARCHAR,  -- e.g. "claude-3-haiku", "gpt-4o"
    prompt_version   VARCHAR,  -- e.g. "summary_v2"
    processed_at     TIMESTAMPTZ
);
```

### Worker 寫入版本號

```python
# workers/process_item.py
CURRENT_SUMMARY_VERSION = "summary_v2"
CURRENT_EMBEDDING_VERSION = "embedding_v3"

item.ai_summary_version = CURRENT_SUMMARY_VERSION
item.ai_embedding_version = CURRENT_EMBEDDING_VERSION
```

---

## 重要注意事項

### Embedding 版本最敏感

換了 embedding 模型，維度或語意空間都會改變，**舊向量和新向量不能混用做語意搜尋**。升級 embedding 版本時必須選擇：

1. 全部 re-embed（確保語意搜尋一致性）
2. 分開索引舊版/新版（複雜度高，不建議）

Summary 和 Tags 混用沒有技術問題，只有品質落差，相對寬鬆。

---

## 執行優先序

| 階段 | 動作 |
|------|------|
| MVP  | `items` 表加 `ai_*_version` 欄位，新 item 寫入版本號，舊 item 不動 |
| 之後 | UI 加「重新分析」按鈕（策略 B） |
| 未來 | 考慮批次升級 + history（策略 C） |
