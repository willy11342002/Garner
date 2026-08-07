export {}

const WEB = process.env.PLASMO_PUBLIC_WEB_URL!

// 只有一般網頁存得進來（排除 chrome:// / about: / devtools:// 這類內部頁）
function isSavable(url?: string): boolean {
  return !!url && /^https?:\/\//.test(url)
}

// 點擊 toolbar icon → 開新分頁跳到網頁版的 quick-add，由網頁版呼叫 API。
// 擴充本身不接觸後端網域，之後後端搬家不會再讓擴充壞掉。
chrome.action.onClicked.addListener((tab) => {
  const url = isSavable(tab.url)
    ? `${WEB}/app/quick-add?url=${encodeURIComponent(tab.url!)}`
    : `${WEB}/app`
  chrome.tabs.create({ url })
})

// 舊版擴充會把 PAT 存在 chrome.storage，新版不再需要 token，升級時一併清掉
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.clear()
})
