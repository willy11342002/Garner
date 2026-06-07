<script setup lang="ts">
import type { Item, Tag } from '~/types/api'

const props = defineProps<{
  itemTagsMap: Record<string, Tag[]>
}>()

const emit = defineEmits<{
  'open-share': [tagId: string]
}>()

const itemStore = useItemStore()
const { localize } = useI18nContent()
const { open: openItemModal } = useItemModal()
const { pendingItemIds } = usePendingItems()
const { t } = useI18n()

const processingHover = ref<string | null>(null)
const selectedTagIds = ref(new Set<string>())

// Drag-to-scroll for desktop
const chipsRef = ref<HTMLElement | null>(null)
let dragState: { startX: number; scrollLeft: number } | null = null
let didDrag = false

function onChipsMouseDown(e: MouseEvent) {
  if (!chipsRef.value) return
  dragState = { startX: e.pageX - chipsRef.value.offsetLeft, scrollLeft: chipsRef.value.scrollLeft }
  didDrag = false
  chipsRef.value.style.cursor = 'grabbing'
}

function onChipsMouseMove(e: MouseEvent) {
  if (!dragState || !chipsRef.value) return
  e.preventDefault()
  const x = e.pageX - chipsRef.value.offsetLeft
  const delta = x - dragState.startX
  if (Math.abs(delta) > 4) didDrag = true
  chipsRef.value.scrollLeft = dragState.scrollLeft - delta
}

function onChipsMouseUp() {
  if (!chipsRef.value) return
  dragState = null
  chipsRef.value.style.cursor = ''
}

function onChipClick(e: MouseEvent, action: () => void) {
  if (didDrag) { e.preventDefault(); e.stopPropagation(); didDrag = false; return }
  action()
}
const filterLogic = ref<'and' | 'or'>('and')
const timeFilter = ref<'all' | '7d' | '30d' | 'year'>('all')
const sortOrder = ref<'saved_desc' | 'saved_asc'>('saved_desc')

const TAG_COLORS = ['a', 'b', 'c', 'd', 'e'] as const
function tagColor(i: number) {
  return TAG_COLORS[i % TAG_COLORS.length]
}

function cardTitle(url: string, title: string | null) {
  if (title) return title
  try { return new URL(url).hostname.replace(/^www\./, '') }
  catch { return '' }
}

function sourceLabel(url: string) {
  if (/youtu/.test(url)) return t('home.source_youtube')
  if (/instagram\.com/.test(url)) return t('home.source_ig')
  return t('home.source_article')
}

function relativeTime(dateStr: string) {
  const d = Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000)
  if (d === 0) return t('home.time_today')
  if (d === 1) return t('home.time_1d')
  return t('home.time_nd', { n: d })
}

// All tags sorted by count
const allTagGroups = computed(() => {
  const groups = new Map<string, { tag: Tag; count: number }>()
  for (const item of itemStore.items) {
    if (!item.parsed_at || pendingItemIds.value.has(item.id)) continue
    for (const tag of props.itemTagsMap[item.id] ?? []) {
      if (!groups.has(tag.id)) groups.set(tag.id, { tag, count: 0 })
      groups.get(tag.id)!.count++
    }
  }
  return [...groups.values()].sort((a, b) => b.count - a.count)
})

// Color index map (stable across strip and cards)
const tagColorIndex = computed(() => {
  const map = new Map<string, number>()
  allTagGroups.value.forEach((g, i) => map.set(g.tag.id, i))
  return map
})
function getTagColor(tagId: string) {
  return tagColor(tagColorIndex.value.get(tagId) ?? 0)
}

// Active chips first, then inactive
const orderedTagGroups = computed(() => {
  const active = allTagGroups.value.filter(g => selectedTagIds.value.has(g.tag.id))
  const inactive = allTagGroups.value.filter(g => !selectedTagIds.value.has(g.tag.id))
  return [...active, ...inactive]
})

function toggleTag(tagId: string) {
  const next = new Set(selectedTagIds.value)
  if (next.has(tagId)) next.delete(tagId)
  else next.add(tagId)
  selectedTagIds.value = next
  currentPage.value = 1
}

function removeTag(tagId: string) {
  const next = new Set(selectedTagIds.value)
  next.delete(tagId)
  selectedTagIds.value = next
  currentPage.value = 1
}

function clearFilters() {
  selectedTagIds.value = new Set()
  timeFilter.value = 'all'
  currentPage.value = 1
}

const hasActiveFilters = computed(() =>
  selectedTagIds.value.size > 0 || timeFilter.value !== 'all'
)

function getTimeFilterDate(): Date | null {
  const now = new Date()
  if (timeFilter.value === '7d') return new Date(now.getTime() - 7 * 86400000)
  if (timeFilter.value === '30d') return new Date(now.getTime() - 30 * 86400000)
  if (timeFilter.value === 'year') return new Date(now.getFullYear(), 0, 1)
  return null
}

// Reactive filtering — no search button needed
const filteredItems = computed(() => {
  const since = getTimeFilterDate()
  let items = itemStore.items.filter(i => {
    if (!i.parsed_at || pendingItemIds.value.has(i.id)) return false
    if (since && new Date(i.saved_at) < since) return false
    return true
  })
  if (selectedTagIds.value.size > 0) {
    if (filterLogic.value === 'and') {
      items = items.filter(item => {
        const tags = new Set((props.itemTagsMap[item.id] ?? []).map(t => t.id))
        return [...selectedTagIds.value].every(id => tags.has(id))
      })
    } else {
      items = items.filter(item => {
        const tags = new Set((props.itemTagsMap[item.id] ?? []).map(t => t.id))
        return [...selectedTagIds.value].some(id => tags.has(id))
      })
    }
  }
  return items
})

// Sort is also reactive
const allDisplayItems = computed(() => {
  return [...filteredItems.value].sort((a, b) => {
    const diff = new Date(b.saved_at).getTime() - new Date(a.saved_at).getTime()
    return sortOrder.value === 'saved_desc' ? diff : -diff
  })
})

const PAGE_SIZE = 30
const currentPage = ref(1)
const totalPages = computed(() => Math.ceil(allDisplayItems.value.length / PAGE_SIZE))
const displayItems = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE
  return allDisplayItems.value.slice(start, start + PAGE_SIZE)
})

// Reset page on filter changes
watch([timeFilter, filterLogic], () => { currentPage.value = 1 })

// Dropdown display labels (reactive to locale)
const timeLabel = computed(() => ({
  all: t('home.time_all'),
  '7d': t('home.time_7d'),
  '30d': t('home.time_30d'),
  year: t('home.time_year'),
})[timeFilter.value] ?? t('home.time_all'))

const sortLabel = computed(() => ({
  saved_desc: t('home.sort_newest'),
  saved_asc: t('home.sort_oldest'),
})[sortOrder.value] ?? t('home.sort_newest'))

// Filter summary text (e.g. "AI + 設計 · 近 30 天")
const filterSummary = computed(() => {
  const parts: string[] = []
  if (selectedTagIds.value.size > 0) {
    const names = [...selectedTagIds.value]
      .map(id => {
        const g = allTagGroups.value.find(g => g.tag.id === id)
        return g ? localize(g.tag.name_i18n, g.tag.name) : ''
      })
      .filter(Boolean)
    if (names.length) parts.push(names.join(' + '))
  }
  if (timeFilter.value !== 'all') {
    parts.push(timeLabel.value)
  }
  return parts.join(' · ')
})
</script>

<template>
  <div class="tag-view">

    <!-- Filter Row -->
    <div class="filter-row">
      <span class="filter-row__label">{{ t('home.filter_label') }}</span>

      <div
        ref="chipsRef"
        class="filter-chips"
        @mousedown="onChipsMouseDown"
        @mousemove="onChipsMouseMove"
        @mouseup="onChipsMouseUp"
        @mouseleave="onChipsMouseUp"
      >
        <button
          v-for="(group) in orderedTagGroups"
          :key="group.tag.id"
          class="tag-filter-chip"
          :class="{ 'tag-filter-chip--active': selectedTagIds.has(group.tag.id) }"
          @click="onChipClick($event, () => toggleTag(group.tag.id))"
        >
          <span
            class="tag-filter-chip__dot"
            :style="`background:var(--tag-${tagColor(tagColorIndex.get(group.tag.id) ?? 0)})`"
          ></span>
          {{ localize(group.tag.name_i18n, group.tag.name) }}
          <span class="tag-filter-chip__count">{{ group.count }}</span>
          <span
            v-if="selectedTagIds.has(group.tag.id)"
            class="tag-filter-chip__remove"
            @click.stop="onChipClick($event, () => removeTag(group.tag.id))"
          >×</span>
        </button>
      </div>

      <button v-if="hasActiveFilters" class="filter-clear-btn" @click="clearFilters">
        {{ t('home.filter_clear') }}
      </button>
      <div class="filter-row__divider"></div>
      <div class="filter-andor">
        <span class="filter-andor__label">{{ t('home.filter_match') }}</span>
        <button
          class="filter-andor__opt"
          :class="{ 'filter-andor__opt--active': filterLogic === 'and' }"
          @click="filterLogic = 'and'"
        >{{ t('home.filter_all') }}</button>
        <button
          class="filter-andor__opt"
          :class="{ 'filter-andor__opt--active': filterLogic === 'or' }"
          @click="filterLogic = 'or'"
        >{{ t('home.filter_any') }}</button>
      </div>
    </div>

    <!-- Results Row -->
    <div class="results-row">
      <p class="results-row__summary">
        {{ t('home.results', { n: allDisplayItems.length }) }}
        <span v-if="filterSummary" class="results-row__filter-desc">{{ filterSummary }}</span>
      </p>
      <div class="results-row__controls">
        <div class="filter-dropdown">
          <span class="filter-dropdown__label">{{ t('home.time_label') }}</span>
          <span class="filter-dropdown__val">{{ timeLabel }}</span>
          <select v-model="timeFilter">
            <option value="all">{{ t('home.time_all') }}</option>
            <option value="7d">{{ t('home.time_7d') }}</option>
            <option value="30d">{{ t('home.time_30d') }}</option>
            <option value="year">{{ t('home.time_year') }}</option>
          </select>
        </div>
        <div class="filter-dropdown">
          <span class="filter-dropdown__label">{{ t('home.sort_label') }}</span>
          <span class="filter-dropdown__val">{{ sortLabel }}</span>
          <select v-model="sortOrder">
            <option value="saved_desc">{{ t('home.sort_newest') }}</option>
            <option value="saved_asc">{{ t('home.sort_oldest') }}</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Card Grid -->
    <div class="card-grid">
      <a
        v-for="item in displayItems"
        :key="item.id"
        class="card"
        :href="`/app/item/${item.id}`"
        @click.prevent="openItemModal(item.id)"
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
            <span
              v-if="!item.parsed_at"
              class="processing-badge"
              @mouseenter="processingHover = item.id"
              @mouseleave="processingHover = null"
            >
              AI 處理中
              <ProcessingStatus
                v-if="processingHover === item.id"
                :item-id="item.id"
                :source-type="item.source_type"
                class="processing-badge__panel"
              />
            </span>
            <div v-else class="card__tags">
              <span
                v-for="tag in (itemTagsMap[item.id] ?? []).slice(0, 2)"
                :key="tag.id"
                :class="`tag-chip tag-chip--${getTagColor(tag.id)}`"
              >{{ localize(tag.name_i18n, tag.name) }}</span>
            </div>
          </div>
        </div>
      </a>
      <div v-if="displayItems.length === 0" class="card-grid__empty">
        {{ t('home.no_results') }}
      </div>
    </div>

    <!-- Pagination -->
    <div class="pagination">
      <button
        class="pagination__btn"
        :disabled="currentPage === 1"
        @click="currentPage--"
      >←</button>
      <span class="pagination__info mono">{{ currentPage }} / {{ totalPages }}</span>
      <button
        class="pagination__btn"
        :disabled="currentPage === totalPages"
        @click="currentPage++"
      >→</button>
    </div>
  </div>
</template>
