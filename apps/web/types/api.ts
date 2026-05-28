export interface User {
  id: string
  email: string
  avatar_url: string | null
}

export interface Item {
  id: string
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
