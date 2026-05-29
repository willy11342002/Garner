<template>
  <div>
    <header class="ex-head">
      <div class="ex-head__top">
        <div>
          <span class="eyebrow">EXPLORE</span>
          <h1 class="page-title" style="margin-top:4px;">探索 · 漫遊</h1>
        </div>
        <div class="ex-head__stats">
          <div class="stat"><b>{{ stats ? stats.total_items.toLocaleString() : '—' }}</b>知識庫總量</div>
          <div class="stat"><b>{{ stats ? stats.public_collections : '—' }}</b>公開集合</div>
          <div class="stat"><b>{{ stats ? '+' + stats.weekly_new : '—' }}</b>本週新增</div>
        </div>
      </div>
      <nav class="ex-tabs">
        <NuxtLink class="ex-tab" to="/app/explore/focus" active-class="ex-tab--active">Focus<span class="mono">問知識庫</span></NuxtLink>
        <NuxtLink class="ex-tab" to="/app/explore/surprise" active-class="ex-tab--active">Surprise<span class="mono">隨機驚喜</span></NuxtLink>
        <NuxtLink class="ex-tab" to="/app/explore/browse" active-class="ex-tab--active">Browse<span class="mono">公開集合</span></NuxtLink>
      </nav>
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
.ex-head { padding: 24px 32px 0; border-bottom: 1px solid var(--border); max-width: 1400px; margin: 0 auto; }
.ex-head__top { display: flex; align-items: flex-end; gap: 24px; padding-bottom: 14px; }
.ex-head__stats { margin-left: auto; display: flex; gap: 18px; font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); }
.stat b { display: block; color: var(--text); font-size: 16px; font-weight: 500; margin-bottom: 1px; }
.ex-tabs { display: flex; gap: 0; margin-bottom: -1px; }
.ex-tab { padding: 12px 18px 14px; border-bottom: 2px solid transparent; font-family: var(--font-ui); font-size: 13.5px; font-weight: 500; color: var(--text-mid); transition: all .15s ease; }
.ex-tab:hover { color: var(--text); }
.ex-tab--active { color: var(--accent); border-bottom-color: var(--accent); }
.ex-tab .mono { margin-left: 6px; font-size: 10.5px; color: var(--text-dim); }
.ex-tab--active .mono { color: var(--accent); opacity: 0.7; }
.ex-pane { max-width: 1400px; margin: 0 auto; padding: 28px 32px 80px; }

@media (max-width: 980px) { .ex-head { padding: 18px 16px 0; } .ex-pane { padding: 20px 16px 60px; } }
@media (max-width: 640px) { .ex-head__stats { display: none; } }
</style>
