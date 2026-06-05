<template>
  <nav class="nav">
    <NuxtLink to="/" class="nav__logo">Garner</NuxtLink>
    <div class="nav__right">
      <button class="nav__icon-btn" :title="t('nav.toggleTheme')" @click="toggleTheme">
        <svg v-if="isDark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
          <circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>
        </svg>
      </button>
      <button class="nav__icon-btn nav__lang-btn" :title="t('nav.toggleLanguage')" @click="toggleLocale">
        {{ locale === 'zh-TW' ? '中' : 'EN' }}
      </button>
      <NuxtLink to="/login" class="nav__add nav__login"><span>{{ t('nav.login') }}</span></NuxtLink>
    </div>
  </nav>
</template>

<script setup lang="ts">
const { t, locale, setLocale } = useI18n()
const { isDark, setMode } = useTheme()

function toggleTheme() {
  setMode(isDark.value ? 'light' : 'dark')
}

function toggleLocale() {
  setLocale(locale.value === 'zh-TW' ? 'en' : 'zh-TW')
}
</script>
