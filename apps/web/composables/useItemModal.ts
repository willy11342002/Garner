const activeItemId = ref<string | null>(null)
const activeItemEditMode = ref(false)

export function useItemModal() {
  return {
    activeItemId: readonly(activeItemId),
    activeItemEditMode: readonly(activeItemEditMode),
    open: (id: string) => { activeItemEditMode.value = false; activeItemId.value = id },
    openInEdit: (id: string) => { activeItemEditMode.value = true; activeItemId.value = id },
    close: () => { activeItemId.value = null; activeItemEditMode.value = false },
  }
}
