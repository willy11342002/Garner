/**
 * ItemDetailModal 的兩種輪詢：重新分析（reanalyze）與初始分析。
 *
 * 兩者都是「打 POST 觸發背景工作 → 每 2 秒問一次 /items/{id} 直到 note_status
 * 變成 complete/error 或次數用完」。輪詢請求都帶 skipWhenHidden：分頁在背景時
 * 不需要繼續問，省額度也避免喚醒機器（見 utils/apiFetch.ts 的說明）。
 *
 * 需要元件的三個東西：
 * - `itemId`：要輪詢哪一筆
 * - `fetchedItem`：輪詢到結果後要寫回去
 * - `isEditingNotes`：使用者正在編輯筆記時不要覆蓋他打到一半的內容
 */

import type { Ref } from 'vue'
import type { Item } from '~/types/api'

export function useItemPolling(
  itemId: Ref<string | null | undefined>,
  fetchedItem: Ref<Item | null>,
  isEditingNotes: Ref<boolean>,
) {
  const apiFetch = useApiFetch()
  const { resumeItem } = useItems()

  // ── Reanalyze (stage 3 → 5) ─────────────────────────────────────────────────
  const reanalyzing = ref(false)
  const showReanalyzeConfirm = ref(false)
  const reanalyzeQuotaError = ref(false)
  let _reanalyzePollTimer: ReturnType<typeof setTimeout> | null = null

  function requestReanalyze() {
    reanalyzeQuotaError.value = false
    showReanalyzeConfirm.value = true
  }

  async function reanalyze() {
    if (!itemId.value) return
    reanalyzing.value = true
    reanalyzeQuotaError.value = false
    try {
      await apiFetch(`/items/${itemId.value}/reanalyze`, { method: 'POST' })
      showReanalyzeConfirm.value = false
      pollReanalyze()
    } catch (err: any) {
      reanalyzing.value = false
      if (err?.response?.status === 429) {
        reanalyzeQuotaError.value = true  // keep dialog open to show the message
      } else {
        showReanalyzeConfirm.value = false
      }
    }
  }

  function pollReanalyze(maxAttempts = 60) {
    let attempts = 0
    async function poll() {
      if (!itemId.value || attempts >= maxAttempts) {
        reanalyzing.value = false
        _reanalyzePollTimer = null
        return
      }
      attempts++
      try {
        const updated = await apiFetch<Item>(`/items/${itemId.value}`, { skipWhenHidden: true })
        const done = updated.note_status === 'complete' && updated.embedding_status === 'complete'
        const failed = updated.note_status === 'error'
        if (done || failed) {
          if (done) fetchedItem.value = updated
          reanalyzing.value = false
          _reanalyzePollTimer = null
          return
        }
      } catch { /* 靜默：單次輪詢失敗不中斷，下面照樣排下一輪 */ }
      _reanalyzePollTimer = setTimeout(poll, 2000)
    }
    poll()
  }

  // ── Initial-analysis polling (item opened while still being processed) ──────
  let _analysisPollTimer: ReturnType<typeof setTimeout> | null = null

  function stopAnalysisPoll() {
    if (_analysisPollTimer) { clearTimeout(_analysisPollTimer); _analysisPollTimer = null }
  }

  function pollAnalysis(maxAttempts = 90) {
    stopAnalysisPoll()
    let attempts = 0
    async function poll() {
      if (!itemId.value || attempts >= maxAttempts) { _analysisPollTimer = null; return }
      attempts++
      try {
        const updated = await apiFetch<Item>(`/items/${itemId.value}`, { skipWhenHidden: true })
        if (!isEditingNotes.value) fetchedItem.value = updated
        if (updated.note_status === 'complete' || updated.note_status === 'error') {
          _analysisPollTimer = null
          return
        }
      } catch { /* 靜默：單次輪詢失敗不中斷，下面照樣排下一輪 */ }
      _analysisPollTimer = setTimeout(poll, 2000)
    }
    _analysisPollTimer = setTimeout(poll, 2000)
  }

  // ── Retry a stalled ingest ──────────────────────────────────────────────────
  const retrying = ref(false)

  async function retryIngest() {
    if (!itemId.value || retrying.value) return
    retrying.value = true
    try {
      await resumeItem(itemId.value)
      pollAnalysis()
    } finally {
      retrying.value = false
    }
  }

  onUnmounted(() => {
    if (_reanalyzePollTimer) clearTimeout(_reanalyzePollTimer)
    stopAnalysisPoll()
  })

  return {
    reanalyzing,
    showReanalyzeConfirm,
    reanalyzeQuotaError,
    requestReanalyze,
    reanalyze,
    pollAnalysis,
    stopAnalysisPoll,
    retrying,
    retryIngest,
  }
}
