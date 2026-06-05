const SUPABASE_URL = process.env.PLASMO_PUBLIC_SUPABASE_URL!
const SUPABASE_ANON_KEY = process.env.PLASMO_PUBLIC_SUPABASE_ANON_KEY!
const API = process.env.PLASMO_PUBLIC_API_BASE_URL!

// ── Storage keys ──────────────────────────────────────────────
const KEY_PAT = "vela_pat"

// 舊版 JWT keys（用於遷移，遷移後清除）
const JWT_KEYS = ["access_token", "refresh_token", "expires_at"]

// ── PAT helpers ───────────────────────────────────────────────

export async function getStoredPat(): Promise<string | null> {
  const data = await chrome.storage.local.get(KEY_PAT)
  return data[KEY_PAT] ?? null
}

async function storePat(pat: string): Promise<void> {
  await chrome.storage.local.set({ [KEY_PAT]: pat })
  // 清除舊版 JWT 資料
  await chrome.storage.local.remove(JWT_KEYS)
}

export async function clearStoredPat(): Promise<void> {
  await chrome.storage.local.remove([KEY_PAT, ...JWT_KEYS])
}

// ── 舊版 JWT（只用來做一次性遷移） ────────────────────────────

interface StoredJwt {
  access_token: string
  refresh_token: string
  expires_at: number
}

async function getStoredJwt(): Promise<StoredJwt | null> {
  const data = await chrome.storage.local.get(JWT_KEYS)
  if (!data.access_token) return null
  return {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    expires_at: data.expires_at,
  }
}

function isJwtExpiringSoon(expires_at: number): boolean {
  return Date.now() / 1000 > expires_at - 60
}

async function refreshJwt(refresh_token: string): Promise<StoredJwt | null> {
  try {
    const resp = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=refresh_token`, {
      method: "POST",
      headers: { apikey: SUPABASE_ANON_KEY, "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token }),
    })
    if (!resp.ok) return null
    const data = await resp.json()
    return {
      access_token: data.access_token,
      refresh_token: data.refresh_token,
      expires_at: data.expires_at,
    }
  } catch {
    return null
  }
}

async function getFreshJwtToken(): Promise<string | null> {
  const jwt = await getStoredJwt()
  if (!jwt) return null
  if (!isJwtExpiringSoon(jwt.expires_at)) return jwt.access_token
  const refreshed = await refreshJwt(jwt.refresh_token)
  if (!refreshed) return null
  await chrome.storage.local.set(refreshed)
  return refreshed.access_token
}

// ── PAT 換取（用 JWT 換 PAT，一次性）────────────────────────

async function exchangeJwtForPat(jwtToken: string): Promise<string | null> {
  try {
    const resp = await fetch(`${API}/auth/pat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${jwtToken}`,
      },
      body: JSON.stringify({ name: "Chrome Extension" }),
    })
    if (!resp.ok) return null
    const data = await resp.json()
    return data.token ?? null
  } catch {
    return null
  }
}

// ── 公開 API ─────────────────────────────────────────────────

/**
 * 取得有效的 Bearer token（PAT）。
 * - 已有 PAT → 直接回傳
 * - 有舊版 JWT → 自動換成 PAT 並儲存，回傳新 PAT
 * - 兩者都沒有 → 回傳 null（未登入）
 */
export async function getFreshToken(): Promise<string | null> {
  // 優先：已有 PAT
  const pat = await getStoredPat()
  if (pat) return pat

  // 遷移路徑：有舊版 JWT → 換成 PAT
  const jwtToken = await getFreshJwtToken()
  if (!jwtToken) return null

  const newPat = await exchangeJwtForPat(jwtToken)
  if (!newPat) {
    // 換取失敗，暫時回傳 JWT 讓本次呼叫可以繼續
    return jwtToken
  }

  await storePat(newPat)
  return newPat
}

/**
 * 判斷是否已登入（有 PAT 或舊版 JWT 其一即可）
 */
export async function getStoredSession(): Promise<{ valid: true } | null> {
  const pat = await getStoredPat()
  if (pat) return { valid: true }

  const jwt = await getStoredJwt()
  if (jwt) return { valid: true }

  return null
}

/**
 * 登出：清除所有 token
 */
export async function clearStoredSession(): Promise<void> {
  await clearStoredPat()
}
