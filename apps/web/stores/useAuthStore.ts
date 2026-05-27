import type { User } from '~/types/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)

  async function init() {
    const apiFetch = useApiFetch()
    try {
      user.value = await apiFetch<User>('/auth/me')
    } catch {
      user.value = null
    }
  }

  function clear() {
    user.value = null
  }

  return { user, init, clear }
})
