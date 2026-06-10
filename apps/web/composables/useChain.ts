import type { Item } from '~/types/api'

const chainItems = ref<Item[]>([])

export function useChain() {
  function add(item: Item) {
    if (chainItems.value.length >= 10) return
    if (!chainItems.value.some(i => i.id === item.id)) {
      chainItems.value.push(item)
    }
  }

  function remove(id: string) {
    chainItems.value = chainItems.value.filter(i => i.id !== id)
  }

  function toggle(item: Item) {
    if (chainItems.value.some(i => i.id === item.id)) remove(item.id)
    else add(item)
  }

  function clear() {
    chainItems.value = []
  }

  function isInChain(id: string) {
    return chainItems.value.some(i => i.id === id)
  }

  return {
    chainItems: readonly(chainItems),
    add,
    remove,
    toggle,
    clear,
    isInChain,
  }
}
