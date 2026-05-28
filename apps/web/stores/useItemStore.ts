import { defineStore } from 'pinia'
import type { Item, ItemCreate, ItemUpdate } from '~/types/api'

export const useItemStore = defineStore('item', () => {
  const items = ref<Item[]>([])

  async function load() {
    const { listItems } = useItems()
    items.value = await listItems()
  }

  async function add(data: ItemCreate): Promise<Item> {
    const { createItem } = useItems()
    const item = await createItem(data)
    items.value.unshift(item)
    if (!item.parsed_at) {
      _watchProcessing(item.id)
    }
    return item
  }

  async function remove(id: string) {
    const { deleteItem } = useItems()
    await deleteItem(id)
    const idx = items.value.findIndex(i => i.id === id)
    if (idx !== -1) items.value.splice(idx, 1)
  }

  async function patch(id: string, data: ItemUpdate): Promise<Item> {
    const { updateItem } = useItems()
    const updated = await updateItem(id, data)
    const idx = items.value.findIndex(i => i.id === id)
    if (idx !== -1) items.value[idx] = updated
    return updated
  }

  async function _watchProcessing(itemId: string) {
    const config = useRuntimeConfig()
    const session = useSupabaseSession()
    const token = session.value?.access_token
    if (!token) return

    let response: Response
    try {
      response = await fetch(
        `${config.public.apiBase}/items/${itemId}/stream`,
        { headers: { Authorization: `Bearer ${token}` } },
      )
    } catch { return }

    if (!response.ok || !response.body) return

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const msg = JSON.parse(line.slice(6))
            if (msg.status === 'done') {
              const idx = items.value.findIndex(i => i.id === itemId)
              if (idx !== -1 && msg.item) items.value[idx] = msg.item
              return
            }
            if (msg.status === 'timeout' || msg.status === 'error') return
          } catch { /* ignore malformed lines */ }
        }
      }
    } finally {
      reader.cancel()
    }
  }

  return { items, load, add, remove, patch }
})
