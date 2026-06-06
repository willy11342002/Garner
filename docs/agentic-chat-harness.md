# Chat — Agentic RAG + Harness 演進方向

> 建立時間：2026-06-06
> 背景：朋友建議 RAG 要走 agentic，並在 pipeline 末端加 harness 穩定品質。

---

## 現況（已實作）

`chat_service.stream_reply` 目前是**單輪 agentic pipeline**：

```
用戶訊息
  → Step 1: plan_tools（AI 決定要呼叫哪些工具）
  → Step 2: 執行 tool（semantic_search / structured_filter）
  → Step 3: chat_stream（用 chunks + summary 組 prompt 回覆）
  → 儲存訊息 + 壓縮 memory_summary（每 10 則）
```

這已是 agentic 的雛形：AI 自己規劃 tool call，不是固定流程。

---

## 缺少的部分

### 1. Agentic 回圈（Reflect & Re-retrieve）

目前只跑一輪，AI 無法判斷「檢索結果不夠好，需要換策略再查一次」。

目標行為：
```
plan_tools → execute → [評估：結果夠嗎？] → 不夠 → 重新 plan → re-execute（最多 N 輪）
                                          ↓ 夠
                                      chat_stream → done
```

實作方向：
- 在 Step 2 之後加一個 `reflect_retrieval()` 步驟
- 讓 AI 評估 `tool_result` 的 count 和 titles 是否足以回答問題
- 若不足（count=0 或主題偏差），重新 plan 並換參數再查
- 最多重試 2 輪，避免無限循環

### 2. Harness 評估層（Response Quality Gate）

在 Step 3（chat_stream）完成後，加一個品質評分步驟再 emit `done`。

```
chat_stream 完成
  → harness_eval（非 streaming，背景或快速 LLM call）
      - 檢查：回覆是否有根據 sources？
      - 檢查：是否直接回答了用戶問題？
      - 產出：quality_score（0–1）+ flags（hallucination / off-topic / no_evidence）
  → 若 quality_score < threshold → 觸發重新生成 或 標記警告
  → emit done（帶 quality metadata）
```

---

## 技術選型

| 元件 | 選項 | 建議 |
|------|------|------|
| Agentic 框架 | LangGraph / 自製 | **自製**（現有 FastAPI 架構已夠，LangGraph 引入複雜度不值得） |
| Harness eval | 另一個 LLM call / rule-based | **輕量 LLM call**（用 haiku/flash 級模型，速度快成本低） |
| 評估時機 | 同步（阻塞 done）/ 異步（背景） | **背景任務**（不影響 streaming 延遲，結果記在 process_log） |

---

## 實作優先順序

1. **Harness（先做）**：實作簡單，立刻有品質監控數據，不影響現有流程
2. **Agentic 回圈（後做）**：影響 latency，需要先有 harness 數據確認必要性

---

## Harness 最小實作草案

```python
# app/services/chat_harness.py

async def eval_response(
    user_query: str,
    sources: list[dict],
    reply: str,
) -> dict:
    """
    輕量品質評估。回傳 quality_score 和 flags。
    用 haiku/flash 模型，timeout 2s。
    """
    ...

# 在 chat_service.py 的背景任務中呼叫：
background_tasks.add_task(
    _run_harness_eval,
    message_id, user_content, sources_json, reply_text
)
```

評估結果存在 `chat_messages.process_log` 的 `harness` 欄位，方便日後分析。

---

## 相關檔案

| 檔案 | 說明 |
|------|------|
| `apps/api/app/services/chat_service.py` | 現有 agentic pipeline |
| `apps/api/app/services/ai_service.py` | LLM call 層 |
| `apps/api/app/crud/chat.py` | 訊息存取、memory_summary |
