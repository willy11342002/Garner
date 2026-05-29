<template>
  <div v-if="collection">
    <section class="ch-wrap">
      <div class="ch-mosaic" :class="`ch-mosaic--n${mosaicItems.length}`">
        <div v-for="(item, i) in mosaicItems" :key="item.id" class="tile">
          <img
            v-if="item.thumbnail_url"
            :src="item.thumbnail_url"
            :alt="item.title ?? ''"
            style="width:100%;height:100%;object-fit:cover;"
          />
          <div v-else :class="`placeholder placeholder--${colors[i % colors.length]}`">
            <div class="placeholder__stripes"></div>
          </div>
        </div>
      </div>
      <div class="ch-content">
        <div class="ch-author">
          <span class="ch-author__av" style="background:linear-gradient(135deg,var(--tag-c),var(--tag-a));overflow:hidden;">
            <img
              v-if="authStore.user?.avatar_url"
              :src="authStore.user.avatar_url"
              style="width:100%;height:100%;object-fit:cover;border-radius:50%;"
            />
            <template v-else>{{ authorInitials }}</template>
          </span>
          <span class="ch-author__name">@{{ authStore.user?.username }}</span>
          <span class="ch-author__suffix">的集合</span>
        </div>
        <h1 class="ch-title">{{ collection.title }}</h1>
        <div class="ch-stats">
          <span class="ch-stat">{{ collection.items.length }} 個項目</span>
          <span class="ch-stat">⑂ {{ collection.fork_count }} forks</span>
          <span class="ch-stat">{{ createdAgo }}</span>
          <span class="ch-stat">
            <span :class="`myvis-dot myvis-dot--${collection.visibility}`"></span>
            {{ visLabel }}
          </span>
        </div>
      </div>
    </section>

    <div class="cta-bar">
      <span class="cta-bar__title">{{ collection.title }}</span>
      <span class="cta-bar__sub">{{ collection.items.length }} 個項目</span>
      <div class="cta-bar__actions">
        <template v-if="collection.visibility !== 'private'">
          <span class="mycta-url mono">{{ shareUrl }}</span>
          <button class="btn" @click="copyUrl">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            {{ copied ? '已複製' : '複製連結' }}
          </button>
        </template>
        <NuxtLink to="/app/collections" class="btn btn--accent">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          管理集合
        </NuxtLink>
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
        <div class="icard__thumb">
          <img
            v-if="item.thumbnail_url"
            :src="item.thumbnail_url"
            :alt="item.title ?? ''"
            style="width:100%;height:100%;object-fit:cover;"
          />
          <div v-else :class="`placeholder placeholder--${colors[i % colors.length]}`">
            <div class="placeholder__stripes"></div>
          </div>
          <span class="source-badge">{{ sourceBadge(item.source_type) }}</span>
        </div>
        <div class="icard__body">
          <h3 class="icard__title">{{ item.title || item.url }}</h3>
          <div class="icard__foot">
            <span class="tag-chip tag-chip--a">{{ sourceLabel(item.source_type) }}</span>
            <a :href="item.url" target="_blank" rel="noopener noreferrer" @click.stop>原文</a>
          </div>
        </div>
      </a>
    </section>

    <Transition name="id-fade-t">
      <div v-if="activeItem" class="id-overlay" @click.self="activeItem = null">
        <div class="id-panel fadeup">
          <button class="id-close" @click="activeItem = null">×</button>
          <div class="id-media">
            <img v-if="activeItem.thumbnail_url" :src="activeItem.thumbnail_url" class="id-media__img" :alt="activeItem.title ?? ''" />
            <div v-else :class="`placeholder placeholder--${colors[0]} id-media__ph`">
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
  </div>

  <div v-else-if="error" class="empty-state" style="padding:80px 32px;text-align:center;">
    <p style="color:var(--text-mid);">找不到這個集合</p>
    <NuxtLink to="/app/collections" class="btn" style="margin-top:16px;">回到我的集合</NuxtLink>
  </div>
</template>

<script setup lang="ts">
import type { CollectionDetail, Item } from '~/types/api'

definePageMeta({ ssr: false })

const route = useRoute()
const apiFetch = useApiFetch()
const authStore = useAuthStore()
const id = route.params.id as string

const { data: collection, error } = await useAsyncData<CollectionDetail>(
  `my-collection-${id}`,
  () => apiFetch<CollectionDetail>(`/collections/${id}`)
)

const colors = ['a', 'b', 'c', 'd', 'e']
const activeItem = ref<Item | null>(null)
const copied = ref(false)

const mosaicItems = computed(() => (collection.value?.items ?? []).slice(0, 5))

const authorInitials = computed(() => (authStore.user?.username ?? '').slice(0, 2).toUpperCase())

const createdAgo = computed(() => {
  if (!collection.value) return ''
  const days = Math.floor((Date.now() - new Date(collection.value.created_at).getTime()) / 86400000)
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 30) return `${days} 天前`
  if (days < 365) return `${Math.floor(days / 30)} 個月前`
  return `${Math.floor(days / 365)} 年前`
})

const visLabel = computed(() => {
  const map: Record<string, string> = { private: '私人', link: '連結分享', public: '公開' }
  return map[collection.value?.visibility ?? 'private'] ?? ''
})

const shareUrl = computed(() => {
  if (typeof window === 'undefined' || !collection.value) return ''
  return `${window.location.origin}/share/${collection.value.slug}`
})

async function copyUrl() {
  if (!shareUrl.value) return
  await navigator.clipboard.writeText(shareUrl.value)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

function sourceBadge(t: string | null) {
  if (t === 'youtube') return '▶'
  if (t === 'ig') return 'IG'
  return '⎘'
}

function sourceLabel(t: string | null) {
  if (t === 'youtube') return 'YouTube'
  if (t === 'ig') return 'Instagram'
  return '文章'
}
</script>

<style>
/* styles from collection-view.css (global) */
.mycta-url {
  font-size: 11px;
  color: var(--text-dim);
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.myvis-dot {
  display: inline-block;
  width: 7px; height: 7px;
  border-radius: 50%;
  margin-right: 4px;
  vertical-align: middle;
}
.myvis-dot--public  { background: #34c759; }
.myvis-dot--link    { background: #ff9f0a; }
.myvis-dot--private { background: var(--text-dim); }
</style>
