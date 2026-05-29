<template>
  <div v-if="collection" :class="{ 'pick-mode': pickMode }">
    <section class="ch-wrap">
      <div class="ch-mosaic">
        <div
          v-for="(item, i) in mosaicItems"
          :key="item.id"
          class="tile"
        >
          <img
            v-if="item.thumbnail_url"
            :src="item.thumbnail_url"
            :alt="item.title ?? ''"
            style="width:100%;height:100%;object-fit:cover;"
          />
          <div v-else :class="`placeholder placeholder--${placeholderColors[i % placeholderColors.length]}`">
            <div class="placeholder__stripes"></div>
          </div>
        </div>
        <div v-for="i in Math.max(0, 5 - mosaicItems.length)" :key="`fill-${i}`" class="tile">
          <div :class="`placeholder placeholder--${placeholderColors[(mosaicItems.length + i - 1) % placeholderColors.length]}`">
            <div class="placeholder__stripes"></div>
          </div>
        </div>
      </div>
      <div class="ch-content">
        <div class="ch-author">
          <span class="ch-author__av" :style="avatarStyle">
            <img
              v-if="collection.author_avatar_url"
              :src="collection.author_avatar_url"
              :alt="collection.author_username"
              style="width:100%;height:100%;object-fit:cover;border-radius:50%;"
            />
            <template v-else>{{ authorInitials }}</template>
          </span>
          <span class="ch-author__name">@{{ collection.author_username }}</span>
          <span class="ch-author__suffix">{{ t('share.author_suffix') }}</span>
        </div>
        <h1 class="ch-title">{{ collection.title }}</h1>
        <div class="ch-stats">
          <span class="ch-stat">{{ t('share.stat_items', { count: collection.items.length }) }}</span>
          <span class="ch-stat">{{ t('share.stat_forks', { count: collection.fork_count }) }}</span>
          <span class="ch-stat">{{ t('share.stat_created', { date: createdAgo }) }}</span>
        </div>
      </div>
    </section>

    <div class="cta-bar">
      <span class="ch-author__av" style="width:28px;height:28px;font-size:10px;">
        <img
          v-if="collection.author_avatar_url"
          :src="collection.author_avatar_url"
          style="width:100%;height:100%;object-fit:cover;border-radius:50%;"
        />
        <template v-else>{{ authorInitials }}</template>
      </span>
      <span class="cta-bar__title">{{ collection.title }}</span>
      <span class="cta-bar__sub">{{ t('share.cta_items', { count: collection.items.length }) }} · @{{ collection.author_username }}</span>
      <div class="cta-bar__actions">
        <button class="btn" @click="togglePickMode">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
          {{ pickMode ? t('share.pick_selected', { count: selectedIds.size }) : t('share.pick_mode') }}
        </button>
        <button
          v-if="pickMode && selectedIds.size > 0"
          class="btn btn--accent"
          :disabled="forking"
          @click="doFork(false)"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="6" cy="3" r="2"/><circle cx="6" cy="21" r="2"/><circle cx="18" cy="12" r="2"/><path d="M6 5v6a4 4 0 0 0 4 4h6M6 13v6"/></svg>
          {{ t('share.fork_selected', { count: selectedIds.size }) }}
        </button>
        <button
          v-else
          class="btn btn--accent"
          :disabled="forking"
          @click="doFork(true)"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="6" cy="3" r="2"/><circle cx="6" cy="21" r="2"/><circle cx="18" cy="12" r="2"/><path d="M6 5v6a4 4 0 0 0 4 4h6M6 13v6"/></svg>
          {{ t('share.fork_all', { count: collection.items.length }) }}
        </button>
      </div>
    </div>

    <section class="content-grid">
      <a
        v-for="(item, i) in collection.items"
        :key="item.id"
        class="icard"
        :class="{ sel: selectedIds.has(item.id) }"
        :href="item.url"
        target="_blank"
        rel="noopener noreferrer"
        @click.prevent="handleItemClick($event, item)"
      >
        <span class="icard__check">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
        </span>
        <div class="icard__thumb">
          <img
            v-if="item.thumbnail_url"
            :src="item.thumbnail_url"
            :alt="item.title ?? ''"
            style="width:100%;height:100%;object-fit:cover;"
          />
          <div v-else :class="`placeholder placeholder--${placeholderColors[i % placeholderColors.length]}`">
            <div class="placeholder__stripes"></div>
          </div>
          <span class="source-badge">{{ sourceBadge(item.source_type) }}</span>
        </div>
        <div class="icard__body">
          <h3 class="icard__title">{{ item.title || item.url }}</h3>
          <div class="icard__foot">
            <span class="tag-chip tag-chip--a">{{ sourceLabel(item.source_type) }}</span>
            <a :href="item.url" target="_blank" rel="noopener noreferrer" @click.stop>{{ t('share.source_link') }}</a>
          </div>
        </div>
      </a>
    </section>

    <section class="rec-section">
      <header class="rec-head">
        <span class="eyebrow">{{ t('share.you_may_like') }}</span>
        <span class="line"></span>
        <NuxtLink to="/app/explore" class="mono" style="font-size:11px; color:var(--text-mid);">{{ t('share.see_all') }}</NuxtLink>
      </header>
      <div class="rec-scroll">
        <NuxtLink v-for="rec in recs" :key="rec.slug" class="rec-card" :to="`/share/${rec.slug}`">
          <div class="rec-card__cover">
            <div class="t"><div :class="`placeholder placeholder--${rec.c1}`"><div class="placeholder__stripes"></div></div></div>
            <div class="t"><div :class="`placeholder placeholder--${rec.c2}`"><div class="placeholder__stripes"></div></div></div>
          </div>
          <div class="rec-card__body">
            <h4 class="rec-card__title">{{ rec.title }}</h4>
            <div class="rec-card__meta">{{ rec.meta }}</div>
          </div>
        </NuxtLink>
      </div>
    </section>
  </div>

  <div v-else-if="error" class="empty-state" style="padding:80px 32px;text-align:center;">
    <p style="color:var(--text-mid);">{{ t('share.not_found') }}</p>
    <NuxtLink to="/app/explore" class="btn" style="margin-top:16px;">{{ t('share.explore_btn') }}</NuxtLink>
  </div>
</template>

<script setup lang="ts">
import type { CollectionForkCreate, CollectionShareRead } from '~/types/api'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const config = useRuntimeConfig()
const session = useSupabaseSession()
const slug = route.params.slug as string

const { data: collection, error } = await useAsyncData<CollectionShareRead>(
  `share-${slug}`,
  () => $fetch(`${config.public.apiBase}/share/${slug}`)
)

useHead({
  title: collection.value ? `${collection.value.title} — Vela` : 'Vela',
})

const placeholderColors = ['a', 'b', 'c', 'd', 'e']

const mosaicItems = computed(() => (collection.value?.items ?? []).slice(0, 5))

const authorInitials = computed(() => {
  const name = collection.value?.author_username ?? ''
  return name.slice(0, 2).toUpperCase()
})

const avatarStyle = computed(() => ({
  background: 'linear-gradient(135deg, var(--tag-c), var(--tag-a))',
}))

const createdAgo = computed(() => {
  if (!collection.value) return ''
  const diff = Date.now() - new Date(collection.value.created_at).getTime()
  const days = Math.floor(diff / 86400000)
  if (days === 0) return t('share.date_today')
  if (days === 1) return t('share.date_yesterday')
  if (days < 30) return t('share.date_days_ago', { days })
  if (days < 365) return t('share.date_months_ago', { months: Math.floor(days / 30) })
  return t('share.date_years_ago', { years: Math.floor(days / 365) })
})

function sourceBadge(sourceType: string | null): string {
  if (sourceType === 'youtube') return '▶'
  if (sourceType === 'ig') return 'IG'
  return '⎘'
}

function sourceLabel(sourceType: string | null): string {
  if (sourceType === 'youtube') return 'YouTube'
  if (sourceType === 'ig') return 'Instagram'
  return t('share.source_article')
}

// Pick / fork
const pickMode = ref(false)
const selectedIds = reactive(new Set<string>())
const forking = ref(false)

function togglePickMode() {
  pickMode.value = !pickMode.value
  if (!pickMode.value) selectedIds.clear()
}

function handleItemClick(e: MouseEvent, item: { id: string; url: string }) {
  if (!pickMode.value) {
    window.open(item.url, '_blank', 'noopener,noreferrer')
    return
  }
  e.preventDefault()
  if (selectedIds.has(item.id)) {
    selectedIds.delete(item.id)
  } else {
    selectedIds.add(item.id)
  }
}

async function doFork(all: boolean) {
  if (!session.value) {
    router.push('/login')
    return
  }
  if (!collection.value) return
  forking.value = true
  try {
    const apiFetch = useApiFetch()
    const body: CollectionForkCreate = {
      content_ids: all ? [] : Array.from(selectedIds),
    }
    const newCol = await apiFetch<{ id: string }>(`/collections/${collection.value.id}/fork`, {
      method: 'POST',
      body,
    })
    router.push(`/app/collection/${newCol.id}`)
  } finally {
    forking.value = false
  }
}

// Static recs (placeholder until recommendation engine is built)
const recs = [
  { slug: 'tokyo-local',  title: '東京 7 天 — 在地人路線',      c1: 'a', c2: 'b', meta: '@tk_local · 28 items · ⑂ 256' },
  { slug: 'okinawa',      title: '沖繩離島跳島 9 天',            c1: 'c', c2: 'e', meta: '@ocean_runner · 36 items · ⑂ 142' },
  { slug: 'kanazawa',     title: '北陸新幹線開通後的金澤行程',   c1: 'd', c2: 'a', meta: '@yuki_travels · 22 items · ⑂ 89' },
  { slug: 'kyoto-hidden', title: '京都祕境 — 不在 Google Maps 的 12 個地點', c1: 'b', c2: 'c', meta: '@hiddenkyoto · 18 items · ⑂ 67' },
]
</script>

<style>
/* Shares the same CSS as app/collection/[id].vue — kept local to avoid flash */
.ch-wrap {
  position: relative;
  height: 320px;
  margin-bottom: 0;
  overflow: hidden;
}
.ch-mosaic {
  position: absolute; inset: 0;
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 2fr;
  grid-template-rows: 1fr 1fr;
  gap: 2px;
}
.ch-mosaic .tile { overflow: hidden; }
.ch-mosaic .tile:nth-child(1) { grid-row: 1 / span 2; }
.ch-mosaic .tile:nth-child(4) { grid-column: 4; grid-row: 1 / span 2; }
.ch-mosaic::after {
  content: '';
  position: absolute; inset: 0;
  background: linear-gradient(180deg, transparent 30%, var(--bg) 95%);
}
.ch-content {
  position: absolute;
  left: 32px; right: 32px;
  bottom: 28px;
  z-index: 2;
  max-width: 720px;
}
.ch-author {
  display: inline-flex; align-items: center; gap: 10px;
  margin-bottom: 12px;
}
.ch-author__av {
  width: 36px; height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--tag-c), var(--tag-a));
  color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
  font-family: var(--font-mono); font-size: 12px; font-weight: 500;
  border: 1px solid var(--border2);
  overflow: hidden;
}
.ch-author__name { font-weight: 500; font-size: 13.5px; }
.ch-author__suffix { font-family: var(--font-mono); font-size: 11px; color: var(--text-mid); margin-left: 4px; }
.ch-title {
  font-family: var(--font-brand);
  font-weight: 700;
  font-size: 36px;
  letter-spacing: -0.02em;
  margin: 0 0 10px;
  line-height: 1.15;
  text-wrap: balance;
}
.ch-stats {
  display: flex; gap: 14px; flex-wrap: wrap;
  font-family: var(--font-mono); font-size: 11.5px;
  color: var(--text-mid);
}
.ch-stats b { color: var(--text); font-weight: 500; }
.ch-stat::after { content: '·'; margin-left: 14px; color: var(--text-dim); }
.ch-stat:last-child::after { display: none; }
.cta-bar {
  position: sticky; top: 52px;
  z-index: 30;
  padding: 12px 32px;
  background: var(--nav-bg);
  backdrop-filter: blur(18px);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 12px;
}
.cta-bar__title { font-family: var(--font-brand); font-weight: 600; font-size: 14px; }
.cta-bar__sub { margin-left: 12px; font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); }
.cta-bar__actions { margin-left: auto; display: flex; gap: 8px; }
.content-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
  padding: 28px 32px 48px;
  max-width: 1400px;
  margin: 0 auto;
}
.icard {
  position: relative;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all .2s ease;
  text-decoration: none;
  color: inherit;
}
.icard:hover { transform: translateY(-3px); border-color: var(--border2); box-shadow: 0 12px 28px -12px var(--shadow); }
.icard__check {
  position: absolute; top: 10px; left: 10px;
  z-index: 3;
  width: 22px; height: 22px;
  border-radius: 6px;
  background: rgba(0,0,0,0.55);
  border: 1.5px solid #fff;
  backdrop-filter: blur(4px);
  display: none; align-items: center; justify-content: center;
  color: #fff;
}
.pick-mode .icard__check { display: inline-flex; }
.icard.sel .icard__check { background: var(--accent); border-color: var(--accent); color: var(--accent-fg); }
.icard__check svg { width: 14px; height: 14px; }
.icard__thumb { height: 130px; position: relative; overflow: hidden; }
.icard__thumb .source-badge { position: absolute; right: 8px; bottom: 8px; }
.icard__body { padding: 12px 14px 14px; display: flex; flex-direction: column; gap: 10px; }
.icard__title {
  font-size: 13px; font-weight: 500;
  line-height: 1.45; margin: 0;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.icard__foot { display: flex; align-items: center; justify-content: space-between; }
.icard__foot a { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); transition: color .15s ease; }
.icard__foot a:hover { color: var(--accent); }
.rec-section { border-top: 1px solid var(--border); padding: 30px 32px 60px; max-width: 1400px; margin: 0 auto; }
.rec-head { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.rec-head .line { flex: 1; height: 1px; background: var(--border); }
.rec-scroll { display: flex; gap: 14px; overflow-x: auto; padding-bottom: 8px; scrollbar-width: none; }
.rec-scroll::-webkit-scrollbar { display: none; }
.rec-card {
  flex: 0 0 240px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; overflow: hidden;
  transition: all .2s ease; text-decoration: none; color: inherit;
}
.rec-card:hover { transform: translateY(-3px); border-color: var(--border2); }
.rec-card__cover { height: 100px; display: grid; grid-template-columns: 2fr 1fr; gap: 2px; }
.rec-card__cover .t { overflow: hidden; }
.rec-card__body { padding: 12px 14px 14px; }
.rec-card__title { font-family: var(--font-brand); font-weight: 600; font-size: 14px; margin: 0 0 6px; line-height: 1.3; }
.rec-card__meta { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-mid); }
@media (max-width: 768px) {
  .ch-content { left: 18px; right: 18px; bottom: 18px; }
  .ch-title { font-size: 24px; }
  .cta-bar { padding: 10px 16px; flex-wrap: wrap; }
  .cta-bar__actions { width: 100%; }
  .content-grid { padding: 20px 16px 40px; gap: 10px; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); }
  .rec-section { padding: 24px 16px 40px; }
}
</style>
