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

  async function updateProfile(data: { allow_public_chain?: boolean }) {
    const apiFetch = useApiFetch()
    user.value = await apiFetch<User>('/auth/me', { method: 'PUT', body: data })
  }

  async function deleteAccount() {
    const apiFetch = useApiFetch()
    await apiFetch('/auth/me', { method: 'DELETE' })
    const supabase = useSupabaseClient()
    await supabase.auth.signOut()
    user.value = null
  }

  function clear() {
    user.value = null
  }

  return { user, init, clear, updateProfile, deleteAccount }
})
