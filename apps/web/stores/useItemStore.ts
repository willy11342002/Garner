import { defineStore } from 'pinia'
import type { Item, ItemCreate, ItemUpdate } from '~/types/api'

interface LoadParams {
  page?: number
  page_size?: number
  tag_ids?: string[]
  tag_logic?: 'and' | 'or'
  saved_after?: string
  sort?: 'saved_desc' | 'saved_asc'
}

export const useItemStore = defineStore('item', () => {
  const items = ref<Item[]>([])
  const total = ref(0)
  const totalAll = ref<number | null>(null)
  const recentlyProcessed = ref<string | null>(null)
  const processingStages = ref<Map<string, string>>(new Map())

  async function load(params?: LoadParams) {
    const { listItemsPage } = useItems()
    const result = await listItemsPage(params ?? {})
    items.value = result.items
    total.value = result.total

    const hasFilters = !!(params?.tag_ids?.length || params?.saved_after)
    if (!hasFilters) {
      totalAll.value = result.total
    }

    for (const item of items.value) {
      if (!item.parsed_at && !item.url.startsWith('/')) _watchProcessing(item.id)
    }
  }

  async function add(data: ItemCreate): Promise<Item> {
    const config = useRuntimeConfig()
    const session = useSupabaseSession()
    const token = session.value?.access_token
    if (!token) throw new Error('Not authenticated')

    const response = await fetch(`${config.public.apiBase}/items/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, 'X-Response-Mode': 'async' },
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      // Normalise error code: HTTPException → detail string; quota → detail.feature
      const detail = body?.detail
      const errorCode: string =
        typeof detail === 'string' ? detail
        : typeof detail?.feature === 'string' ? `quota_exceeded_${detail.feature}`
        : `http_${response.status}`
      throw Object.assign(new Error(`HTTP ${response.status}`), {
        data: body,
        statusCode: response.status,
        errorCode,
      })
    }

    const item = await response.json() as Item
    items.value.unshift(item)
    total.value++
    if (totalAll.value !== null) totalAll.value++
    if (!item.parsed_at && !item.url.startsWith('/')) {
      _watchProcessing(item.id)
    }
    return item
  }

  async function remove(id: string) {
    const { deleteItem } = useItems()
    await deleteItem(id)
    const idx = items.value.findIndex(i => i.id === id)
    if (idx !== -1) {
      items.value.splice(idx, 1)
      total.value = Math.max(0, total.value - 1)
      if (totalAll.value !== null) totalAll.value = Math.max(0, totalAll.value - 1)
    }
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

    processingStages.value.set(itemId, 'fetching')

    let response: Response
    try {
      response = await fetch(
        `${config.public.apiBase}/items/${itemId}/stream`,
        { headers: { Authorization: `Bearer ${token}` } },
      )
    } catch {
      processingStages.value.delete(itemId)
      return
    }

    if (!response.ok || !response.body) {
      processingStages.value.delete(itemId)
      return
    }

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

            if (msg.status === 'progress' && msg.stage) {
              processingStages.value.set(itemId, msg.stage)
            } else if (msg.status === 'done') {
              const idx = items.value.findIndex(i => i.id === itemId)
              if (idx !== -1 && msg.item) items.value[idx] = msg.item
              recentlyProcessed.value = itemId
              processingStages.value.delete(itemId)
              return
            } else if (msg.status === 'failed' || msg.status === 'timeout' || msg.status === 'error') {
              processingStages.value.set(itemId, msg.status)
              return
            }
          } catch { /* ignore malformed lines */ }
        }
      }
    } finally {
      reader.cancel()
    }
  }

  return { items, total, totalAll, load, add, remove, patch, recentlyProcessed, processingStages }
})
