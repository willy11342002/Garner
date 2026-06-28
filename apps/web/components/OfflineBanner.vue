<template>
  <div v-if="!isOnline" class="offline-banner">
    目前離線，顯示快取內容
  </div>
</template>

<script setup lang="ts">
const isOnline = ref(true)

onMounted(() => {
  isOnline.value = navigator.onLine
  window.addEventListener('online', () => { isOnline.value = true })
  window.addEventListener('offline', () => { isOnline.value = false })
})
</script>

<style scoped>
.offline-banner {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  padding: 8px 16px;
  background: #2a2a2a;
  color: #aaa;
  font-size: 13px;
  text-align: center;
  border-top: 1px solid #3a3a3a;
}
</style>
