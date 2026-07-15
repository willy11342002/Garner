import type { Item, ItemCreate, ItemPage, ItemUpdate, Tag } from '~/types/api'

export function useItems() {
  const apiFetch = useApiFetch()

  function listItems(): Promise<Item[]> {
    return apiFetch('/items/')
  }

  function listItemsPage(params: {
    page?: number
    page_size?: number
    tag_ids?: string[]
    tag_logic?: 'and' | 'or'
    saved_after?: string
    sort?: 'saved_desc' | 'saved_asc'
  }): Promise<ItemPage> {
    return apiFetch('/items/', {
      params: {
        page: params.page ?? 1,
        page_size: params.page_size ?? 25,
        ...(params.tag_ids?.length ? { tag_ids: params.tag_ids } : {}),
        tag_logic: params.tag_logic ?? 'and',
        ...(params.saved_after ? { saved_after: params.saved_after } : {}),
        sort: params.sort ?? 'saved_desc',
      },
    })
  }

  function createItem(data: ItemCreate): Promise<Item> {
    return apiFetch('/items/', { method: 'POST', body: data })
  }

  function getItem(id: string): Promise<Item> {
    return apiFetch(`/items/${id}`)
  }

  function updateItem(id: string, data: ItemUpdate): Promise<Item> {
    return apiFetch(`/items/${id}`, { method: 'PATCH', body: data })
  }

  function deleteItem(id: string): Promise<void> {
    return apiFetch(`/items/${id}`, { method: 'DELETE' })
  }

  function getItemTags(id: string): Promise<Tag[]> {
    return apiFetch(`/items/${id}/tags`)
  }

  function attachTag(id: string, name: string): Promise<Tag> {
    return apiFetch(`/items/${id}/tags`, { method: 'POST', body: { name } })
  }

  function detachTag(itemId: string, tagId: string): Promise<void> {
    return apiFetch(`/items/${itemId}/tags/${tagId}`, { method: 'DELETE' })
  }

  function listArchivedItems(): Promise<Item[]> {
    return apiFetch('/items/archived')
  }

  function resumeItem(id: string): Promise<Item> {
    return apiFetch(`/items/${id}/resume`, { method: 'POST' })
  }

  return {
    listItems, listItemsPage, createItem, getItem, updateItem, deleteItem,
    getItemTags, attachTag, detachTag, listArchivedItems, resumeItem,
  }
}
