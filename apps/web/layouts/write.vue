<template>
  <div class="write-layout">
    <LayoutAppNav v-if="isLoggedIn" />
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
</style>
