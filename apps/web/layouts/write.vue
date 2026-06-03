<template>
  <div class="write-layout">
    <LayoutAppNav v-if="isLoggedIn" />
    <div v-else class="write-layout__nav-placeholder"></div>
    <slot />
  </div>
</template>

<script setup lang="ts">
const supabaseUser = useSupabaseUser()
const isLoggedIn = computed(() => !!supabaseUser.value)
</script>

<style>
/* AppNav 在 write 頁面不 sticky，隨頁面捲走 */
.write-layout .nav {
  position: relative !important;
  top: auto !important;
}

/* 在 auth 尚未 resolve 前，預先佔據 nav 的高度，防止 layout shift */
.write-layout__nav-placeholder {
  height: 52px;
  flex-shrink: 0;
}
</style>
