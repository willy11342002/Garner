<script setup lang="ts">
definePageMeta({ ssr: false })
</script>

<template>
  <main class="write-shell">
    <div class="write-placeholder">
      <h1 class="write-placeholder__title">文章編輯器</h1>
      <p class="write-placeholder__desc">Coming soon</p>
    </div>
  </main>
</template>

<style scoped>
.write-shell {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 56px);
}

.write-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: var(--text-dim);
}

.write-placeholder__icon {
  font-size: 40px;
}

.write-placeholder__title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--text);
}

.write-placeholder__desc {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 13px;
}
</style>
