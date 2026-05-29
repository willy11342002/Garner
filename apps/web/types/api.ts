export interface User {
  id: string
  email: string
  avatar_url: string | null
}

export interface Item {
  id: string
  content_id: string | null
  url: string
  title: string | null
  summary: string | null
  summary_i18n: Record<string, string> | null
  thumbnail_url: string | null
  saved_at: string
  deleted_at: string | null
  parsed_at: string | null
  status: string | null
  source_type: string | null
}

export interface ItemCreate {
  url: string
  title?: string
  raw_content?: string
}

export interface ItemUpdate {
  title?: string
  status?: 'active' | 'archived' | 'deleted'
}

export type CollectionVisibility = 'private' | 'link' | 'public'

export interface Tag {
  id: string
  name: string
  name_i18n: Record<string, string> | null
  item_count: number
}

export interface ItemPendingReview {
  id: string
  url: string
  title: string | null
  thumbnail_url: string | null
  saved_at: string
  pending_tags: Tag[]
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

export interface ExploreStats {
  total_items: number
  public_collections: number
  weekly_new: number
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
  summary: string | null
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
