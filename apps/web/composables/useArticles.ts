import type { ArticleUpdate, Item } from '~/types/api'

export function useArticles() {
  const apiFetch = useApiFetch()

  // 建立一篇手動文章（知識），建立後由呼叫端開編輯器
  function createArticle(): Promise<Item> {
    return apiFetch('/articles/', { method: 'POST' })
  }

  function updateArticle(id: string, data: ArticleUpdate): Promise<Item> {
    return apiFetch(`/articles/${id}`, { method: 'PATCH', body: data })
  }

  return { createArticle, updateArticle }
}
