export default defineNuxtPlugin(() => {
  const isDark = useState('theme-dark', () => true)
  const saved = localStorage.getItem('vela-theme')
  isDark.value = saved !== 'light'
  document.body.classList.toggle('light', !isDark.value)
})
