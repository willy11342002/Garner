export type ThemeMode = 'dark' | 'light' | 'system'

export const useTheme = () => {
  const mode = useState<ThemeMode>('theme-mode', () => 'dark')
  const isDark = useState('theme-dark', () => true)

  const applyMode = (m: ThemeMode) => {
    if (!import.meta.client) return
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    const dark = m === 'system' ? prefersDark : m === 'dark'
    isDark.value = dark
    document.body.classList.toggle('light', !dark)
    localStorage.setItem('vela-theme', m)
  }

  const setMode = (m: ThemeMode) => {
    mode.value = m
    applyMode(m)
  }

  const toggle = () => setMode(isDark.value ? 'light' : 'dark')

  const init = () => {
    if (!import.meta.client) return
    const saved = localStorage.getItem('vela-theme') as ThemeMode | null
    const initial: ThemeMode = (saved === 'dark' || saved === 'light' || saved === 'system') ? saved : 'dark'
    mode.value = initial
    applyMode(initial)

    if (initial === 'system') {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => applyMode('system'))
    }
  }

  return { isDark, mode, setMode, toggle, init }
}
