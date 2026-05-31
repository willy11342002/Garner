<template>
  <div>
    <header class="ex-head">
      <div class="ex-head__top">
        <div>
          <span class="eyebrow">{{ $t('explore.eyebrow') }}</span>
          <h1 class="page-title" style="margin-top:4px;">{{ $t('explore.title') }}</h1>
        </div>
        <div class="ex-head__stats">
          <div class="stat"><b>{{ stats ? stats.total_items.toLocaleString() : '—' }}</b>{{ $t('explore.stat_total') }}</div>
          <div class="stat"><b>{{ stats ? stats.public_collections : '—' }}</b>{{ $t('explore.stat_public') }}</div>
          <div class="stat"><b>{{ stats ? '+' + stats.weekly_new : '—' }}</b>{{ $t('explore.stat_weekly') }}</div>
        </div>
      </div>
    </header>

    <NuxtPage />
  </div>
</template>

<script setup lang="ts">
import type { ExploreStats } from '~/types/api'

const apiFetch = useApiFetch()
const stats = ref<ExploreStats | null>(null)

onMounted(async () => {
  try {
    stats.value = await apiFetch<ExploreStats>('/explore/stats')
  } catch {
    // stats remain null, UI shows '—'
  }
})
</script>

<style>
.ex-head { padding: 24px 32px 20px; border-bottom: 1px solid var(--border); max-width: 1400px; margin: 0 auto; }
.ex-head__top { display: flex; align-items: flex-end; gap: 24px; }
.ex-head__stats { margin-left: auto; display: flex; gap: 18px; font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); }
.stat b { display: block; color: var(--text); font-size: 16px; font-weight: 500; margin-bottom: 1px; }
.ex-pane { max-width: 1400px; margin: 0 auto; padding: 28px 32px 80px; }

@media (max-width: 980px) { .ex-head { padding: 18px 16px 0; } .ex-pane { padding: 20px 16px 60px; } }
@media (max-width: 640px) { .ex-head__stats { display: none; } }
</style>
