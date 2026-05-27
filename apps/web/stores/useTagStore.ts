import { defineStore } from 'pinia'

export const useTagStore = defineStore('tag', () => {
  const tags = ref([])

  return { tags }
})
