import type { Item, ItemCreate, ItemUpdate, Tag } from '~/types/api'

export function useItems() {
  const apiFetch = useApiFetch()

  function listItems(): Promise<Item[]> {
    return apiFetch('/items/')
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

  return { listItems, createItem, getItem, updateItem, deleteItem, getItemTags, attachTag, detachTag }
}
