const activeItemId = ref<string | null>(null)

export function useItemModal() {
  return {
    activeItemId: readonly(activeItemId),
    open: (id: string) => { activeItemId.value = id },
    close: () => { activeItemId.value = null },
  }
}
