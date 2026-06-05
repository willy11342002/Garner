const KEY_PAT = "pat"

export async function getStoredPat(): Promise<string | null> {
  const data = await chrome.storage.local.get(KEY_PAT)
  return data[KEY_PAT] ?? null
}

/**
 * 取得有效的 Bearer token（PAT）。
 * 沒有 PAT → 回傳 null（未登入）
 */
export async function getFreshToken(): Promise<string | null> {
  const pat = await getStoredPat()
  console.log("[auth] stored PAT:", pat ? pat.slice(0, 20) + "…" : null)
  return pat
}

/**
 * 判斷是否已登入（有 PAT 即可）
 */
export async function getStoredSession(): Promise<{ valid: true } | null> {
  const pat = await getStoredPat()
  return pat ? { valid: true } : null
}

/**
 * 登出：清除所有 chrome.storage 內容
 */
export async function clearStoredSession(): Promise<void> {
  await chrome.storage.local.clear()
}
