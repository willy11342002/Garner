import { defineStore } from 'pinia'
import type { Item, ItemCreate, ItemUpdate } from '~/types/api'

export const useItemStore = defineStore('item', () => {
  const items = ref<Item[]>([])
  const recentlyProcessed = ref<string | null>(null)
  const processingStages = ref<Map<string, string>>(new Map())

  async function load() {
    const { listItems } = useItems()
    items.value = await listItems()
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
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(data),
    })

    if (!response.ok || !response.body) {
      const err = await response.json().catch(() => ({}))
      throw Object.assign(new Error(`HTTP ${response.status}`), { data: err, statusCode: response.status })
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    let resolved = false
    let createdId: string | null = null

    let resolveItem!: (item: Item) => void
    let rejectItem!: (err: unknown) => void
    const waitForCreated = new Promise<Item>((res, rej) => { resolveItem = res; rejectItem = rej })

    // Single reader loop – runs fully in background.
    // Resolves waitForCreated on 'created', then keeps reading progress/done.
    ;(async () => {
      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buf += decoder.decode(value, { stream: true })
          const parts = buf.split('\n')
          buf = parts.pop() ?? ''

          for (const line of parts) {
            if (!line.startsWith('data: ')) continue
            let msg: any
            try { msg = JSON.parse(line.slice(6)) } catch { continue }

            if (msg.status === 'created' && msg.item && !resolved) {
              const item = msg.item as Item
              createdId = item.id
              items.value.unshift(item)
              if (!item.parsed_at && !item.url.startsWith('/')) {
                processingStages.value.set(item.id, 'fetching')
              }
              resolved = true
              resolveItem(item)
            } else if (createdId) {
              if (msg.status === 'progress' && msg.stage) {
                processingStages.value.set(createdId, msg.stage)
              } else if (msg.status === 'done' && msg.item) {
                const updated = msg.item as Item
                const idx = items.value.findIndex(i => i.id === createdId)
                if (idx !== -1) items.value[idx] = updated
                recentlyProcessed.value = createdId
                processingStages.value.delete(createdId)
              } else if (msg.status === 'failed' || msg.status === 'timeout' || msg.status === 'error') {
                processingStages.value.set(createdId, msg.status)
              }
            }
          }
        }
      } catch (err) {
        if (!resolved) rejectItem(err)
      } finally {
        reader.cancel()
        if (!resolved) rejectItem(new Error('SSE stream closed before created event'))
      }
    })()

    return waitForCreated
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

  return { items, load, add, remove, patch, recentlyProcessed, processingStages }
})
