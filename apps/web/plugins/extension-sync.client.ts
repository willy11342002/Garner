// 當用戶在 web app 登出時，通知 Chrome extension 清除 PAT
export default defineNuxtPlugin(() => {
  const supabase = useSupabaseClient()

  supabase.auth.onAuthStateChange((event, _session) => {
    if (event === "SIGNED_OUT") {
      window.postMessage(
        { type: "GARNER_TOKEN_UPDATE", pat: null },
        window.location.origin
      )
    }
  })
})
