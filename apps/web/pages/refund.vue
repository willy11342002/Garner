<template>
  <main class="pp-shell">
    <section class="pp-hero">
      <span class="eyebrow">{{ t('refund.eyebrow') }}</span>
      <h1>{{ t('refund.title') }}</h1>
      <p class="pp-updated">{{ t('refund.updated') }}</p>
    </section>

    <article class="pp-body">
      <p class="pp-intro">{{ t('refund.intro') }}</p>

      <section class="pp-section">
        <h2>{{ t('refund.s1_title') }}</h2>
        <p>{{ t('refund.s1_body') }}</p>
      </section>

      <section class="pp-section">
        <h2>{{ t('refund.s2_title') }}</h2>
        <p>{{ t('refund.s2_body') }}</p>
      </section>

      <section class="pp-section">
        <h2>{{ t('refund.s3_title') }}</h2>
        <p>{{ t('refund.s3_body') }}</p>
      </section>

      <section class="pp-section">
        <h2>{{ t('refund.s4_title') }}</h2>
        <p>{{ t('refund.s4_body') }}</p>
      </section>

      <section class="pp-section">
        <h2>{{ t('refund.s5_title') }}</h2>
        <p>
          {{ t('refund.s5_body') }}
          <a
            href="https://docs.google.com/forms/d/e/1FAIpQLSdYlIIXPUfQ5DyL-ptIxCwx4G99D4mx9CiwJ9OVQYcGXUDzqw/viewform"
            target="_blank"
            rel="noopener"
            class="pp-link"
          >{{ t('refund.contact_form') }}</a>
        </p>
      </section>
    </article>
  </main>
  <LayoutAppFooter />
</template>

<script setup lang="ts">
const { t } = useI18n()

useHead({ title: t('refund.page_title') })
</script>
