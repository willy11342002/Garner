export const useTheme = () => {
  const isDark = useState('theme-dark', () => true)

  const toggle = () => {
    if (!import.meta.client) return
    isDark.value = !isDark.value
    document.body.classList.toggle('light', !isDark.value)
    localStorage.setItem('vela-theme', isDark.value ? 'dark' : 'light')
  }

  return { isDark, toggle }
}
