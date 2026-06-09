<template>
  <footer class="app-footer">
    <div class="app-footer__links">
      <NuxtLink v-if="showPricing" to="/pricing" class="app-footer__link">{{ t('landing.pricing_link') }}</NuxtLink>
      <span v-if="showPricing" class="app-footer__sep">·</span>
      <NuxtLink to="/privacy" class="app-footer__link">{{ t('landing.privacy_link') }}</NuxtLink>
      <span class="app-footer__sep">·</span>
      <NuxtLink to="/terms" class="app-footer__link">{{ t('landing.terms_link') }}</NuxtLink>
      <span class="app-footer__sep">·</span>
      <a
        href="https://docs.google.com/forms/d/e/1FAIpQLSdYlIIXPUfQ5DyL-ptIxCwx4G99D4mx9CiwJ9OVQYcGXUDzqw/viewform"
        target="_blank"
        rel="noopener"
        class="app-footer__link"
      >{{ t('landing.contact_link') }}</a>
      <span class="app-footer__sep">·</span>
      <NuxtLink to="/app/connected" class="app-footer__link">{{ t('connected.title') }}</NuxtLink>
    </div>
    <p class="app-footer__copy">© {{ year }} Garner</p>
  </footer>
</template>

<script setup lang="ts">
const { t } = useI18n()
const year = new Date().getFullYear()

defineProps<{ showPricing?: boolean }>()
</script>

<style scoped>
.app-footer {
  text-align: center;
  padding: 32px 16px 24px;
  margin-top: 0px;
  border-top: 1px solid var(--border);
}
.app-footer__links {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 0;
}
.app-footer__link {
  font-size: 12px;
  color: var(--text-dim);
  text-decoration: none;
  font-family: var(--font-mono);
  transition: color 0.15s;
}
.app-footer__link:hover { color: var(--text-mid); }
.app-footer__sep {
  font-size: 12px;
  color: var(--text-dim);
  margin: 0 8px;
}
.app-footer__copy {
  font-size: 11px;
  color: var(--text-dim);
  margin-top: 6px;
  font-family: var(--font-mono);
}
</style>
