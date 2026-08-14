// 縮圖載入失敗時的共用回退狀態。
// 縮圖可能來自平台原圖或 Supabase Storage 快取，兩者都會過期或被擋；
// 失敗的 <img> 會留下破圖 icon，改成記住失敗的 URL，讓 template 退回無圖時的 placeholder。
// 模組層級共享：同一張圖在卡片壞過，開 modal 時就不用再失敗一次。
const brokenUrls = reactive(new Set<string>())

export function useImageFallback() {
  return {
    isBroken: (url?: string | null) => !!url && brokenUrls.has(url),
    markBroken: (url?: string | null) => { if (url) brokenUrls.add(url) },
  }
}
