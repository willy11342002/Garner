<script setup lang="ts">
import type { Tag } from '~/types/api'

const emit = defineEmits<{
  'open-share': [tagId: string]
}>()

const apiFetch = useApiFetch()
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

// Tags from API (for chip bar counts)
const tags = ref<Tag[]>([])

// All tags sorted by count, derived from API tags list
const allTagGroups = computed(() =>
  tags.value
    .filter(t => t.item_count > 0)
    .map(tag => ({ tag, count: tag.item_count }))
    .sort((a, b) => b.count - a.count)
)

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
}

function removeTag(tagId: string) {
  const next = new Set(selectedTagIds.value)
  next.delete(tagId)
  selectedTagIds.value = next
}

function clearFilters() {
  selectedTagIds.value = new Set()
  timeFilter.value = 'all'
}

// Mobile tag select — pick one to add, then reset
function onMobileTagSelect(e: Event) {
  const id = (e.target as HTMLSelectElement).value
  if (id) toggleTag(id);
  (e.target as HTMLSelectElement).value = ''
}

const hasActiveFilters = computed(() =>
  selectedTagIds.value.size > 0 || timeFilter.value !== 'all'
)

function getSavedAfterParam(): string | undefined {
  const now = new Date()
  if (timeFilter.value === '7d') return new Date(now.getTime() - 7 * 86400000).toISOString()
  if (timeFilter.value === '30d') return new Date(now.getTime() - 30 * 86400000).toISOString()
  if (timeFilter.value === 'year') return new Date(now.getFullYear(), 0, 1).toISOString()
  return undefined
}

const PAGE_SIZE = 25
const currentPage = ref(1)
const totalPages = computed(() => Math.max(1, Math.ceil(itemStore.total / PAGE_SIZE)))

async function fetchItems(page = 1) {
  currentPage.value = page
  await itemStore.load({
    page,
    page_size: PAGE_SIZE,
    tag_ids: selectedTagIds.value.size > 0 ? [...selectedTagIds.value] : undefined,
    tag_logic: filterLogic.value,
    saved_after: getSavedAfterParam(),
    sort: sortOrder.value,
  })
}

// Items to display on current page (excluding pending-review and still-processing)
const displayItems = computed(() =>
  itemStore.items.filter(i => !!i.parsed_at && !pendingItemIds.value.has(i.id))
)

// Watchers: reset to page 1 on any filter change
watch([timeFilter, filterLogic, sortOrder], () => fetchItems(1))
watch(selectedTagIds, () => fetchItems(1))

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

onMounted(async () => {
  tags.value = await apiFetch<Tag[]>('/tags/')
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

      <!-- Mobile: single select + clear on same row -->
      <div class="filter-mobile-row">
        <select class="filter-tags-select" @change="onMobileTagSelect">
          <option value="">{{ t('home.filter_label') }}</option>
          <option
            v-for="group in allTagGroups"
            :key="group.tag.id"
            :value="group.tag.id"
          >{{ localize(group.tag.name_i18n, group.tag.name) }} ({{ group.count }})</option>
        </select>
        <button v-if="hasActiveFilters" class="filter-clear-btn" @click="clearFilters">
          {{ t('home.filter_clear') }}
        </button>
      </div>
      <!-- Mobile: selected tag chips -->
      <div v-if="selectedTagIds.size > 0" class="filter-mobile-chips">
        <button
          v-for="id in selectedTagIds"
          :key="id"
          class="tag-filter-chip tag-filter-chip--active"
          @click="removeTag(id)"
        >
          <span
            class="tag-filter-chip__dot"
            :style="`background:var(--tag-${tagColor(tagColorIndex.get(id) ?? 0)})`"
          ></span>
          {{ localize(allTagGroups.find(g => g.tag.id === id)?.tag.name_i18n ?? {}, allTagGroups.find(g => g.tag.id === id)?.tag.name ?? '') }}
          <span class="tag-filter-chip__remove">×</span>
        </button>
      </div>

      <button v-if="hasActiveFilters" class="filter-clear-btn filter-clear-btn--desktop" @click="clearFilters">
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
        {{ t('home.results', { n: itemStore.total }) }}
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
                v-for="tag in (item.tags ?? []).slice(0, 2)"
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
        @click="fetchItems(currentPage - 1)"
      >←</button>
      <span class="pagination__info mono">{{ currentPage }} / {{ totalPages }}</span>
      <button
        class="pagination__btn"
        :disabled="currentPage === totalPages"
        @click="fetchItems(currentPage + 1)"
      >→</button>
    </div>
  </div>
</template>
