<template>
  <main class="connected">
    <div class="connected__card">
      <div class="connected__icon">✦</div>
      <h1 class="connected__title">Garner</h1>

      <template v-if="status === 'loading'">
        <p class="connected__hint">正在授權中…</p>
      </template>

      <template v-else-if="status === 'done'">
        <p class="connected__status">連結成功</p>
        <p class="connected__hint">Extension 已取得授權，請關閉此分頁。</p>
        <div class="connected__key">
          <kbd>Ctrl</kbd><span class="connected__key-sep">+</span><kbd>W</kbd>
          <span class="connected__key-or">或</span>
          <kbd>⌘</kbd><span class="connected__key-sep">+</span><kbd>W</kbd>
        </div>

        <div class="connected__divider" />

        <p class="connected__ios-label">iOS 捷徑</p>
        <template v-if="!iosToken">
          <button class="connected__ios-btn" :disabled="iosLoading" @click="generateIosToken">
            {{ iosLoading ? '生成中…' : '取得 iOS 捷徑 Token' }}
          </button>
        </template>
        <template v-else>
          <button class="connected__token-btn" :class="{ copied: iosCopied }" @click="copyIosToken">
            <span class="connected__token-text">{{ iosCopied ? '已複製！' : iosToken }}</span>
          </button>
          <p class="connected__ios-hint">Token 只顯示一次，請立即複製後貼入捷徑</p>
        </template>
      </template>

      <template v-else>
        <p class="connected__error">授權失敗，請關閉後重試。</p>
      </template>
    </div>
  </main>
</template>

<script setup lang="ts">
definePageMeta({ layout: false })
useHead({ title: 'Garner — 連結成功' })

const client = useSupabaseClient()
const config = useRuntimeConfig()

type Status = 'loading' | 'done' | 'error'
const status = ref<Status>('loading')

// iOS PAT
const iosToken = ref<string | null>(null)
const iosLoading = ref(false)
const iosCopied = ref(false)
let sessionCache: { access_token: string } | null = null

onMounted(async () => {
  try {
    const { data: { session } } = await client.auth.getSession()
    if (!session) { status.value = 'error'; return }
    sessionCache = session

    const resp = await fetch(`${config.public.apiBase}/auth/pat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({ name: 'Chrome Extension' }),
    })

    if (!resp.ok) { status.value = 'error'; return }

    const { token } = await resp.json()
    window.postMessage({ type: 'GARNER_TOKEN_UPDATE', pat: token }, window.location.origin)
    status.value = 'done'
  } catch {
    status.value = 'error'
  }
})

async function generateIosToken() {
  if (!sessionCache) return
  iosLoading.value = true
  try {
    const resp = await fetch(`${config.public.apiBase}/auth/pat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${sessionCache.access_token}`,
      },
      body: JSON.stringify({ name: 'iOS 捷徑' }),
    })
    if (!resp.ok) return
    const { token } = await resp.json()
    iosToken.value = token
  } finally {
    iosLoading.value = false
  }
}

async function copyIosToken() {
  if (!iosToken.value) return
  await navigator.clipboard.writeText(iosToken.value)
  iosCopied.value = true
  setTimeout(() => { iosCopied.value = false }, 2000)
}
</script>

<style scoped>
.connected {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.connected__card {
  width: 100%;
  max-width: 360px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 48px 32px 40px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.connected__icon {
  font-size: 32px;
  color: var(--accent);
  margin-bottom: 12px;
  line-height: 1;
}

.connected__title {
  font-family: var(--font-brand);
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.03em;
  margin: 0 0 20px;
}

.connected__status {
  font-size: 15px;
  font-weight: 600;
  color: var(--accent);
  margin: 0 0 8px;
}

.connected__hint {
  font-size: 13px;
  color: var(--text-mid);
  margin: 0 0 24px;
  line-height: 1.6;
}

.connected__error {
  font-size: 13px;
  color: #e85555;
  margin: 0;
  line-height: 1.6;
}

.connected__key {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-mid);
  font-size: 13px;
}

.connected__key kbd {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 3px 8px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 500;
  color: var(--text);
}

.connected__key-sep {
  font-size: 11px;
  color: var(--text-mid);
}

.connected__key-or {
  margin: 0 6px;
  color: var(--text-mid);
}

.connected__divider {
  width: 100%;
  height: 1px;
  background: var(--border);
  margin: 24px 0;
}

.connected__ios-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-mid);
  margin: 0 0 12px;
}

.connected__ios-btn {
  width: 100%;
  padding: 10px 16px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  cursor: pointer;
  transition: background 0.15s;
}
.connected__ios-btn:hover:not(:disabled) {
  background: var(--surface-hover, var(--border));
}
.connected__ios-btn:disabled {
  opacity: 0.5;
  cursor: default;
}

.connected__token-btn {
  width: 100%;
  padding: 12px 16px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  font-size: 11px;
  font-family: var(--font-mono, monospace);
  color: var(--accent);
  cursor: pointer;
  word-break: break-all;
  text-align: center;
  transition: background 0.15s, border-color 0.15s;
}
.connected__token-btn:hover {
  border-color: var(--accent);
}
.connected__token-btn.copied {
  background: color-mix(in srgb, var(--accent) 10%, transparent);
  border-color: var(--accent);
  color: var(--accent);
  font-family: var(--font-ui);
  font-size: 13px;
  font-weight: 600;
}

.connected__token-text {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.connected__ios-hint {
  font-size: 11px;
  color: var(--text-mid);
  margin: 8px 0 0;
  line-height: 1.5;
}
</style>
