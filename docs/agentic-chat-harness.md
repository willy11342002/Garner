# Chat — Agentic RAG + Harness 演進方向

> 建立時間：2026-06-06 ／ 最後更新：2026-06-14
> 背景：朋友建議 RAG 要走 agentic，並在 pipeline 末端加 harness 穩定品質。

---

## 現況（已實作）

Chat 已改用 **原生 LLM tool calling 的 agentic loop**。原本手寫的 `plan_tools → execute → chat_stream` 固定流程已移除。

進入點：`chat_service.stream_reply` → `ai_service.agentic_chat_stream(user_content, history, context_summary, execute_tool)`

```
用戶訊息
  → LLM 原生 tool calling loop（模型自行決定要不要呼叫工具、呼叫幾次）
      - search          # 語意 / 結構化檢索，回傳 items + chunk 文字
      - create_article  # 生成文章草稿
  → 模型用工具結果 streaming 回覆
      （emit: tool_call | tool_result | sources | delta | done）
  → 存訊息；每 8 則於背景壓縮 context_summary
```

**Reflect & Re-retrieve 已由原生 tool calling 自然吸收**：檢索結果不足時，模型會自己換 query / 參數再呼叫一次 `search`，不需要手寫「評估 → 重試」步驟。（這是舊版文件列為「缺少的部分」的 agentic 回圈，現已不必另外實作。）

### 相關檔案

| 檔案 | 說明 |
|------|------|
| `apps/api/app/services/chat_service.py` | `stream_reply`、`execute_tool`、context 壓縮 |
| `apps/api/app/services/ai_service.py` | `agentic_chat_stream`（原生 tool calling 迴圈）、`embed` |
| `apps/api/app/crud/chat.py` | 訊息存取、context_summary |

---

## 待實作：Harness 評估層（Response Quality Gate）

> 狀態：**尚未實作**。與編排方式無關——它評估的是「輸出品質」，原生 tool calling 下一樣適用。

目的：抓 hallucination / 無根據作答 / 答非所問，作為**可觀測性與護欄**，不是編排。

> ⚠️ 原生 tool calling + 良好 prompt 已把亂編風險壓低。**建議實際觀察到品質問題、或樣本累積到一定量再做**，否則屬 premature optimization。

### 設計（背景執行，不阻塞 streaming）

```
stream_reply 完成
  → background_tasks 丟一個輕量 LLM eval（haiku 級，timeout ~2s）
      - 回覆是否有根據 sources？
      - 是否直接回答了用戶問題？
      - 產出 quality_score（0–1）+ flags（hallucination / off-topic / no_evidence）
  → 結果寫入 chat_messages.process_log 的 harness 欄位（先純觀測）
  → 累積數據後再決定是否加「低分觸發重生成」
```

### 最小實作草案

```python
# app/services/chat_harness.py
async def eval_response(user_query: str, sources: list[dict], reply: str) -> dict:
    """輕量品質評估，回傳 quality_score 和 flags。用 haiku / flash 模型。"""
    ...

# chat_service.py，stream_reply 末端：
background_tasks.add_task(
    _run_harness_eval, message_id, user_content, sources_json, reply_text
)
```

### 技術選型

| 元件 | 建議 |
|------|------|
| Eval 方式 | 輕量 LLM call（haiku / flash 級，速度快成本低） |
| 評估時機 | 背景任務（不影響 streaming 延遲，結果記在 `process_log`） |
| Agentic 框架 | 自製即可（現有 FastAPI 架構已夠，不引入 LangGraph） |
