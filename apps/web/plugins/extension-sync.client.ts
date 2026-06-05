// 當 Supabase 在同一個 tab 自動 refresh token 時，通知 Chrome extension 的 content script 同步
export default defineNuxtPlugin(() => {
  const supabase = useSupabaseClient()

  supabase.auth.onAuthStateChange((_event, session) => {
    window.postMessage(
      {
        type: "GARNER_TOKEN_UPDATE",
        access_token: session?.access_token ?? null,
        refresh_token: session?.refresh_token ?? null,
        expires_at: session?.expires_at ?? null,
      },
      window.location.origin
    )
  })
})
