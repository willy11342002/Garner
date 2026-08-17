// 讓呼叫端可以帶 skipWhenHidden。NitroFetchOptions 繼承自 ofetch 的 FetchOptions，
// 所以擴充這個介面之後 apiFetch(url, { skipWhenHidden: true }) 就有型別。
declare module 'ofetch' {
  interface FetchOptions {
    /**
     * 分頁不可見時放棄這個請求（會 reject）。**只給輪詢用**。
     * 使用者觸發或掛載時的載入絕對不要帶——請求被靜默丟掉會讓畫面卡在載入中。
     */
    skipWhenHidden?: boolean
  }
}

export function useApiFetch() {
  const config = useRuntimeConfig()
  const session = useSupabaseSession()
  const supabase = useSupabaseClient()

  return $fetch.create({
    baseURL: config.public.apiBase as string,
    retry: 1,
    retryStatusCodes: [401],
    onRequest({ options }) {
      // 分頁不可見時放棄請求——**只對明確標記的輪詢生效**，預設一律送出。
      //
      // 這個檢查原本是無條件的，於是掛載當下分頁不可見（背景開新分頁、開完就切走、
      // 瀏覽器還原分頁）時，/app 的初始 items 載入會被靜默丟掉、連請求都不送，
      // 頁面永久停在「載入中」也不會自己恢復。pages/app/trips.vue 早就為此加了
      // visibilitychange 補救，但知識首頁沒有。
      //
      // 靜默丟掉請求對輪詢是合理的（省額度、避免背景喚醒機器），對使用者觸發或
      // 掛載時的載入則是錯的，所以改成 opt-in：呼叫端要跳過就自己帶 skipWhenHidden。
      const skipWhenHidden = (options as unknown as Record<string, unknown>).skipWhenHidden === true
      if (skipWhenHidden && typeof document !== 'undefined' && document.hidden) {
        throw new Error('Page is not active')
      }

      const token = session.value?.access_token
      if (token) {
        const merged: Record<string, string> = {
          ...(options.headers as unknown as Record<string, string>),
          Authorization: `Bearer ${token}`,
        }
        options.headers = merged as unknown as Headers
      }
    },
    async onResponseError({ response, options }) {
      // 401: token 過期，刷新 token，讓 ofetch 重試時 onRequest 帶新 token
      // _refreshed flag 確保每個請求只 refresh 一次，避免重試失敗後再次觸發
      if (response.status === 401 && !(options as unknown as Record<string, unknown>)._refreshed) {
        ;(options as unknown as Record<string, unknown>)._refreshed = true
        try {
          await supabase.auth.refreshSession()
        } catch (error) {
          console.error('[apiFetch] Token refresh failed:', error)
        }
      }
    },
  })
}
