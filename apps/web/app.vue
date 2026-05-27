<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>

<script setup lang="ts">
const supabaseUser = useSupabaseUser()
const authStore = useAuthStore()

watch(supabaseUser, async (u) => {
  if (u) await authStore.init()
  else authStore.clear()
}, { immediate: true })
</script>
