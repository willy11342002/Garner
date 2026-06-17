export function useApiFetch() {
  const config = useRuntimeConfig()
  const session = useSupabaseSession()
  const supabase = useSupabaseClient()

  return $fetch.create({
    baseURL: config.public.apiBase as string,
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
    async onResponseError({ response }) {
      // 401: token 過期，刷新 token
      if (response.status === 401) {
        try {
          await supabase.auth.refreshSession()
        } catch (error) {
          console.error('[apiFetch] Token refresh failed:', error)
        }
      }
    },
  })
}
