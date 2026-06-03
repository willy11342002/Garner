// 暫時用於 debug：把 SSR 錯誤完整印到 console（Vercel Logs 可看到）
// 確認問題後可移除此檔案
export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.hook('app:error', (error) => {
    console.error('[SSR Error]', {
      message: error.message,
      stack: error.stack,
      cause: error.cause,
    })
  })

  nuxtApp.hook('vue:error', (error) => {
    console.error('[Vue Error]', {
      message: (error as Error).message,
      stack: (error as Error).stack,
    })
  })
})
