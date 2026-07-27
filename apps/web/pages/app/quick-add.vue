<template>
  <main class="login">
    <div class="login__card">
      <h1 class="login__logo">Garner</h1>

      <template v-if="status === 'loading'">
        <div class="quick-add__spinner" />
        <p class="login__sub">{{ t('quickAdd.adding') }}</p>
      </template>

      <template v-else>
        <p class="login__error">{{ errorMessage }}</p>
        <NuxtLink class="btn btn--oauth quick-add__back" to="/app">{{ t('quickAdd.back') }}</NuxtLink>
      </template>
    </div>
  </main>
</template>

<script setup lang="ts">
definePageMeta({ layout: false })
useHead({ title: 'Garner — 新增中' })

const { t } = useI18n()
const route = useRoute()
const itemStore = useItemStore()

const status = ref<'loading' | 'error'>('loading')
const errorMessage = ref('')

onMounted(async () => {
  const raw = route.query.url
  const url = (Array.isArray(raw) ? raw[0] : raw)?.trim()

  if (!url || !/^https?:\/\//.test(url)) {
    status.value = 'error'
    errorMessage.value = t('quickAdd.missingUrl')
    return
  }

  try {
    const item = await itemStore.add({ url })
    await navigateTo({ path: '/app', query: { item: item.id } }, { replace: true })
  } catch (err: any) {
    status.value = 'error'
    errorMessage.value = err?.errorCode?.startsWith('quota_exceeded')
      ? t('home.error_quota_full')
      : t('quickAdd.error')
  }
})
</script>

<style scoped>
.login {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.login__card {
  width: 100%;
  max-width: 360px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 40px 32px;
  text-align: center;
}

.login__logo {
  font-family: var(--font-brand);
  font-size: 32px;
  font-weight: 700;
  letter-spacing: -0.03em;
  margin: 0 0 24px;
}

.login__sub {
  font-size: 13px;
  color: var(--text-mid);
  margin: 0;
}

.login__error {
  margin: 0 0 20px;
  font-size: 13px;
  color: #e85555;
}

.quick-add__spinner {
  width: 28px;
  height: 28px;
  margin: 0 auto 16px;
  border-radius: 50%;
  border: 3px solid var(--border2);
  border-top-color: var(--accent);
  animation: quick-add-spin 0.7s linear infinite;
}

.quick-add__back {
  display: inline-flex;
  width: auto;
  padding: 10px 20px;
}

@keyframes quick-add-spin {
  to { transform: rotate(360deg); }
}
</style>
