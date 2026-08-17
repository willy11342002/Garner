/**
 * 手機版的「向下拖曳關閉」底部面板手勢。
 *
 * 原本 pages/app/trips.vue 與 components/item/ItemDetailModal.vue 各有一份幾乎
 * 逐字相同的實作（連中文註解、80px 門檻、-100vh 動畫都一樣），只差 touchEnd
 * 結尾有沒有重設樣式。這裡統一採用「有重設」的版本：面板若是 v-if 卸載，
 * 多做一次無害；若是重複使用同一個 DOM，少做就會下次打開時卡在畫面外。
 *
 * 用法：
 *   const { panelRef, onTouchStart, onTouchMove, onTouchEnd } = useSwipeToClose(doClose)
 *
 *   <div ref="panelRef"
 *        @touchstart.passive="onTouchStart"
 *        @touchmove.passive="onTouchMove"
 *        @touchend.passive="onTouchEnd">
 */

export interface SwipeToCloseOptions {
  /** 觸發關閉的下拉距離（px）。 */
  threshold?: number
  /** 關閉動畫時間（ms），要跟下面的 transition 對齊。 */
  closeMs?: number
  /** 彈回動畫時間（ms）。 */
  springMs?: number
}

export function useSwipeToClose(
  onClose: () => void | Promise<void>,
  options: SwipeToCloseOptions = {},
) {
  const { threshold = 80, closeMs = 200, springMs = 300 } = options

  const panelRef = ref<HTMLElement | null>(null)
  let startY = 0

  function onTouchStart(e: TouchEvent) {
    startY = e.touches[0].clientY
  }

  function onTouchMove(e: TouchEvent) {
    const panel = panelRef.value
    if (!panel) return

    const deltaY = e.touches[0].clientY - startY

    // 只有面板已捲到頂、而且是往下拉時才跟手；否則交還給內容捲動
    if (panel.scrollTop <= 0 && deltaY > 0) {
      panel.style.transition = 'none' // 拖曳時不要動畫，才能即時跟手
      panel.style.bottom = `-${deltaY}px`
    } else {
      panel.style.transition = ''
      panel.style.bottom = ''
    }
  }

  function onTouchEnd(e: TouchEvent) {
    const panel = panelRef.value
    if (!panel) return

    const deltaY = e.changedTouches[0].clientY - startY

    if (panel.scrollTop <= 0 && deltaY > threshold) {
      // 超過門檻：滑出畫面外，動畫結束後才真的關閉
      panel.style.transition = `bottom ${closeMs}ms ease-out`
      panel.style.bottom = '-100vh'
      setTimeout(() => {
        onClose()
        // 重設樣式，避免下次打開時面板還停在畫面外
        panel.style.transition = ''
        panel.style.bottom = ''
      }, closeMs)
    } else if (deltaY > 0) {
      // 有拉但沒過門檻：彈回原位
      panel.style.transition = `bottom ${springMs}ms cubic-bezier(0.32, 0.72, 0, 1)`
      panel.style.bottom = '0px'
      setTimeout(() => {
        panel.style.transition = ''
      }, springMs)
    }
  }

  return { panelRef, onTouchStart, onTouchMove, onTouchEnd }
}
