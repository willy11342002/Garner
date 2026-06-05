export default defineNuxtRouteMiddleware((to) => {
  if (!to.path.startsWith('/app')) return
  if (to.path.startsWith('/app/explore')) return
  const user = useSupabaseUser()
  if (!user.value) {
    return navigateTo(`/login?redirect=${encodeURIComponent(to.path)}`)
  }
})
