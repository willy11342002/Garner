interface Toast {
  id: number
  message: string
  type: 'success' | 'error' | 'info'
}

const toasts = ref<Toast[]>([])
let id = 0

export function useToast() {
  function show(message: string, type: 'success' | 'error' | 'info' = 'info', duration = 3000) {
    const toast: Toast = { id: ++id, message, type }
    toasts.value.push(toast)
    setTimeout(() => {
      toasts.value = toasts.value.filter(t => t.id !== toast.id)
    }, duration)
  }
  return { toasts, show }
}
