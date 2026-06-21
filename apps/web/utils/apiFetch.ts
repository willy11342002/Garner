export function useApiFetch() {
  const config = useRuntimeConfig()
  const session = useSupabaseSession()
  const supabase = useSupabaseClient()

  return $fetch.create({
    baseURL: config.public.apiBase as string,
    retry: 1,
    retryStatusCodes: [401],
    onRequest({ options }) {
      // 分頁不活躍就不發請求
      if (typeof document !== 'undefined' && document.hidden) {
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
      if (response.status === 401 && !(options as Record<string, unknown>)._refreshed) {
        ;(options as Record<string, unknown>)._refreshed = true
        try {
          await supabase.auth.refreshSession()
        } catch (error) {
          console.error('[apiFetch] Token refresh failed:', error)
        }
      }
    },
  })
}
