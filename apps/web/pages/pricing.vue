<template>
  <main class="pr-shell">
    <section class="pr-hero">
      <span class="eyebrow">{{ t('pricing.eyebrow') }}</span>
      <h1>{{ t('pricing.hero_title') }}</h1>
      <p>{{ t('pricing.hero_sub') }}</p>
    </section>

    <PricingPlans :current-plan="userPlan" @upgrade="handleUpgrade" />
  </main>
</template>

<script setup lang="ts">
const { t } = useI18n()
const authStore = useAuthStore()

useHead({ title: t('pricing.page_title') })

const userPlan = computed(() => authStore.user?.plan)

function handleUpgrade() {
  navigateTo('/app/billing')
}
</script>

<style>
.pr-shell { max-width: 920px; margin: 0 auto; padding: 56px 32px 80px; }

.pr-hero { text-align: center; margin-bottom: 48px; }
.pr-hero .eyebrow { color: var(--accent); letter-spacing: 0.12em; }
.pr-hero h1 {
  font-family: var(--font-brand);
  font-weight: 700;
  font-size: 44px;
  line-height: 1.15;
  letter-spacing: -0.02em;
  margin: 14px 0 14px;
  text-wrap: balance;
}
.pr-hero p {
  font-size: 15.5px; color: var(--text-mid); line-height: 1.6;
  margin: 0 auto 24px; max-width: 520px; text-wrap: pretty;
}

@media (max-width: 780px) {
  .pr-shell { padding: 32px 16px 60px; }
  .pr-hero h1 { font-size: 30px; }
  .pr-hero p { font-size: 14px; }
}
</style>
