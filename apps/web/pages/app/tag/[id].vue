<script setup lang="ts">
import type { Item, Tag } from '~/types/api'

const route = useRoute()
const apiFetch = useApiFetch()
const { localize } = useI18nContent()

const tagId = route.params.id as string

const tag = ref<Tag | null>(null)
const items = ref<Item[]>([])
const loading = ref(true)
const error = ref(false)

useHead(computed(() => ({
  title: tag.value ? `Garner — ${localize(tag.value.name_i18n, tag.value.name)}` : 'Garner',
})))

const TAG_COLORS = ['a', 'b', 'c', 'd', 'e'] as const

function sourceLabel(url: string) {
  if (/youtu/.test(url)) return '▶ YouTube'
  if (/instagram\.com/.test(url)) return 'IG'
  return 'Article'
}

function cardTitle(url: string, title: string | null) {
  if (title) return title
  try { return new URL(url).hostname.replace(/^www\./, '') }
  catch { return '' }
}

function daysSince(dateStr: string) {
  return Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000)
}

function relativeTime(dateStr: string) {
  const d = daysSince(dateStr)
  if (d === 0) return 'today'
  if (d === 1) return '1d ago'
  return `${d}d ago`
}

onMounted(async () => {
  try {
    const [tagRes, itemsRes] = await Promise.all([
      apiFetch<Tag>(`/tags/${tagId}`),
      apiFetch<Item[]>(`/tags/${tagId}/items`),
    ])
    tag.value = tagRes
    items.value = itemsRes
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <main class="shell">
    <div v-if="loading" class="loading-state">載入中...</div>

    <div v-else-if="error" class="tg-error">
      <p>無法載入標籤內容</p>
      <NuxtLink to="/app" class="btn btn--ghost">← 返回首頁</NuxtLink>
    </div>

    <template v-else-if="tag">
      <header class="tg-header fadeup">
        <NuxtLink to="/app" class="tg-back mono">← 返回</NuxtLink>
        <div class="tg-header__title">
          <span class="tg-dot" style="background:var(--tag-a)"></span>
          <h1 class="tg-name">{{ localize(tag.name_i18n, tag.name) }}</h1>
          <span class="tg-count mono">{{ items.length }} 個項目</span>
        </div>
      </header>

      <div v-if="items.length === 0" class="tg-empty">
        <p class="mono">這個標籤還沒有項目</p>
      </div>

      <div v-else class="tg-grid fadeup">
        <NuxtLink
          v-for="item in items"
          :key="item.id"
          class="card"
          :to="`/app/item/${item.id}`"
        >
          <div class="card__thumb">
            <img v-if="item.thumbnail_url" :src="item.thumbnail_url" class="card__img" alt="" />
            <div v-else class="placeholder placeholder--a">
              <div class="placeholder__stripes"></div>
            </div>
            <span class="source-badge">{{ sourceLabel(item.url) }}</span>
          </div>
          <div class="card__body">
            <h3 class="card__title">{{ cardTitle(item.url, item.title) }}</h3>
            <div class="card__footer">
              <span class="mono">{{ relativeTime(item.saved_at) }}</span>
              <span v-if="!item.parsed_at" class="processing-badge">AI 處理中</span>
              <span v-else class="tag-chip tag-chip--a">{{ localize(tag.name_i18n, tag.name) }}</span>
            </div>
          </div>
        </NuxtLink>
      </div>
    </template>
  </main>
</template>
