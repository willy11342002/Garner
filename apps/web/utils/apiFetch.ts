export function useApiFetch() {
  const config = useRuntimeConfig()
  const session = useSupabaseSession()

  return $fetch.create({
    baseURL: config.public.apiBase as string,
    onRequest({ options }) {
      const token = session.value?.access_token
      if (token) {
        const merged: Record<string, string> = {
          ...(options.headers as unknown as Record<string, string>),
          Authorization: `Bearer ${token}`,
        }
        options.headers = merged as unknown as Headers
      }
    },
  })
}
