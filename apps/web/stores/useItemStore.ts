import { defineStore } from 'pinia'

export const useItemStore = defineStore('item', () => {
  const items = ref([])

  return { items }
})
