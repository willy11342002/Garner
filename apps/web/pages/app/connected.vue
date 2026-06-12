<template>
  <main class="connected">
    <div class="connected__card">
      <div class="connected__icon">✦</div>
      <h1 class="connected__title">{{ t('connected.title') }}</h1>

      <!-- Desktop: Chrome Extension -->
      <template v-if="device === 'desktop'">
        <!-- 偵測中 -->
        <template v-if="extInstalled === null">
          <p class="connected__hint">{{ t('connected.desktop.detecting') }}</p>
        </template>

        <!-- 未安裝 Extension -->
        <template v-else-if="extInstalled === false">
          <p class="connected__desc">{{ t('connected.desktop.desc') }}</p>
          <a
            href="https://chromewebstore.google.com/detail/nleemnjodbbknndffljjmcolkicmdghh"
            target="_blank"
            rel="noopener"
            class="connected__install-btn"
          >
            {{ t('connected.desktop.install_btn') }}
          </a>
          <p class="connected__hint-sm">{{ t('connected.desktop.install_hint') }}</p>
        </template>

        <!-- 已安裝：授權中 -->
        <template v-else-if="status === 'loading'">
          <p class="connected__hint">{{ t('connected.desktop.authorising') }}</p>
        </template>

        <!-- 已安裝：授權成功 -->
        <template v-else-if="status === 'done'">
          <div class="connected__success-icon">✓</div>
          <p class="connected__status">{{ t('connected.desktop.status_done') }}</p>
          <p class="connected__hint">{{ t('connected.desktop.hint_done') }}</p>
          <div class="connected__key">
            <kbd>Ctrl</kbd><span class="connected__key-sep">+</span><kbd>W</kbd>
            <span class="connected__key-or">{{ t('connected.desktop.key_or') }}</span>
            <kbd>⌘</kbd><span class="connected__key-sep">+</span><kbd>W</kbd>
            <span class="connected__key-or">{{ t('connected.desktop.key_close') }}</span>
          </div>
        </template>

        <!-- 授權失敗 -->
        <template v-else>
          <p class="connected__error">{{ t('connected.desktop.error') }}</p>
        </template>
      </template>

      <!-- iOS: Shortcut Token -->
      <template v-else-if="device === 'ios'">
        <p class="connected__desc">{{ t('connected.ios.desc') }}</p>
        <div class="connected__steps">
          <div class="connected__step">
            <span class="connected__step-num">1</span>
            <span>{{ t('connected.ios.step1') }}</span>
          </div>
          <div class="connected__step">
            <span class="connected__step-num">2</span>
            <span>{{ t('connected.ios.step2') }}</span>
          </div>
          <div class="connected__step">
            <span class="connected__step-num">3</span>
            <span>{{ t('connected.ios.step3') }}</span>
          </div>
        </div>

        <!-- 階段一：下載 -->
        <template v-if="iosStep === 'download'">
          <a
            href="https://www.icloud.com/shortcuts/854b6616a6174901aeafb5870aba6749"
            target="_blank"
            rel="noopener"
            class="connected__ios-btn"
            @click="iosStep = 'token'"
          >
            {{ t('connected.ios.download_btn') }}
          </a>
          <button class="connected__skip-link" @click="iosStep = 'token'">
            {{ t('connected.ios.skip') }}
          </button>
        </template>

        <!-- 階段二：取得並複製 Token -->
        <template v-else>
          <template v-if="!iosToken">
            <button class="connected__ios-btn" :disabled="iosLoading" @click="generateIosToken">
              {{ iosLoading ? t('connected.ios.generating') : t('connected.ios.get_token') }}
            </button>
          </template>
          <template v-else>
            <p class="connected__ios-label">{{ t('connected.ios.token_label') }}</p>
            <button class="connected__token-btn" :class="{ copied: iosCopied }" @click="copyIosToken">
              <span class="connected__token-text">{{ iosCopied ? t('connected.ios.copied') : iosToken }}</span>
            </button>
            <p class="connected__ios-hint">{{ t('connected.ios.token_hint') }}</p>
          </template>
          <button class="connected__skip-link" @click="iosStep = 'download'">
            {{ t('connected.ios.back') }}
          </button>
        </template>
      </template>

      <!-- Android / other mobile -->
      <template v-else>
        <p class="connected__desc">{{ t('connected.android.desc') }}</p>
        <div class="connected__steps">
          <div class="connected__step">
            <span class="connected__step-num">1</span>
            <span>{{ t('connected.android.step1') }}</span>
          </div>
          <div class="connected__step">
            <span class="connected__step-num">2</span>
            <span>{{ t('connected.android.step2') }}</span>
          </div>
          <div class="connected__step">
            <span class="connected__step-num">3</span>
            <span>{{ t('connected.android.step3') }}</span>
          </div>
        </div>
        <NuxtLink to="/app" class="connected__back-btn btn btn--accent">{{ t('connected.android.back_btn') }}</NuxtLink>
        <p class="connected__android-hint">{{ t('connected.android.hint') }}</p>
      </template>
    </div>
  </main>
</template>

<script setup lang="ts">
definePageMeta({})
const { t } = useI18n()
useHead({ title: t('connected.page_title') })

const client = useSupabaseClient()
const config = useRuntimeConfig()

// 裝置偵測
const ua = import.meta.client ? navigator.userAgent : ''
const isIOSPhone = /iPhone|iPod/.test(ua)
const isMobile = /Mobi|Android|iPhone|iPad|iPod/.test(ua)
const device = isIOSPhone ? 'ios' : isMobile ? 'android' : 'desktop'

type Status = 'loading' | 'done' | 'error'
const status = ref<Status>('loading')
// null = 偵測中，true/false = 偵測結果
const extInstalled = ref<boolean | null>(null)

const iosStep = ref<'download' | 'token'>('download')
const iosToken = ref<string | null>(null)
const iosLoading = ref(false)
const iosCopied = ref(false)
let sessionCache: { access_token: string } | null = null

onMounted(async () => {
  if (device !== 'desktop') {
    try {
      const { data: { session } } = await client.auth.getSession()
      if (session) sessionCache = session
    } catch {}
    return
  }

  // PING / PONG 偵測 extension（timeout 1s fallback）
  extInstalled.value = await new Promise<boolean>(resolve => {
    const timer = setTimeout(() => {
      window.removeEventListener('message', handler)
      resolve(false)
    }, 1000)
    function handler(e: MessageEvent) {
      if (e.origin !== window.location.origin) return
      if (e.data?.type !== 'GARNER_PONG') return
      clearTimeout(timer)
      window.removeEventListener('message', handler)
      resolve(true)
    }
    window.addEventListener('message', handler)
    window.postMessage({ type: 'GARNER_PING' }, window.location.origin)
  })

  // 不管有沒有擴充都靜默建立 PAT
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
    if (extInstalled.value) {
      window.postMessage({ type: 'GARNER_TOKEN_UPDATE', pat: token }, window.location.origin)
      status.value = 'done'
    }
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
  min-height: calc(100vh - 120px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.connected__card {
  width: 100%;
  max-width: 380px;
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

.connected__success-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--accent) 15%, transparent);
  color: var(--accent);
  font-size: 18px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}

.connected__title {
  font-family: var(--font-brand);
  font-size: 22px;
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

.connected__desc {
  font-size: 13px;
  color: var(--text-mid);
  line-height: 1.7;
  margin: 0 0 20px;
}

.connected__hint {
  font-size: 13px;
  color: var(--text-mid);
  margin: 0 0 20px;
  line-height: 1.6;
}

.connected__hint-sm {
  font-size: 11.5px;
  color: var(--text-dim);
  margin: 10px 0 0;
  line-height: 1.6;
}

.connected__error {
  font-size: 13px;
  color: #e85555;
  margin: 0;
  line-height: 1.6;
}

/* Install button */
.connected__install-btn {
  display: block;
  width: 100%;
  padding: 11px 16px;
  background: var(--accent);
  color: var(--accent-fg);
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  text-align: center;
  transition: opacity 0.15s;
}
.connected__install-btn:hover { opacity: 0.88; }

/* Key shortcut */
.connected__key {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-mid);
  font-size: 13px;
  flex-wrap: wrap;
  justify-content: center;
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

.connected__key-sep { font-size: 11px; color: var(--text-mid); }
.connected__key-or { margin: 0 4px; color: var(--text-dim); font-size: 12px; }

/* Steps */
.connected__steps {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  margin-bottom: 20px;
}

.connected__step {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  text-align: left;
  font-size: 13px;
  color: var(--text-mid);
  line-height: 1.5;
}

.connected__step-num {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--accent-dim);
  color: var(--accent);
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 1px;
}

/* iOS Token */
.connected__ios-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-mid);
  margin: 0 0 10px;
}

.connected__ios-btn {
  width: 100%;
  padding: 10px 16px;
  background: var(--accent);
  color: var(--accent-fg);
  border: none;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
  margin-bottom: 16px;
}
.connected__ios-btn:disabled { opacity: 0.5; cursor: default; }

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
  margin-bottom: 6px;
}
.connected__token-btn:hover { border-color: var(--accent); }
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
  color: var(--text-dim);
  margin: 0 0 16px;
  line-height: 1.5;
}

.connected__skip-link {
  background: none;
  border: none;
  font-size: 12px;
  color: var(--accent);
  cursor: pointer;
  padding: 0;
  margin-top: 12px;
  text-decoration: none;
}
.connected__skip-link:hover { text-decoration: underline; }

/* Android */
.connected__back-btn {
  width: 100%;
  text-align: center;
  margin-bottom: 12px;
}

.connected__android-hint {
  font-size: 11px;
  color: var(--text-dim);
  margin: 0;
  line-height: 1.5;
}
</style>
