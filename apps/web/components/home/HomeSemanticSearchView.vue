<script setup lang="ts">
import type { Item } from '~/types/api'

const { searchSemantic } = useSearch()
const itemStore = useItemStore()
const { open: openItemModal } = useItemModal()
const { t } = useI18n()

const query = ref('')
const results = ref<Item[]>([])
const loading = ref(false)
const loadingMore = ref(false)
const hasSearched = ref(false)
const hasNext = ref(false)
const isProGated = ref(false)
const page = ref(1)
const currentQuery = ref('')
const sentinelRef = ref<HTMLElement | null>(null)

const topTags = computed(() => {
  const counts = new Map<string, { name: string; count: number }>()
  for (const item of itemStore.items) {
    for (const tag of item.tags ?? []) {
      if (!counts.has(tag.id)) counts.set(tag.id, { name: tag.name, count: 0 })
      counts.get(tag.id)!.count++
    }
  }
  return [...counts.values()]
    .sort((a, b) => b.count - a.count)
    .slice(0, 3)
})

async function submit() {
  const q = query.value.trim()
  if (!q || loading.value) return
  loading.value = true
  isProGated.value = false
  hasSearched.value = false
  results.value = []
  hasNext.value = false
  page.value = 1
  currentQuery.value = q
  try {
    const res = await searchSemantic(q, 1)
    results.value = res.items
    hasNext.value = res.has_next
    hasSearched.value = true
  } catch (err: any) {
    if (err?.response?.status === 403) {
      isProGated.value = true
    }
  } finally {
    loading.value = false
  }
}

async function loadMore() {
  if (!hasNext.value || loadingMore.value || loading.value) return
  loadingMore.value = true
  page.value++
  try {
    const res = await searchSemantic(currentQuery.value, page.value)
    results.value.push(...res.items)
    hasNext.value = res.has_next
  } catch {
    page.value--
  } finally {
    loadingMore.value = false
  }
}

let observer: IntersectionObserver | null = null

watch(sentinelRef, (el) => {
  observer?.disconnect()
  if (!el) return
  observer = new IntersectionObserver(
    ([entry]) => { if (entry.isIntersecting) loadMore() },
    { rootMargin: '200px' },
  )
  observer.observe(el)
})

onUnmounted(() => observer?.disconnect())

function applyChip(tagName: string) {
  query.value = t('home.semantic_chip_query', { tag: tagName })
  submit()
}

function sourceLabel(url: string) {
  if (/youtu/.test(url)) return t('home.source_youtube')
  if (/instagram\.com/.test(url)) return t('home.source_ig')
  return t('home.source_article')
}

function excerpt(summary: string | null) {
  if (!summary) return ''
  return summary.length > 120 ? summary.slice(0, 120) + '...' : summary
}

function cardTitle(url: string, title: string | null) {
  if (title) return title
  try { return new URL(url).hostname.replace(/^www\./, '') } catch { return '' }
}
</script>

<template>
  <div class="semantic-view">
    <!-- Search box -->
    <div class="semantic-search-area">
      <p v-if="!hasSearched && !isProGated && !loading" class="semantic-desc">
        {{ t('home.semantic_desc') }}
      </p>
      <div class="semantic-input-row">
        <input
          v-model="query"
          class="semantic-input"
          :placeholder="t('home.semantic_placeholder')"
          :disabled="loading"
          @keydown.enter="submit"
        />
        <button class="btn btn--accent" :disabled="loading || !query.trim()" @click="submit">
          {{ loading ? t('home.semantic_searching') : t('home.semantic_search_btn') }}
        </button>
      </div>
      <!-- Suggestion chips — only before first search -->
      <div v-if="!hasSearched && !isProGated && !loading && topTags.length" class="semantic-chips-row">
        <span class="semantic-chips-label">{{ t('home.semantic_try') }}</span>
        <button
          v-for="tag in topTags"
          :key="tag.name"
          class="semantic-chip"
          @click="applyChip(tag.name)"
        >{{ t('home.semantic_chip', { tag: tag.name }) }}</button>
      </div>
    </div>

    <!-- Loading (initial search) -->
    <div v-if="loading" class="semantic-state">
      <span class="semantic-spinner"></span>
      {{ t('home.semantic_searching') }}
    </div>

    <!-- Pro gate -->
    <div v-else-if="isProGated" class="semantic-gate">
      <div class="semantic-gate__icon">★</div>
      <div class="semantic-gate__body">
        <p class="semantic-gate__title">{{ t('home.semantic_pro_title') }}</p>
        <p class="semantic-gate__desc">{{ t('home.semantic_pro_desc') }}</p>
        <NuxtLink to="/pricing" class="btn btn--accent semantic-gate__btn">
          {{ t('home.semantic_pro_btn') }}
        </NuxtLink>
      </div>
    </div>

    <!-- Results -->
    <template v-else-if="hasSearched">
      <p class="semantic-results-summary">
        {{ t('home.semantic_results', { n: results.length }) }}
      </p>
      <div v-if="results.length === 0" class="semantic-empty">
        {{ t('home.semantic_empty') }}
      </div>
      <div v-else class="semantic-list">
        <button
          v-for="item in results"
          :key="item.id"
          class="semantic-card"
          @click="openItemModal(item.id)"
        >
          <div class="semantic-card__thumb">
            <img v-if="item.thumbnail_url" :src="item.thumbnail_url" alt="" />
            <div v-else class="placeholder placeholder--b">
              <div class="placeholder__stripes"></div>
            </div>
          </div>
          <div class="semantic-card__body">
            <p class="semantic-card__title">{{ cardTitle(item.url, item.title) }}</p>
            <p v-if="excerpt(item.notes_md)" class="semantic-card__excerpt">
              {{ excerpt(item.notes_md) }}
            </p>
            <div class="semantic-card__meta">
              <span class="source-badge source-badge--sm">{{ sourceLabel(item.url) }}</span>
            </div>
          </div>
        </button>
      </div>

      <!-- Infinite scroll sentinel -->
      <div v-if="hasNext || loadingMore" ref="sentinelRef" class="semantic-load-more">
        <span v-if="loadingMore" class="semantic-spinner"></span>
      </div>
    </template>
  </div>
</template>
