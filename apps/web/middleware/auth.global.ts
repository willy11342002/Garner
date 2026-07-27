export default defineNuxtRouteMiddleware((to) => {
  if (!to.path.startsWith('/app')) return
  const user = useSupabaseUser()
  if (!user.value) {
    return navigateTo(`/login?redirect=${encodeURIComponent(to.fullPath)}`)
  }
})
