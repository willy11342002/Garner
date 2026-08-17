/**
 * 把 apiFetch（ofetch）拋出的錯誤分類，讓 UI 能給出有意義的訊息。
 *
 * 起因：trips 的自動儲存本來所有失敗都顯示同一句「儲存失敗，已復原」，
 * 422 驗證錯誤、500 伺服器錯誤、網路斷線全部長一樣。使用者不知道該怎麼辦，
 * 開發時也看不出發生什麼事——這次「新增卡片必定 500」的 bug 能活這麼久，
 * 這個籠統的 toast 是原因之一。
 *
 * 原則：
 * - 後端用 `HTTPException(detail="...")` 寫的字串是刻意給人看的，優先直接顯示
 * - 其餘依 status 分類，由呼叫端決定要顯示哪句翻譯
 * - 一律 console.error 原始錯誤，不要讓 toast 成為唯一線索
 */

export type ApiErrorKind =
  | 'network'      // 根本沒連上：斷網、CORS、伺服器沒起來
  | 'server'       // 5xx
  | 'forbidden'    // 401 / 403
  | 'notFound'     // 404
  | 'quota'        // 429
  | 'validation'   // 其餘 4xx
  | 'unknown'

/** 各分類對應的 i18n key（寫成表格而不是動態組字串，方便全站 grep）。 */
export const API_ERROR_I18N_KEYS: Record<ApiErrorKind, string> = {
  network: 'apiError.network',
  server: 'apiError.server',
  forbidden: 'apiError.forbidden',
  notFound: 'apiError.notFound',
  quota: 'apiError.quota',
  validation: 'apiError.validation',
  unknown: 'apiError.unknown',
}

export interface ClassifiedApiError {
  kind: ApiErrorKind
  /** 後端給的可讀訊息；有值就直接顯示，不要再套翻譯。 */
  detail: string | null
  status: number | null
}

export function classifyApiError(err: unknown, context = 'api'): ClassifiedApiError {
  console.error(`[${context}]`, err)

  const e = err as {
    response?: { status?: number }
    data?: { detail?: unknown }
    statusCode?: number
  }
  const status = e?.response?.status ?? e?.statusCode ?? null

  const rawDetail = e?.data?.detail
  const detail = typeof rawDetail === 'string' && rawDetail.trim() ? rawDetail : null

  let kind: ApiErrorKind
  if (status === null) kind = 'network'
  else if (status >= 500) kind = 'server'
  else if (status === 401 || status === 403) kind = 'forbidden'
  else if (status === 404) kind = 'notFound'
  else if (status === 429) kind = 'quota'
  else if (status >= 400) kind = 'validation'
  else kind = 'unknown'

  return { kind, detail, status }
}
