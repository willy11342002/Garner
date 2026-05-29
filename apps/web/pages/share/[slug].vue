<template>
  <div v-if="collection">
    <section class="ch-wrap">
      <div class="ch-mosaic" :class="`ch-mosaic--n${mosaicItems.length}`">
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
        <button class="btn btn--accent" @click="goFork">
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
        :href="item.url"
        target="_blank"
        rel="noopener noreferrer"
        @click.prevent="activeItem = item"
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

    <!-- item detail modal -->
    <Transition name="id-fade-t">
      <div v-if="activeItem" class="id-overlay" @click.self="activeItem = null">
        <div class="id-panel fadeup">
          <button class="id-close" @click="activeItem = null">×</button>
          <div class="id-media">
            <img v-if="activeItem.thumbnail_url" :src="activeItem.thumbnail_url" class="id-media__img" :alt="activeItem.title ?? ''" />
            <div v-else :class="`placeholder placeholder--${placeholderColors[0]} id-media__ph`">
              <div class="placeholder__stripes"></div>
            </div>
            <span class="source-badge id-media__badge">{{ sourceBadge(activeItem.source_type) }}</span>
          </div>
          <div class="id-body">
            <div class="id-body__meta mono">{{ sourceLabel(activeItem.source_type) }}</div>
            <h1 class="id-body__title">{{ activeItem.title || activeItem.url }}</h1>
            <div v-if="activeItem.summary" class="id-body__summary">
              <div class="id-body__summary-label mono">SUMMARY</div>
              <p class="id-body__summary-text">{{ activeItem.summary }}</p>
            </div>
            <div class="id-body__actions">
              <a :href="activeItem.url" target="_blank" rel="noopener noreferrer" class="btn btn--accent">開啟原文 →</a>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <section class="rec-section">
      <header class="rec-head">
        <span class="eyebrow">{{ t('share.you_may_like') }}</span>
        <span class="line"></span>
        <NuxtLink to="/app/explore" class="mono" style="font-size:11px; color:var(--text-mid);">{{ t('share.see_all') }}</NuxtLink>
      </header>
      <div class="rec-scroll">
        <NuxtLink v-for="(rec, ri) in recs" :key="rec.slug" class="rec-card" :to="`/share/${rec.slug}`">
          <div class="rec-card__cover">
            <div class="t">
              <img v-if="rec.cover_thumbnails[0]" :src="rec.cover_thumbnails[0]" :alt="rec.title" style="width:100%;height:100%;object-fit:cover;">
              <div v-else :class="`placeholder placeholder--${placeholderColors[ri % placeholderColors.length]}`"><div class="placeholder__stripes"></div></div>
            </div>
            <div class="t">
              <img v-if="rec.cover_thumbnails[1]" :src="rec.cover_thumbnails[1]" :alt="rec.title" style="width:100%;height:100%;object-fit:cover;">
              <div v-else :class="`placeholder placeholder--${placeholderColors[(ri + 2) % placeholderColors.length]}`"><div class="placeholder__stripes"></div></div>
            </div>
          </div>
          <div class="rec-card__body">
            <h4 class="rec-card__title">{{ rec.title }}</h4>
            <div class="rec-card__meta">@{{ rec.author_username }} · {{ rec.item_count }} items · ⑂ {{ rec.fork_count }}</div>
          </div>
        </NuxtLink>
        <div v-if="!recs.length" class="rec-empty">暫無推薦集合</div>
      </div>
    </section>
  </div>

  <div v-else-if="error" class="empty-state" style="padding:80px 32px;text-align:center;">
    <p style="color:var(--text-mid);">{{ t('share.not_found') }}</p>
    <NuxtLink to="/app/explore" class="btn" style="margin-top:16px;">{{ t('share.explore_btn') }}</NuxtLink>
  </div>
</template>

<script setup lang="ts">
import type { CollectionShareItem, CollectionShareRead, PublicCollectionRead } from '~/types/api'

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

const { data: recsData } = await useAsyncData<PublicCollectionRead[]>(
  `share-recs-${slug}`,
  () => ($fetch(`${config.public.apiBase}/share/recommendations`, {
    query: { exclude_slug: slug, limit: 8 }
  }) as Promise<PublicCollectionRead[]>).catch(() => [])
)

useHead({
  title: collection.value ? `${collection.value.title} — Vela` : 'Vela',
})

const placeholderColors = ['a', 'b', 'c', 'd', 'e']

// 最多取 5 張做 mosaic；若 items 超過 5 張仍只顯示前 5
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

// Item detail drawer
const activeItem = ref<CollectionShareItem | null>(null)

function goFork() {
  if (!session.value) {
    router.push('/login')
    return
  }
  router.push(`/app/share?from_slug=${slug}`)
}

const recs = computed(() => recsData.value ?? [])
</script>

<style>
/* styles moved to assets/css/collection-view.css */
.ch-wrap {
  position: relative;
  height: 320px;
  margin-bottom: 0;
  overflow: hidden;
}
.ch-mosaic {
  position: absolute; inset: 0;
  display: grid;
  gap: 2px;
}
.ch-mosaic .tile { overflow: hidden; }

/* 1 item: full area */
.ch-mosaic--n1 {
  grid-template-columns: 1fr;
  grid-template-rows: 1fr;
}

/* 2 items: side by side */
.ch-mosaic--n2 {
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr;
}

/* 3 items: 1 large left + 2 stacked right */
.ch-mosaic--n3 {
  grid-template-columns: 2fr 1fr;
  grid-template-rows: 1fr 1fr;
}
.ch-mosaic--n3 .tile:nth-child(1) { grid-row: 1 / span 2; }

/* 4 items: 2x2 */
.ch-mosaic--n4 {
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
}

/* 5 items: original layout */
.ch-mosaic--n5 {
  grid-template-columns: 2fr 1fr 1fr 2fr;
  grid-template-rows: 1fr 1fr;
}
.ch-mosaic--n5 .tile:nth-child(1) { grid-row: 1 / span 2; }
.ch-mosaic--n5 .tile:nth-child(4) { grid-column: 4; grid-row: 1 / span 2; }
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
.rec-empty { font-size: 13px; color: var(--text-dim); padding: 20px 0; }

/* ── item detail drawer ── */
.item-drawer {
  position: fixed;
  inset: 0;
  z-index: 400;
  background: rgba(0,0,0,0.45);
  display: flex;
  justify-content: flex-end;
}
.item-drawer__panel {
  width: 440px;
  max-width: 100vw;
  height: 100%;
  background: var(--surface);
  border-left: 1px solid var(--border);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  position: relative;
  box-shadow: -16px 0 48px rgba(0,0,0,0.18);
}
.item-drawer__close {
  position: absolute;
  top: 14px; right: 14px;
  z-index: 2;
  width: 32px; height: 32px;
  border-radius: 8px;
  background: var(--surface2);
  border: 1px solid var(--border);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  color: var(--text-mid);
  transition: background .12s, color .12s;
}
.item-drawer__close:hover { background: var(--bg); color: var(--text); }
.item-drawer__thumb {
  height: 240px;
  flex-shrink: 0;
  position: relative;
  overflow: hidden;
  background: var(--surface2);
}
.item-drawer__badge { bottom: 12px; right: 12px; }
.item-drawer__body {
  padding: 22px 24px 40px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  flex: 1;
}
.item-drawer__title {
  font-family: var(--font-brand);
  font-size: 20px;
  font-weight: 700;
  line-height: 1.3;
  margin: 0;
  letter-spacing: -0.01em;
}
.item-drawer__summary {
  font-size: 13.5px;
  line-height: 1.7;
  color: var(--text-mid);
  margin: 0;
  flex: 1;
}
.item-drawer__cta {
  align-self: flex-start;
  display: flex;
  align-items: center;
  gap: 7px;
  margin-top: 4px;
}

/* drawer transition */
.drawer-enter-active, .drawer-leave-active { transition: opacity .2s ease; }
.drawer-enter-active .item-drawer__panel, .drawer-leave-active .item-drawer__panel { transition: transform .25s cubic-bezier(.32,0,.67,0); }
.drawer-enter-from, .drawer-leave-to { opacity: 0; }
.drawer-enter-from .item-drawer__panel, .drawer-leave-to .item-drawer__panel { transform: translateX(100%); }

@media (max-width: 640px) {
  .item-drawer { align-items: flex-end; justify-content: stretch; }
  .item-drawer__panel { width: 100%; height: 85vh; border-left: none; border-top: 1px solid var(--border); border-radius: 16px 16px 0 0; }
  .item-drawer__thumb { height: 180px; }
}
@media (max-width: 768px) {
  .ch-content { left: 18px; right: 18px; bottom: 18px; }
  .ch-title { font-size: 24px; }
  .cta-bar { padding: 10px 16px; flex-wrap: wrap; }
  .cta-bar__actions { width: 100%; }
  .content-grid { padding: 20px 16px 40px; gap: 10px; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); }
  .rec-section { padding: 24px 16px 40px; }
}
</style>
