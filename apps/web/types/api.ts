export interface User {
  id: string
  email: string
}

export interface Item {
  id: string
  url: string
  title: string | null
  summary: string | null
  thumbnail_url: string | null
  saved_at: string
  deleted_at: string | null
  parsed_at: string | null
}

export interface ItemCreate {
  url: string
  title?: string
  raw_content?: string
}

export interface ItemUpdate {
  title?: string
}

export type CollectionVisibility = 'private' | 'link' | 'public'

export interface Tag {
  id: string
  name: string
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
