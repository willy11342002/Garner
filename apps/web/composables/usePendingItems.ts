import type { ItemPendingReview } from '~/types/api'

const pendingItems = ref<ItemPendingReview[]>([])

export function usePendingItems() {
  const pendingItemIds = computed(() => new Set(pendingItems.value.map(i => i.id)))
  return { pendingItems, pendingItemIds }
}
