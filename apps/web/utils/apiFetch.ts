export function useApiFetch() {
  const config = useRuntimeConfig()
  const session = useSupabaseSession()

  return $fetch.create({
    baseURL: config.public.apiBase as string,
    onRequest({ options }) {
      const token = session.value?.access_token
      if (token) {
        options.headers = {
          ...options.headers,
          Authorization: `Bearer ${token}`,
        }
      }
    },
  })
}
