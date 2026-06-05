import type { PlasmoCSConfig } from "plasmo"

// 只在 vela.app（或本地開發）執行，document_start 確保在 Supabase JS 初始化前跑完
export const config: PlasmoCSConfig = {
  matches: [
    "https://vela.app/*",
    "http://localhost:3000/*",
  ],
  run_at: "document_start",
}

const SUPABASE_URL = process.env.PLASMO_PUBLIC_SUPABASE_URL!
const projectRef = new URL(SUPABASE_URL).hostname.split(".")[0]
const STORAGE_KEY = `sb-${projectRef}-auth-token`

interface SupabaseSession {
  access_token: string
  refresh_token: string
  expires_at: number
  [key: string]: unknown
}

function readWebSession(): SupabaseSession | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

async function sync() {
  const stored = await chrome.storage.local.get(["access_token", "refresh_token", "expires_at"])
  const web = readWebSession()

  const extAt: number = stored.expires_at ?? 0
  const webAt: number = web?.expires_at ?? 0

  if (extAt > webAt && stored.access_token) {
    // Extension 的 token 較新（extension 剛 refresh 過）
    // 把新 token 寫進 web app localStorage，讓 Supabase JS 初始化時讀到正確的值
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...web, ...stored }))
  } else if (webAt > extAt && web?.access_token) {
    // Web app 的 token 較新，同步到 chrome.storage
    await chrome.storage.local.set({
      access_token: web.access_token,
      refresh_token: web.refresh_token,
      expires_at: web.expires_at,
    })
  } else if (!stored.access_token && web?.access_token) {
    // 第一次：extension 還沒有 token，從 web app 複製
    await chrome.storage.local.set({
      access_token: web.access_token,
      refresh_token: web.refresh_token,
      expires_at: web.expires_at,
    })
  }
}

// 頁面載入時同步一次（主要用途：extension refresh 後，用戶回到 vela.app）
sync()

// 跨 tab：另一個 vela.app tab 更新了 token（例如 web app 自動 refresh）
window.addEventListener("storage", (e) => {
  if (e.key !== STORAGE_KEY) return
  if (!e.newValue) {
    // 用戶在另一個 tab 登出
    chrome.storage.local.remove(["access_token", "refresh_token", "expires_at"])
    return
  }
  try {
    const session: SupabaseSession = JSON.parse(e.newValue)
    if (session.access_token) {
      chrome.storage.local.set({
        access_token: session.access_token,
        refresh_token: session.refresh_token,
        expires_at: session.expires_at,
      })
    }
  } catch {}
})

// 同 tab：web app 的 Supabase JS 自動 refresh 後透過 postMessage 通知
window.addEventListener("message", (e) => {
  if (e.origin !== window.location.origin) return
  if (e.data?.type !== "VELA_TOKEN_UPDATE") return
  const { access_token, refresh_token, expires_at } = e.data
  if (access_token) {
    chrome.storage.local.set({ access_token, refresh_token, expires_at })
  } else {
    chrome.storage.local.remove(["access_token", "refresh_token", "expires_at"])
  }
})
