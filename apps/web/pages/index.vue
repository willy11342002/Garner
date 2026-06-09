<template>
  <main class="landing">
    <section class="landing__hero">
      <span class="eyebrow">PERSONAL KNOWLEDGE BASE</span>
      <h1 class="landing__title">{{ t('landing.title') }}</h1>
      <p class="landing__sub">{{ t('landing.sub') }}</p>
      <div class="landing__cta">
        <NuxtLink to="/app" class="btn btn--accent btn--lg">{{ t('landing.cta_start') }}</NuxtLink>
      </div>
    </section>

    <section class="landing__features">
      <div class="feat-card">
        <span class="feat-card__icon">⚡</span>
        <h3>{{ t('landing.feat_collect_title') }}</h3>
        <p>{{ t('landing.feat_collect_desc') }}</p>
      </div>
      <div class="feat-card">
        <span class="feat-card__icon">🧠</span>
        <h3>{{ t('landing.feat_ai_title') }}</h3>
        <p>{{ t('landing.feat_ai_desc') }}</p>
      </div>
      <div class="feat-card">
        <span class="feat-card__icon">🔍</span>
        <h3>{{ t('landing.feat_search_title') }}</h3>
        <p>{{ t('landing.feat_search_desc') }}</p>
      </div>

    </section>
  </main>
</template>

<script setup lang="ts">
const { t } = useI18n()

useHead({ title: t('landing.page_title') })

const user = useSupabaseUser()
if (user.value) {
  await navigateTo('/app')
}
watch(user, (u) => {
  if (u) navigateTo('/app')
})
</script>

<style>
.landing {
  max-width: 860px;
  margin: 0 auto;
  padding: 80px 32px 100px;
  text-align: center;
}
.landing__hero { margin-bottom: 72px; }
.landing__title {
  font-family: var(--font-brand);
  font-weight: 700;
  font-size: 56px;
  line-height: 1.12;
  letter-spacing: -0.025em;
  margin: 16px 0 18px;
  text-wrap: balance;
}
.landing__sub {
  font-size: 16px;
  color: var(--text-mid);
  line-height: 1.7;
  margin: 0 auto 32px;
  max-width: 540px;
  text-wrap: pretty;
}
.landing__cta { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }

.landing__features {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 240px));
  justify-content: center;
  gap: 16px;
  text-align: left;
  margin-bottom: 48px;
}
.feat-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 22px 20px;
}
.feat-card__icon { font-size: 22px; display: block; margin-bottom: 12px; }
.feat-card h3 { font-family: var(--font-brand); font-weight: 600; font-size: 15px; margin: 0 0 8px; }
.feat-card p { font-size: 13px; color: var(--text-mid); line-height: 1.6; margin: 0; }


@media (max-width: 640px) {
  .landing { padding: 48px 20px 64px; }
  .landing__title { font-size: 36px; }
  .landing__sub { font-size: 14px; }
}
</style>
