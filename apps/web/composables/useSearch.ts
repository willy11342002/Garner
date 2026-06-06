import type { Item } from '~/types/api'

export function useSearch() {
  const apiFetch = useApiFetch()

  async function searchItems(q: string): Promise<Item[]> {
    if (!q.trim()) return []
    return apiFetch('/search/', { query: { q } })
  }

  async function searchSemantic(q: string): Promise<Item[]> {
    if (!q.trim()) return []
    return apiFetch('/search/semantic', { query: { q } })
  }

  return { searchItems, searchSemantic }
}
