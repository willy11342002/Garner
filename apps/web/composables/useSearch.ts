import type { Item, PaginatedResult } from '~/types/api'

export function useSearch() {
  const apiFetch = useApiFetch()

  async function searchItems(q: string): Promise<Item[]> {
    if (!q.trim()) return []
    return apiFetch('/search/', { query: { q } })
  }

  async function searchSemantic(q: string, page = 1): Promise<PaginatedResult<Item>> {
    if (!q.trim()) return { items: [], page: 1, page_size: 10, has_next: false }
    return apiFetch('/search/semantic', { query: { q, page } })
  }

  return { searchItems, searchSemantic }
}
