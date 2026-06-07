import type { PlasmoCSConfig } from "plasmo"

export const config: PlasmoCSConfig = {
  matches: [
    "https://garner.app/*",
    "http://localhost:3000/*",
  ],
  run_at: "document_start",
}

// 讓 web app 能偵測 Extension 是否已安裝
document.documentElement.setAttribute("data-garner-ext", "true")

// 接收 web app 推送的 PAT
window.addEventListener("message", (e) => {
  if (e.origin !== window.location.origin) return
  if (e.data?.type !== "GARNER_TOKEN_UPDATE") return

  const { pat } = e.data
  if (pat) {
    chrome.storage.local.set({ pat })
  } else {
    // web app 登出時清除 extension 所有資料
    chrome.storage.local.clear()
  }
})
