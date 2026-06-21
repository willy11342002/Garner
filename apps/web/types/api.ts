export interface User {
  id: string
  email: string | null
  username: string
  avatar_url: string | null
  plan?: 'free' | 'pro'
  plan_expires_at?: string | null
}

export interface Item {
  id: string
  content_id: string | null
  url: string
  title: string | null
  notes_md: string | null
  thumbnail_url: string | null
  saved_at: string
  deleted_at: string | null
  parsed_at: string | null
  status: string | null
  source_type: string | null
  tags: Tag[]
  note_status: string | null
  embedding_status: string | null
  landmarks_status: string | null
}

export interface ArticleUpdate {
  title?: string
  notes_md?: string
}

export interface ItemCreate {
  url?: string        // omit to create an in-app note
  title?: string
  raw_content?: string
}

export interface ItemUpdate {
  title?: string
  status?: 'active' | 'archived' | 'deleted'
  notes_md?: string
}

export type CollectionVisibility = 'private' | 'link' | 'public'

export interface Tag {
  id: string
  name: string
  name_i18n: Record<string, string> | null
  item_count: number
}

export interface TagCreate {
  name: string
}

export interface TagUpdate {
  name: string
}

export interface Collection {
  id: string
  title: string
  visibility: CollectionVisibility
  slug: string
  fork_count: number
  created_at: string
}

export interface CollectionDetail extends Collection {
  items: Item[]
}

export interface CollectionCreate {
  title: string
  visibility?: CollectionVisibility
  slug: string
}

export interface CollectionUpdate {
  title?: string
  visibility?: CollectionVisibility
}

export interface CollectionRead {
  id: string
  title: string
  visibility: string
  slug: string
  fork_count: number
  created_at: string
}

export interface CollectionShareItem {
  id: string
  url: string
  title: string | null
  thumbnail_url: string | null
  source_type: string | null
}

export interface CollectionShareRead {
  id: string
  title: string
  slug: string
  fork_count: number
  created_at: string
  author_username: string
  author_avatar_url: string | null
  items: CollectionShareItem[]
}

export interface CollectionForkCreate {
  title?: string
  content_ids?: string[]
}

export interface PublicCollectionRead {
  id: string
  title: string
  slug: string
  fork_count: number
  created_at: string
  item_count: number
  author_username: string
  author_avatar_url: string | null
  source_tag_name: string | null
  cover_thumbnails: (string | null)[]
}

// Focus (AI synthesis search)
export interface FocusSource {
  id: string
  url: string
  title: string | null
  thumbnail_url: string | null
  source_type: string | null
  saved_at: string
}

export interface FocusResult {
  synthesis: string
  sources: FocusSource[]
}

// Custom synthesis
export interface SynthesizeResult {
  content: string   // Markdown
  sources: FocusSource[]
}

// Surprise (AI insights)
export type InsightType = 'connection' | 'forgotten' | 'trend'

export interface InsightItem {
  id: string
  url: string
  title: string | null
  thumbnail_url: string | null
  source_type: string | null
}

export interface TrendBar {
  label: string
  pct: number
}

export interface Insight {
  type: InsightType
  badge: string
  title: string
  body: string
  when: string
  items: InsightItem[]
  trend_bars: TrendBar[]
}

export interface SurpriseResult {
  insights: Insight[]
}

// Chain exploration
export interface ChainItem {
  id: string
  url: string
  title: string | null
  thumbnail_url: string | null
  source_type: string | null
  saved_at: string
}

export interface ChainHopAnalysis {
  connection: string
  ideation: string
  question: string
}

export interface ChainHop {
  item: ChainItem
  analysis: ChainHopAnalysis | null  // null for starting node
  candidates: ChainItem[]            // next hop options at this node
}

// AI Chat
export interface ChatFolder {
  id: string
  name: string
  created_at: string
}

export interface ChatSession {
  id: string
  folder_id: string | null
  title: string | null
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  cited_item_ids: string[] | null
  process_log: { thinking: string; steps: Array<{ toolCall: Record<string, any>; toolResult: { count: number; titles: string[] } | null }> } | null
  created_at: string
}

export interface ChatSessionDetail extends ChatSession {
  messages: ChatMessage[]
}

export interface ChatSource {
  id: string
  url: string
  title: string | null
  thumbnail_url: string | null
  source_type: string | null
  locations?: string[]
}

export interface QuotaItem {
  used: number
  limit: number | null  // null = unlimited
}

/** chat 產出報告後回傳的精簡草稿（用於聊天內卡片）。 */
export interface ReportDraft {
  id: string
  title: string
  summary?: string | null
}

/** chat 產出旅遊行程後回傳的精簡草稿（trip_draft 事件，用於聊天內卡片）。 */
export interface TripDraft {
  id: string
  title: string
  summary?: string | null
  item_count?: number
}

/** 報告的來源知識（provenance）。 */
export interface ReportSource {
  id: string
  title: string | null
  url: string | null
  thumbnail_url: string | null
  source_type: string | null
}

export interface Report {
  id: string
  title: string
  body_md: string
  summary: string | null
  sources: ReportSource[]
  last_edited_by: string | null
  created_at: string
  updated_at: string
}

export interface ReportListItem {
  id: string
  title: string
  summary: string | null
  source_count: number
  last_edited_by: string | null
  created_at: string
  updated_at: string
}

export interface PaginatedResult<T> {
  items: T[]
  page: number
  page_size: number
  has_next: boolean
}

export interface ItemPage {
  items: Item[]
  total: number
  page: number
  page_size: number
}

export interface UsageSummary {
  plan: string
  period_end: string | null
  saves: QuotaItem
  chat: QuotaItem
  synthesis: QuotaItem
  search_enabled: boolean
  video_max_minutes: number
}

export type NotificationType = 'item_processed' | 'item_failed' | 'system' | 'trip_invited'

export interface Notification {
  id: string
  type: NotificationType
  title: string
  body: string | null
  item_id: string | null
  trip_id: string | null
  is_read: boolean
  created_at: string
}

// ── Trip types ────────────────────────────────────────────────────────────────

export type TripRole = 'owner' | 'editor' | 'viewer'

export interface TripMember {
  id: string
  member_user_id: string
  email: string
  display_name: string | null
  role: 'editor' | 'viewer'
  created_at: string
}

export interface TripMemberCreate {
  email: string
  role?: 'editor' | 'viewer'
}

export interface TripMemberUpdate {
  role: 'editor' | 'viewer'
}

export interface TripInviteLinkUpdate {
  role?: 'editor' | 'viewer'
}

export interface TripTag {
  id: string
  name: string
  color: string | null
}

export interface TripTagCreate {
  name: string
  color?: string | null
}

export interface TripTagUpdate {
  name?: string | null
  color?: string | null
}

export interface TripItemTag {
  trip_tag_id: string
  name: string
  color: string | null
}

/** 卡片關聯的知識（user_items）。 */
export interface TripItemSource {
  id: string
  title: string | null
  thumbnail_url: string | null
  source_type: string | null
}

export interface TripItem {
  id: string
  trip_id: string
  user_item_id: string | null
  kind: 'event' | 'reference'
  title: string
  emoji: string | null
  note: string | null
  category: string | null
  booked: boolean
  ticket_url: string | null
  start_date: string | null
  end_date: string | null
  start_time: string | null
  end_time: string | null
  order_index: number
  place_name: string | null
  lat: number | null
  lng: number | null
  geocoding_status: string
  tags: TripItemTag[]
  sources: TripItemSource[]
  created_at: string
  updated_at: string
}

export interface TripItemCreate {
  user_item_id?: string | null
  kind?: 'event' | 'reference'
  title: string
  emoji?: string | null
  note?: string | null
  category?: string | null
  booked?: boolean
  ticket_url?: string | null
  start_date?: string | null
  end_date?: string | null
  start_time?: string | null
  end_time?: string | null
  order_index?: number
  place_name?: string | null
  lat?: number | null
  lng?: number | null
}

export interface TripItemUpdate {
  kind?: string | null
  title?: string | null
  emoji?: string | null
  note?: string | null
  category?: string | null
  booked?: boolean | null
  ticket_url?: string | null
  start_date?: string | null
  end_date?: string | null
  start_time?: string | null
  end_time?: string | null
  order_index?: number | null
  place_name?: string | null
  lat?: number | null
  lng?: number | null
  tag_ids?: string[] | null
}

export interface TripItemReorderEntry {
  id: string
  order_index: number
}

export interface TripItemReorderRequest {
  items: TripItemReorderEntry[]
}

export interface TripSourceItem {
  id: string
  title: string | null
  thumbnail_url: string | null
  source_type: string | null
}

export interface Trip {
  id: string
  title: string
  summary: string | null
  start_date: string | null
  end_date: string | null
  last_edited_by: string | null
  sources: TripSourceItem[]
  items: TripItem[]
  my_role: TripRole
  members: TripMember[]
  invite_token: string | null  // only filled for owner
  invite_role: string
  created_at: string
  updated_at: string
}

export interface TripListItem {
  id: string
  title: string
  summary: string | null
  start_date: string | null
  end_date: string | null
  source_count: number
  item_count: number
  member_count: number
  my_role: TripRole
  last_edited_by: string | null
  created_at: string
  updated_at: string
}

export interface TripCreate {
  title: string
  summary?: string | null
  start_date?: string | null
  end_date?: string | null
}

export interface TripUpdate {
  title?: string | null
  summary?: string | null
  start_date?: string | null
  end_date?: string | null
}
