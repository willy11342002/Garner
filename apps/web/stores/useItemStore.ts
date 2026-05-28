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

  return { items, load, add, remove, patch }
})
