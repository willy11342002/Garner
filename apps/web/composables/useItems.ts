export function useItems() {
  const config = useRuntimeConfig()

  async function fetchItems() {
    return useFetch(`${config.public.apiBase}/items`)
  }

  return { fetchItems }
}
