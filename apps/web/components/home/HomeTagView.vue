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

const processingHover = ref<string | null>(null)
const TAG_STRIP_DEFAULT = 12
const showAllTags = ref(false)
const selectedTagIds = ref(new Set<string>())
const filterLogic = ref<'and' | 'or'>('and')
const searchResults = ref<Item[] | null>(null)

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
  if (/youtu/.test(url)) return '▶ YouTube'
  if (/instagram\.com/.test(url)) return 'IG'
  return 'Article'
}

function relativeTime(dateStr: string) {
  const d = Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000)
  if (d === 0) return 'today'
  if (d === 1) return '1d ago'
  return `${d}d ago`
}

// All tags sorted by item count, deduped
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

// Map tagId → color index (consistent across strip and cards)
const tagColorIndex = computed(() => {
  const map = new Map<string, number>()
  allTagGroups.value.forEach((g, i) => map.set(g.tag.id, i))
  return map
})

function getTagColor(tagId: string) {
  return tagColor(tagColorIndex.value.get(tagId) ?? 0)
}

const visibleTagGroups = computed(() =>
  showAllTags.value ? allTagGroups.value : allTagGroups.value.slice(0, TAG_STRIP_DEFAULT)
)

const hasMoreTags = computed(() => allTagGroups.value.length > TAG_STRIP_DEFAULT)

function toggleTag(tagId: string) {
  const next = new Set(selectedTagIds.value)
  if (next.has(tagId)) next.delete(tagId)
  else next.add(tagId)
  selectedTagIds.value = next
}

const PAGE_SIZE = 30
const currentPage = ref(1)

function doSearch() {
  currentPage.value = 1
  const parsed = itemStore.items.filter(i => !!i.parsed_at && !pendingItemIds.value.has(i.id))
  if (selectedTagIds.value.size === 0) {
    searchResults.value = parsed.slice().sort((a, b) => new Date(b.saved_at).getTime() - new Date(a.saved_at).getTime())
    return
  }
  if (filterLogic.value === 'and') {
    searchResults.value = parsed.filter(item => {
      const tags = new Set((props.itemTagsMap[item.id] ?? []).map(t => t.id))
      return [...selectedTagIds.value].every(id => tags.has(id))
    })
  } else {
    searchResults.value = parsed.filter(item => {
      const tags = new Set((props.itemTagsMap[item.id] ?? []).map(t => t.id))
      return [...selectedTagIds.value].some(id => tags.has(id))
    })
  }
}

// Default: parsed items excluding those still awaiting pending review
const defaultItems = computed(() =>
  itemStore.items
    .filter(i => !!i.parsed_at && !pendingItemIds.value.has(i.id))
    .slice()
    .sort((a, b) => new Date(b.saved_at).getTime() - new Date(a.saved_at).getTime())
)

const allDisplayItems = computed(() => searchResults.value ?? defaultItems.value)
const totalPages = computed(() => Math.ceil(allDisplayItems.value.length / PAGE_SIZE))
const displayItems = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE
  return allDisplayItems.value.slice(start, start + PAGE_SIZE)
})

</script>

<template>
  <div class="tag-view">
    <!-- Tag Strip -->
    <div class="tag-strip">
      <button
        v-for="(group, i) in visibleTagGroups"
        :key="group.tag.id"
        class="tag-filter-chip"
        :class="{ 'tag-filter-chip--active': selectedTagIds.has(group.tag.id) }"
        @click="toggleTag(group.tag.id)"
      >
        <span class="tag-filter-chip__dot" :style="`background:var(--tag-${tagColor(i)})`"></span>
        {{ localize(group.tag.name_i18n, group.tag.name) }}
        <span class="tag-filter-chip__count">{{ group.count }}</span>
      </button>
      <button
        v-if="hasMoreTags && !showAllTags"
        class="tag-strip__expand"
        @click="showAllTags = true"
      >還有 {{ allTagGroups.length - TAG_STRIP_DEFAULT }} 個標籤 ↓</button>
      <button
        v-else-if="showAllTags && hasMoreTags"
        class="tag-strip__expand"
        @click="showAllTags = false"
      >收起 ↑</button>
    </div>

    <!-- Filter Actions -->
    <div class="tag-filter-actions">
      <button
        class="tag-andor-toggle"
        :class="{ 'tag-andor-toggle--or': filterLogic === 'or' }"
        :title="filterLogic === 'and' ? '目前：全部符合。點擊切換為任一符合' : '目前：任一符合。點擊切換為全部符合'"
        @click="filterLogic = filterLogic === 'and' ? 'or' : 'and'"
      >{{ filterLogic === 'and' ? 'AND' : 'OR' }}</button>
      <button
        class="tag-search-btn"
        @click="doSearch"
      >搜尋</button>
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
        沒有符合條件的內容
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="pagination">
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
