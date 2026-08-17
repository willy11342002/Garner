/**
 * 收藏項目的顯示用純函式。
 *
 * 這些原本散在 HomeTagView / HomeSemanticSearchView / ItemDetailModal /
 * chat / HomeChatPanel 各自複製一份（cardTitle 三份、tagColor 兩份、
 * SOURCE_LABELS 兩份，全部逐字相同）。純函式、無 Vue 依賴，放 utils。
 */

/**
 * 取網域名，去掉**開頭**的 `www.`。網址解析失敗時回傳 fallback。
 *
 * 注意是 `/^www\./` 而不是 `.replace('www.', '')`——後者會命中網址中任何位置的
 * `www.`，`my.www.site.com` 會被誤砍成 `my.site.com`。archive.vue 原本就是字串版。
 */
export function domainFromUrl(url: string, fallback = ''): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return fallback
  }
}

/** 卡片標題：沒有 title 就退回網域名稱。 */
export function cardTitle(url: string, title: string | null): string {
  return title || domainFromUrl(url)
}

/** 標籤配色代號，對應 CSS 的 .tag--a ~ .tag--e。 */
export const TAG_COLORS = ['a', 'b', 'c', 'd', 'e'] as const

export function tagColor(i: number): string {
  return TAG_COLORS[i % TAG_COLORS.length]
}

export type SourceKind = 'youtube' | 'ig' | 'tiktok' | 'facebook' | 'article'

/**
 * 從網址判斷來源平台。
 *
 * 只回傳「種類」而不是顯示文字：呼叫端的文案並不一致——首頁那幾個檢視走 i18n
 * （t('home.source_youtube')），ItemDetailModal 則是寫死英文。統一文案屬於 UI 決策，
 * 不在重構範圍內，所以這裡只共用判斷邏輯。
 */
export function sourceKindFromUrl(url: string): SourceKind {
  if (/youtu/.test(url)) return 'youtube'
  if (/instagram\.com/.test(url)) return 'ig'
  if (/tiktok\.com|vt\.tiktok\.com/.test(url)) return 'tiktok'
  if (/facebook\.com|fb\.watch/.test(url)) return 'facebook'
  return 'article'
}

/** 首頁各檢視用的 i18n key（有翻譯）。 */
export const SOURCE_I18N_KEYS: Record<SourceKind, string> = {
  youtube: 'home.source_youtube',
  ig: 'home.source_ig',
  tiktok: 'home.source_tiktok',
  facebook: 'home.source_facebook',
  article: 'home.source_article',
}

/**
 * 未翻譯的平台顯示名。ItemDetailModal 用這組（它一直是寫死英文，
 * 跟首頁走 i18n 不一致——這是既有的 UI 差異，統一與否屬產品決策，不在重構範圍）。
 */
export const SOURCE_DISPLAY_NAMES: Record<SourceKind, string> = {
  youtube: 'YouTube',
  ig: 'IG',
  tiktok: 'TikTok',
  facebook: 'Facebook',
  article: 'Article',
}

/** source_type 欄位（後端給的）對應的顯示文字。 */
export const SOURCE_LABELS: Record<string, string> = {
  youtube: '▶ YouTube',
  article: 'Article',
  ig: 'IG',
  tiktok: '♪ TikTok',
  facebook_reel: 'Facebook',
  facebook_post: 'Facebook',
}

export function sourceLabelFromType(type: string | null): string {
  return type ? (SOURCE_LABELS[type] ?? type) : 'Article'
}
