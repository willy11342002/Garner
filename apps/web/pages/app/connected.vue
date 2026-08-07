<template>
  <main class="connected">
    <div class="connected__card">
      <div class="connected__icon">✦</div>
      <h1 class="connected__title">{{ t('connected.title') }}</h1>

      <!-- Desktop: Chrome Extension -->
      <template v-if="device === 'desktop'">
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

      <!-- iOS: Shortcut -->
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

        <a
          href="https://www.icloud.com/shortcuts/16f9f18d2d34417eaa6c71361b28d6b3"
          target="_blank"
          rel="noopener"
          class="connected__ios-btn"
        >
          {{ t('connected.ios.download_btn') }}
        </a>
        <p class="connected__hint-sm">{{ t('connected.ios.hint') }}</p>
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
// 這頁只做一件事：依裝置給對應的安裝連結（Chrome Extension / iOS 捷徑）。
// 兩者都是「開分頁到 /app/quick-add?url=...」由網頁版用既有 session 存入，
// 不需要授權、不需要發 token，所以這裡沒有任何 API 呼叫。
const { t } = useI18n()
useHead({ title: t('connected.page_title') })

const ua = import.meta.client ? navigator.userAgent : ''
const isIOSPhone = /iPhone|iPod/.test(ua)
const isMobile = /Mobi|Android|iPhone|iPad|iPod/.test(ua)
const device = isIOSPhone ? 'ios' : isMobile ? 'android' : 'desktop'
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

.connected__title {
  font-family: var(--font-brand);
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.03em;
  margin: 0 0 20px;
}

.connected__desc {
  font-size: 13px;
  color: var(--text-mid);
  line-height: 1.7;
  margin: 0 0 20px;
}

.connected__hint-sm {
  font-size: 11.5px;
  color: var(--text-dim);
  margin: 10px 0 0;
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

/* iOS */
.connected__ios-btn {
  display: block;
  width: 100%;
  padding: 10px 16px;
  background: var(--accent);
  color: var(--accent-fg);
  border: none;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  text-align: center;
  cursor: pointer;
  transition: opacity 0.15s;
  margin-bottom: 16px;
}

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
