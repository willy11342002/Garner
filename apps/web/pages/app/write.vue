<script setup lang="ts">
definePageMeta({ ssr: false })

const router = useRouter()
const { createArticle } = useArticles()
const error = ref(false)

onMounted(async () => {
  try {
    const article = await createArticle()
    router.replace(`/app/write/${article.id}`)
  } catch {
    error.value = true
  }
})
</script>

<template>
  <main class="write-shell">
    <div v-if="error" class="write-placeholder">
      <span class="write-placeholder__icon">⚠️</span>
      <p class="write-placeholder__desc">建立文章失敗，請重試</p>
      <NuxtLink to="/app" class="btn btn--ghost">← 返回</NuxtLink>
    </div>
    <div v-else class="write-placeholder">
      <span class="write-placeholder__spinner"></span>
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

.write-placeholder__icon { font-size: 32px; }
.write-placeholder__desc { margin: 0; font-size: 14px; }

.write-placeholder__spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border2);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
