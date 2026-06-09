<template>
  <main class="pp-shell">
    <section class="pp-hero">
      <span class="eyebrow">{{ t('privacy.eyebrow') }}</span>
      <h1>{{ t('privacy.title') }}</h1>
      <p class="pp-updated">{{ t('privacy.updated') }}</p>
    </section>

    <article class="pp-body">
      <p class="pp-intro">{{ t('privacy.intro') }}</p>

      <section class="pp-section">
        <h2>{{ t('privacy.s1_title') }}</h2>
        <p>{{ t('privacy.s1_body') }}</p>
      </section>

      <section class="pp-section">
        <h2>{{ t('privacy.s2_title') }}</h2>
        <h3>{{ t('privacy.s2_account_title') }}</h3>
        <p>{{ t('privacy.s2_account_body') }}</p>
        <h3>{{ t('privacy.s2_content_title') }}</h3>
        <p>{{ t('privacy.s2_content_body') }}</p>
        <h3>{{ t('privacy.s2_analytics_title') }}</h3>
        <p>{{ t('privacy.s2_analytics_body') }}</p>
        <h3>{{ t('privacy.s2_errors_title') }}</h3>
        <p>{{ t('privacy.s2_errors_body') }}</p>
        <h3>{{ t('privacy.s2_payment_title') }}</h3>
        <p>{{ t('privacy.s2_payment_body') }}</p>
      </section>

      <section class="pp-section">
        <h2>{{ t('privacy.s3_title') }}</h2>
        <p>{{ t('privacy.s3_body') }}</p>
        <ul class="pp-list">
          <li>{{ t('privacy.s3_li1') }}</li>
          <li>{{ t('privacy.s3_li2') }}</li>
        </ul>
        <p>{{ t('privacy.s3_note') }}</p>
      </section>

      <section class="pp-section">
        <h2>{{ t('privacy.s4_title') }}</h2>
        <p>{{ t('privacy.s4_body') }}</p>
      </section>

      <section class="pp-section">
        <h2>{{ t('privacy.s5_title') }}</h2>
        <p>{{ t('privacy.s5_body') }}</p>
        <ul class="pp-list">
          <li>{{ t('privacy.s5_li1') }}</li>
          <li>{{ t('privacy.s5_li2') }}</li>
          <li>{{ t('privacy.s5_li3') }}</li>
          <li>{{ t('privacy.s5_li4') }}</li>
          <li>{{ t('privacy.s5_li5') }}</li>
          <li>{{ t('privacy.s5_li6') }}</li>
          <li>{{ t('privacy.s5_li7') }}</li>
        </ul>
      </section>

      <section class="pp-section">
        <h2>{{ t('privacy.s6_title') }}</h2>
        <p>{{ t('privacy.s6_body') }}</p>
      </section>

      <section class="pp-section">
        <h2>{{ t('privacy.s7_title') }}</h2>
        <p>{{ t('privacy.s7_body') }}</p>
        <ul class="pp-list">
          <li>{{ t('privacy.s7_li1') }}</li>
          <li>{{ t('privacy.s7_li2') }}</li>
          <li>{{ t('privacy.s7_li3') }}</li>
          <li>{{ t('privacy.s7_li4') }}</li>
          <li>{{ t('privacy.s7_li5') }}</li>
          <li>{{ t('privacy.s7_li6') }}</li>
        </ul>
      </section>

      <section class="pp-section">
        <h2>{{ t('privacy.s8_title') }}</h2>
        <p>{{ t('privacy.s8_body') }}</p>
      </section>

      <section class="pp-section">
        <h2>{{ t('privacy.s9_title') }}</h2>
        <p>{{ t('privacy.s9_body') }}</p>
      </section>

      <section class="pp-section">
        <h2>{{ t('privacy.s10_title') }}</h2>
        <p>{{ t('privacy.s10_body') }}</p>
      </section>

      <section class="pp-section">
        <h2>{{ t('privacy.s11_title') }}</h2>
        <p>
          {{ t('privacy.s11_body') }}
          <a href="https://docs.google.com/forms/d/e/1FAIpQLSdYlIIXPUfQ5DyL-ptIxCwx4G99D4mx9CiwJ9OVQYcGXUDzqw/viewform" target="_blank" rel="noopener" class="pp-link">{{ t('privacy.contact_form') }}</a>
        </p>
      </section>
    </article>
  </main>
  <LayoutAppFooter />
</template>

<script setup lang="ts">
const { t } = useI18n()

useHead({ title: t('privacy.page_title') })
</script>

<style>
.pp-shell {
  max-width: 680px;
  margin: 0 auto;
  padding: 56px 32px 100px;
}

.pp-hero {
  margin-bottom: 40px;
  border-bottom: 1px solid var(--border);
  padding-bottom: 32px;
}
.pp-hero h1 {
  font-family: var(--font-brand);
  font-weight: 700;
  font-size: 36px;
  line-height: 1.2;
  letter-spacing: -0.02em;
  margin: 12px 0 10px;
}
.pp-updated {
  font-size: 13px;
  color: var(--text-dim);
  margin: 0;
  font-family: var(--font-mono);
}

.pp-intro {
  font-size: 15px;
  line-height: 1.75;
  color: var(--text-mid);
  margin-bottom: 40px;
}

.pp-section {
  margin-bottom: 36px;
}
.pp-section h2 {
  font-family: var(--font-brand);
  font-weight: 600;
  font-size: 17px;
  margin: 0 0 12px;
  color: var(--text);
}
.pp-section h3 {
  font-family: var(--font-brand);
  font-weight: 600;
  font-size: 14px;
  margin: 20px 0 6px;
  color: var(--text-mid);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.pp-section p {
  font-size: 14px;
  line-height: 1.75;
  color: var(--text-mid);
  margin: 0 0 8px;
}

.pp-list {
  padding-left: 20px;
  margin: 8px 0 12px;
}
.pp-list li {
  font-size: 14px;
  line-height: 1.75;
  color: var(--text-mid);
  margin-bottom: 4px;
}

.pp-link {
  color: var(--accent);
  text-decoration: none;
}
.pp-link:hover { text-decoration: underline; }

@media (max-width: 640px) {
  .pp-shell { padding: 32px 20px 64px; }
  .pp-hero h1 { font-size: 26px; }
}
</style>
