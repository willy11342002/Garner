import type { Notification } from '~/types/api'

export const useNotificationStore = defineStore('notifications', () => {
  const items = ref<Notification[]>([])
  const unreadCount = computed(() => items.value.filter(n => !n.is_read).length)

  let pollTimer: ReturnType<typeof setInterval> | null = null

  async function fetch() {
    try {
      const apiFetch = useApiFetch()
      const data = await apiFetch<Notification[]>('/notifications')
      items.value = data
    } catch {
      // 靜默失敗，不影響主功能
    }
  }

  function startPolling() {
    fetch()
    pollTimer = setInterval(fetch, 60_000)
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  async function markRead(ids: string[]) {
    try {
      const apiFetch = useApiFetch()
      await apiFetch('/notifications/read', { method: 'PATCH', body: { ids } })
      ids.forEach(id => {
        const n = items.value.find(n => n.id === id)
        if (n) n.is_read = true
      })
    } catch {}
  }

  async function markAllRead() {
    try {
      const apiFetch = useApiFetch()
      await apiFetch('/notifications/read-all', { method: 'PATCH' })
      items.value.forEach(n => { n.is_read = true })
    } catch {}
  }

  return { items, unreadCount, fetch, startPolling, stopPolling, markRead, markAllRead }
})
