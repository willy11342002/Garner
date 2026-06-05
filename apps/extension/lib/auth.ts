const SUPABASE_URL = process.env.PLASMO_PUBLIC_SUPABASE_URL!
const SUPABASE_ANON_KEY = process.env.PLASMO_PUBLIC_SUPABASE_ANON_KEY!

export interface StoredSession {
  access_token: string
  refresh_token: string
  expires_at: number  // unix seconds
}

export async function getStoredSession(): Promise<StoredSession | null> {
  const data = await chrome.storage.local.get(["access_token", "refresh_token", "expires_at"])
  if (!data.access_token) return null
  return {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    expires_at: data.expires_at,
  }
}

export async function setStoredSession(session: StoredSession): Promise<void> {
  await chrome.storage.local.set(session)
}

export async function clearStoredSession(): Promise<void> {
  await chrome.storage.local.remove(["access_token", "refresh_token", "expires_at"])
}

function isExpiringSoon(expires_at: number): boolean {
  return Date.now() / 1000 > expires_at - 60  // 60s buffer
}

async function doRefresh(refresh_token: string): Promise<StoredSession | null> {
  try {
    const resp = await fetch(
      `${SUPABASE_URL}/auth/v1/token?grant_type=refresh_token`,
      {
        method: "POST",
        headers: {
          apikey: SUPABASE_ANON_KEY,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ refresh_token }),
      }
    )
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

// 取得有效的 access_token，必要時自動 refresh
// 回傳 null 代表未登入或 refresh 失敗（refresh token 也過期了）
export async function getFreshToken(): Promise<string | null> {
  const session = await getStoredSession()
  if (!session) return null

  if (!isExpiringSoon(session.expires_at)) {
    return session.access_token
  }

  const newSession = await doRefresh(session.refresh_token)
  if (!newSession) {
    await clearStoredSession()
    return null
  }

  await setStoredSession(newSession)
  return newSession.access_token
}
