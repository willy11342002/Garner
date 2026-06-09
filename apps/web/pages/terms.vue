<template>
  <main class="pp-shell">
    <section class="pp-hero">
      <span class="eyebrow">{{ t('terms.eyebrow') }}</span>
      <h1>{{ t('terms.title') }}</h1>
      <p class="pp-updated">{{ t('terms.updated') }}</p>
    </section>

    <article class="pp-body">
      <p class="pp-intro">{{ t('terms.intro') }}</p>

      <section class="pp-section">
        <h2>{{ t('terms.s1_title') }}</h2>
        <p>{{ t('terms.s1_body') }}</p>
      </section>

      <section class="pp-section">
        <h2>{{ t('terms.s2_title') }}</h2>
        <p>{{ t('terms.s2_body') }}</p>
      </section>

      <section class="pp-section">
        <h2>{{ t('terms.s3_title') }}</h2>
        <p>{{ t('terms.s3_body') }}</p>
        <ul class="pp-list">
          <li>{{ t('terms.s3_li1') }}</li>
          <li>{{ t('terms.s3_li2') }}</li>
          <li>{{ t('terms.s3_li3') }}</li>
          <li>{{ t('terms.s3_li4') }}</li>
        </ul>
        <p>{{ t('terms.s3_footer') }}</p>
      </section>

      <section class="pp-section">
        <h2>{{ t('terms.s4_title') }}</h2>
        <p>{{ t('terms.s4_body') }}</p>
      </section>

      <section class="pp-section">
        <h2>{{ t('terms.s5_title') }}</h2>
        <p>{{ t('terms.s5_body') }}</p>
      </section>

      <section class="pp-section">
        <h2>{{ t('terms.s6_title') }}</h2>
        <p>{{ t('terms.s6_body') }}</p>
      </section>

      <section class="pp-section">
        <h2>{{ t('terms.s7_title') }}</h2>
        <p>{{ t('terms.s7_body') }}</p>
      </section>

      <section class="pp-section">
        <h2>{{ t('terms.s8_title') }}</h2>
        <p>{{ t('terms.s8_body') }}</p>
      </section>

      <section class="pp-section">
        <h2>{{ t('terms.s9_title') }}</h2>
        <p>{{ t('terms.s9_body') }}</p>
      </section>

      <section class="pp-section">
        <h2>{{ t('terms.s10_title') }}</h2>
        <p>{{ t('terms.s10_body') }}</p>
      </section>

      <section class="pp-section">
        <h2>{{ t('terms.s11_title') }}</h2>
        <p>{{ t('terms.s11_body') }}</p>
      </section>

      <section class="pp-section">
        <h2>{{ t('terms.s12_title') }}</h2>
        <p>{{ t('terms.s12_privacy') }}</p>
        <p>{{ t('terms.s12_force') }}</p>
        <p>{{ t('terms.s12_severability') }}</p>
        <p>{{ t('terms.s12_waiver') }}</p>
        <p>{{ t('terms.s12_entire') }}</p>
      </section>

      <section class="pp-section">
        <h2>{{ t('terms.s13_title') }}</h2>
        <p>
          {{ t('terms.s13_body') }}
          <a href="https://docs.google.com/forms/d/e/1FAIpQLSdYlIIXPUfQ5DyL-ptIxCwx4G99D4mx9CiwJ9OVQYcGXUDzqw/viewform" target="_blank" rel="noopener" class="pp-link">{{ t('terms.contact_form') }}</a>
        </p>
      </section>
    </article>
  </main>
</template>

<script setup lang="ts">
const { t } = useI18n()

useHead({ title: t('terms.page_title') })
</script>
