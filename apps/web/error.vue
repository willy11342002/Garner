<template>
  <div class="error-root">
    <nav class="nav">
      <NuxtLink to="/" class="nav__logo">Garner</NuxtLink>
      <div class="nav__right">
        <button class="nav__theme" @click="toggle" aria-label="Toggle theme">
          <svg viewBox="0 0 24 24">
            <template v-if="!isDark">
              <circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" stroke-width="1.6"/>
              <path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
            </template>
            <template v-else>
              <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
            </template>
          </svg>
        </button>
      </div>
    </nav>

    <main class="error-main">
      <p class="error-code">{{ error.statusCode }}</p>
      <h1 class="error-title">{{ is404 ? '找不到這個頁面' : '發生錯誤' }}</h1>
      <button class="btn btn--accent error-back" @click="handleError">
        回到首頁
      </button>

    </main>
  </div>
</template>

<script setup lang="ts">
const { isDark, toggle } = useTheme()

const props = defineProps<{ error: { statusCode: number; message?: string } }>()
const is404 = computed(() => props.error.statusCode === 404)

function handleError() {
  clearError({ redirect: '/' })
}

if (!is404.value) {
  console.error('[error.vue]', props.error)
}
</script>

<style scoped>
.error-root {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg);
  color: var(--text);
}

.error-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
}

.error-code {
  font-family: var(--font-mono);
  font-size: 96px;
  font-weight: 500;
  line-height: 1;
  color: var(--accent);
  margin: 0 0 16px;
  letter-spacing: -0.04em;
}

.error-title {
  font-family: var(--font-brand);
  font-size: 28px;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 12px;
  letter-spacing: -0.02em;
}

.error-back {
  font-family: var(--font-ui);
  font-size: 13px;
  font-weight: 700;
  height: 38px;
  padding: 0 20px;
  background: var(--accent);
  color: var(--accent-fg);
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: filter 0.15s ease, transform 0.15s ease;
}

.error-back:hover {
  filter: brightness(1.08);
  transform: translateY(-1px);
}
</style>
