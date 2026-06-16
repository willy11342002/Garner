<template>
  <div>
    <LayoutAppNav v-if="isLoggedIn" />
    <LayoutGuestNav v-else />
    <slot />
    <LayoutAppFooter v-if="showFooter" :show-pricing="!isLoggedIn" />
  </div>
</template>

<script setup lang="ts">
const supabaseUser = useSupabaseUser()
const isLoggedIn = computed(() => !!supabaseUser.value)

const route = useRoute()
// chat / reports / trips 頁面為全高版面，不顯示 footer
const showFooter = computed(() =>
  route.path !== '/app/chat' && route.path !== '/app/reports' && route.path !== '/app/trips'
)
</script>
