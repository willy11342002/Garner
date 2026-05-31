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

  async function updateProfile(data: { username?: string; avatar_url?: string }) {
    const apiFetch = useApiFetch()
    user.value = await apiFetch<User>('/auth/me', { method: 'PUT', body: data })
  }

  async function uploadAvatar(file: File) {
    const apiFetch = useApiFetch()
    const form = new FormData()
    form.append('file', file)
    user.value = await apiFetch<User>('/auth/me/avatar', { method: 'POST', body: form })
  }

  function clear() {
    user.value = null
  }

  return { user, init, clear, updateProfile, uploadAvatar }
})
