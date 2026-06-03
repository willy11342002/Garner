<template>
  <div>
    <LayoutAppNav v-if="isLoggedIn" />
    <LayoutGuestNav v-else />
    <slot />
  </div>
</template>

<script setup lang="ts">
const supabaseUser = useSupabaseUser()
const isLoggedIn = computed(() => !!supabaseUser.value)
</script>
