<script setup lang="ts">
import type { Item, ItemPendingReview, Tag } from '~/types/api'

const itemStore = useItemStore()
const notifStore = useNotificationStore()
const { getItemTags, getPendingReview, confirmItemTag, detachTag, attachTag } = useItems()
const { localize, locale } = useI18nContent()
const { t } = useI18n()

const loading = ref(true)
const itemTagsMap = ref<Record<string, Tag[]>>({})

const pendingItems = ref<ItemPendingReview[]>([])
const selectedPendingIds = reactive(new Set<string>())
const tagDismissing = ref<Record<string, boolean>>({})
const confirmingSelected = ref(false)
const archivingSelected = ref(false)
const confirmingAll = ref(false)
const addingTagFor = ref<string | null>(null)
const newTagInput = ref('')
let newTagInputEl: HTMLInputElement | null = null
const openMenuId = ref<string | null>(null)

function closeMenu() { openMenuId.value = null }

async function startAddingTag(itemId: string) {
  addingTagFor.value = itemId
  newTagInput.value = ''
  await nextTick()
  newTagInputEl?.focus()
}
function toggleRowMenu(itemId: string, e: MouseEvent) {
  e.stopPropagation()
  openMenuId.value = openMenuId.value === itemId ? null : itemId
}

async function handleConfirmItem(item: ItemPendingReview) {
  openMenuId.value = null
  for (const tag of [...item.pending_tags]) {
    await confirmItemTag(item.id, tag.id)
  }
  // 樂觀更新：立刻把 pending tags 合進 tagMap，讓下方 tag 列即時出現
  const existing = itemTagsMap.value[item.id] ?? []
  const merged = [...existing, ...item.pending_tags.filter(pt => !existing.some(t => t.id === pt.id))]
  itemTagsMap.value = { ...itemTagsMap.value, [item.id]: merged }
  pendingItems.value = pendingItems.value.filter(i => i.id !== item.id)
  markNotifReadForItem(item.id)
  // 背景同步：用伺服器最新狀態覆蓋
  getItemTags(item.id).then(tags => { itemTagsMap.value = { ...itemTagsMap.value, [item.id]: tags } })
}

async function handleArchiveItem(item: ItemPendingReview) {
  openMenuId.value = null
  await itemStore.patch(item.id, { status: 'archived' })
  const idx = itemStore.items.findIndex(i => i.id === item.id)
  if (idx !== -1) itemStore.items.splice(idx, 1)
  pendingItems.value = pendingItems.value.filter(i => i.id !== item.id)
}

function markNotifReadForItem(itemId: string) {
  const ids = notifStore.items
    .filter(n => n.item_id === itemId && !n.is_read)
    .map(n => n.id)
  if (ids.length) notifStore.markRead(ids)
}

function pendingKey(itemId: string, tagId: string) {
  return `${itemId}:${tagId}`
}

function sourceEmoji(url: string) {
  if (/youtu/.test(url)) return '▶'
  if (/instagram\.com/.test(url)) return '◈'
  return '◎'
}

function sourceIconBg(url: string) {
  if (/youtu/.test(url)) return 'rgba(255,80,80,.18)'
  if (/instagram\.com/.test(url)) return 'rgba(200,60,180,.18)'
  return 'rgba(80,120,255,.18)'
}

function togglePendingItem(itemId: string, e: MouseEvent) {
  if ((e.target as HTMLElement).closest('button, input')) return
  if (selectedPendingIds.has(itemId)) selectedPendingIds.delete(itemId)
  else selectedPendingIds.add(itemId)
}

async function handleConfirmSelected() {
  confirmingSelected.value = true
  try {
    for (const itemId of [...selectedPendingIds]) {
      const item = pendingItems.value.find(i => i.id === itemId)
      if (!item) continue
      for (const tag of [...item.pending_tags]) {
        await confirmItemTag(item.id, tag.id)
      }
      // 樂觀更新
      const existing = itemTagsMap.value[item.id] ?? []
      const merged = [...existing, ...item.pending_tags.filter(pt => !existing.some(t => t.id === pt.id))]
      itemTagsMap.value = { ...itemTagsMap.value, [item.id]: merged }
      pendingItems.value = pendingItems.value.filter(i => i.id !== itemId)
      selectedPendingIds.delete(itemId)
      markNotifReadForItem(itemId)
      // 背景同步
      getItemTags(itemId).then(tags => { itemTagsMap.value = { ...itemTagsMap.value, [itemId]: tags } })
    }
  } finally {
    confirmingSelected.value = false
  }
}

async function handleConfirmAll() {
  confirmingAll.value = true
  try {
    for (const item of [...pendingItems.value]) {
      for (const tag of [...item.pending_tags]) {
        await confirmItemTag(item.id, tag.id)
      }
      const existing = itemTagsMap.value[item.id] ?? []
      const merged = [...existing, ...item.pending_tags.filter(pt => !existing.some(t => t.id === pt.id))]
      itemTagsMap.value = { ...itemTagsMap.value, [item.id]: merged }
      pendingItems.value = pendingItems.value.filter(i => i.id !== item.id)
      markNotifReadForItem(item.id)
      getItemTags(item.id).then(tags => { itemTagsMap.value = { ...itemTagsMap.value, [item.id]: tags } })
    }
    selectedPendingIds.clear()
  } finally {
    confirmingAll.value = false
  }
}

async function handleArchiveSelected() {
  archivingSelected.value = true
  try {
    for (const itemId of [...selectedPendingIds]) {
      await itemStore.patch(itemId, { status: 'archived' })
      const idx = itemStore.items.findIndex(i => i.id === itemId)
      if (idx !== -1) itemStore.items.splice(idx, 1)
      pendingItems.value = pendingItems.value.filter(i => i.id !== itemId)
      selectedPendingIds.delete(itemId)
    }
  } finally {
    archivingSelected.value = false
  }
}

async function handleDismissTag(item: ItemPendingReview, tagId: string) {
  const key = pendingKey(item.id, tagId)
  tagDismissing.value[key] = true
  try {
    await detachTag(item.id, tagId)
    item.pending_tags = item.pending_tags.filter(t => t.id !== tagId)
    if (item.pending_tags.length === 0) {
      pendingItems.value = pendingItems.value.filter(i => i.id !== item.id)
      selectedPendingIds.delete(item.id)
    }
  } finally {
    tagDismissing.value[key] = false
  }
}

async function handleAddTag(item: ItemPendingReview) {
  const name = newTagInput.value.trim()
  addingTagFor.value = null
  newTagInput.value = ''
  if (!name) return

  // 樂觀更新：先 push 一個暫時 id 讓 chip 立刻出現
  const tempId = `local-${name}-${Date.now()}`
  item.pending_tags.push({ id: tempId, name, name_i18n: null })

  // 送 API（pending=true → confirmed=false，跟 AI tag 一樣待確認）
  const tag = await attachTag(item.id, name, true)
  // 替換成真實 id，讓 × 能正確呼叫 detachTag
  if (tag?.id) {
    const idx = item.pending_tags.findIndex(t => t.id === tempId)
    if (idx !== -1) item.pending_tags[idx] = tag
  }
}

// URL quick-save (empty state CTA)
const newUrl = ref('')
const saving = ref(false)
const saveError = ref('')

// --- Spaced-Repetition Hero ---
const HERO_LS_KEY = 'vela_hero_seen'
const HERO_DATE_KEY = 'vela_hero_date'

function getSeenMap(): Record<string, number> {
  try { return JSON.parse(localStorage.getItem(HERO_LS_KEY) ?? '{}') } catch { return {} }
}

function markHeroSeen(itemId: string) {
  const map = getSeenMap()
  map[itemId] = Date.now()
  localStorage.setItem(HERO_LS_KEY, JSON.stringify(map))
  localStorage.setItem(HERO_DATE_KEY, new Date().toDateString())
}

function heroScore(item: Item): number {
  const age = (Date.now() - new Date(item.saved_at).getTime()) / 86400000
  // 峰值在收藏後第 14 天，sigma=10 的高斯曲線
  const ageFactor = Math.exp(-((age - 14) ** 2) / (2 * 100))
  const seenMap = getSeenMap()
  const lastSeenMs = seenMap[item.id]
  // 最近看過的降權：看過後 7 天內分數接近 0，之後線性恢復
  const recencyFactor = lastSeenMs
    ? Math.min(1, (Date.now() - lastSeenMs) / (7 * 86400000))
    : 1
  return ageFactor * recencyFactor
}

const heroItem = computed(() => {
  const candidates = itemStore.items.filter(i => !!i.parsed_at)
  if (!candidates.length) return null
  return candidates.reduce((best, cur) =>
    heroScore(cur) > heroScore(best) ? cur : best
  )
})

const heroDaysAgo = computed(() =>
  heroItem.value ? Math.round((Date.now() - new Date(heroItem.value.saved_at).getTime()) / 86400000) : 0
)

const heroTiptapDoc = computed(() => {
  const i18n = heroItem.value?.summary_i18n as Record<string, unknown> | null
  if (!i18n) return null
  const doc = i18n[locale.value] ?? i18n['zh-TW']
  if (doc && typeof doc === 'object' && (doc as any).type === 'doc') return doc as Record<string, unknown>
  return null
})

const heroEyebrow = computed(() => {
  const d = heroDaysAgo.value
  if (d === 0) return 'SAVED TODAY · REVISIT'
  if (d <= 3)  return `${d}D AGO · STILL FRESH`
  if (d <= 10) return `${d} DAYS AGO · REVISIT`
  if (d <= 30) return `${d} DAYS AGO · WORTH REVISITING`
  return `${d} DAYS AGO · REDISCOVER`
})

const heroTags = computed(() =>
  heroItem.value ? (itemTagsMap.value[heroItem.value.id] ?? []) : []
)

// 每次 heroItem 確定後記錄到 localStorage（每日只記一次）
watch(heroItem, (item) => {
  if (!item) return
  if (localStorage.getItem(HERO_DATE_KEY) === new Date().toDateString()) return
  markHeroSeen(item.id)
}, { immediate: false })

const heroPage = ref(0)
const HERO_TOTAL = 2
let heroTimer: ReturnType<typeof setInterval> | null = null

function startHeroTimer() {
  stopHeroTimer()
  heroTimer = setInterval(() => {
    if (weeklyTagGroups.value.length) heroPage.value = (heroPage.value + 1) % HERO_TOTAL
  }, 10000)
}
function stopHeroTimer() {
  if (heroTimer) { clearInterval(heroTimer); heroTimer = null }
}
function goHeroPage(page: number) {
  heroPage.value = page
  startHeroTimer()
}

function onHeroCardClick() {
  if (import.meta.client && window.innerWidth < 768 && heroItem.value)
    openItemModal(heroItem.value.id)
}

// Touch / mouse drag support for hero gallery
const dragStartX = ref<number | null>(null)

function onDragStart(e: MouseEvent | TouchEvent) {
  dragStartX.value = 'touches' in e ? e.touches[0].clientX : e.clientX
}
function onDragEnd(e: MouseEvent | TouchEvent) {
  if (dragStartX.value === null) return
  const endX = 'changedTouches' in e ? e.changedTouches[0].clientX : e.clientX
  const dx = endX - dragStartX.value
  dragStartX.value = null
  if (!weeklyTagGroups.value.length) return
  if (dx < -50 && heroPage.value < HERO_TOTAL - 1) goHeroPage(1)
  else if (dx > 50 && heroPage.value > 0) goHeroPage(0)
}

const weeklyTagGroups = computed(() => {
  if (loading.value) return []
  const weekAgo = Date.now() - 7 * 86400000
  const groups = new Map<string, { tag: Tag; count: number }>()
  for (const item of itemStore.items) {
    if (new Date(item.saved_at).getTime() < weekAgo) continue
    for (const tag of itemTagsMap.value[item.id] ?? []) {
      if (!groups.has(tag.id)) groups.set(tag.id, { tag, count: 0 })
      groups.get(tag.id)!.count++
    }
  }
  return [...groups.values()].sort((a, b) => b.count - a.count).slice(0, 4)
})

const totalWeeklyCount = computed(() =>
  weeklyTagGroups.value.reduce((s, g) => s + g.count, 0) || 1
)

const TAGROWS_PER_PAGE = 3
const visibleTagCount = ref(TAGROWS_PER_PAGE)

const tagGroups = computed(() => {
  const groups = new Map<string, { tag: Tag; items: Item[] }>()
  for (const item of itemStore.items) {
    if (!item.parsed_at) continue
    for (const tag of itemTagsMap.value[item.id] ?? []) {
      if (!groups.has(tag.id)) groups.set(tag.id, { tag, items: [] })
      groups.get(tag.id)!.items.push(item)
    }
  }
  // Sort: primary = item count desc, secondary = most recent saved_at desc
  return [...groups.values()].sort((a, b) => {
    if (b.items.length !== a.items.length) return b.items.length - a.items.length
    const latestA = Math.max(...a.items.map(i => new Date(i.saved_at).getTime()))
    const latestB = Math.max(...b.items.map(i => new Date(i.saved_at).getTime()))
    return latestB - latestA
  })
})

const visibleTagGroups = computed(() => tagGroups.value.slice(0, visibleTagCount.value))
const hasMoreTagGroups = computed(() => tagGroups.value.length > visibleTagCount.value)

const pendingItemIds = computed(() => new Set(pendingItems.value.map(i => i.id)))

const untaggedItems = computed(() =>
  itemStore.items.filter(item =>
    !!item.parsed_at &&
    (itemTagsMap.value[item.id] ?? []).length === 0 &&
    !pendingItemIds.value.has(item.id)
  )
)

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

function daysSince(dateStr: string) {
  return Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000)
}

function relativeTime(dateStr: string) {
  const d = daysSince(dateStr)
  if (d === 0) return 'today'
  if (d === 1) return '1d ago'
  return `${d}d ago`
}

async function quickSave() {
  const url = newUrl.value.trim()
  if (!url) return
  saving.value = true
  saveError.value = ''
  try {
    const item = await itemStore.add({ url })
    newUrl.value = ''
    itemTagsMap.value[item.id] = await getItemTags(item.id)
  } catch {
    saveError.value = '儲存失敗，請確認 URL 格式是否正確'
  } finally {
    saving.value = false
  }
}

watch(() => itemStore.recentlyProcessed, async (itemId) => {
  if (!itemId) return
  itemTagsMap.value[itemId] = await getItemTags(itemId)
  pendingItems.value = await getPendingReview()
})

onMounted(async () => {
  document.addEventListener('click', closeMenu)
  startHeroTimer()
  await itemStore.load()
  for (const item of itemStore.items) {
    itemTagsMap.value[item.id] = item.tags
  }
  pendingItems.value = await getPendingReview()
  loading.value = false
})

onUnmounted(() => {
  document.removeEventListener('click', closeMenu)
  stopHeroTimer()
})

// inline item detail modal
const { activeItemId, open: openItemModal } = useItemModal()

// modal 關閉後刷新該卡片的 tags 與 pending 狀態
watch(activeItemId, async (newId, oldId) => {
  if (!newId && oldId) {
    itemTagsMap.value[oldId] = await getItemTags(oldId)
    pendingItems.value = await getPendingReview()
  }
})

// share wizard modal
const shareModalOpen = ref(false)
const shareModalTagId = ref<string | undefined>(undefined)

function openShareModal(tagId: string) {
  shareModalTagId.value = tagId
  shareModalOpen.value = true
}
</script>

<template>
  <main class="shell">
    <!-- Loading -->
    <div v-if="loading" class="loading-state">載入中...</div>

    <!-- Empty: Ghost Preview + CTA -->
    <template v-else-if="itemStore.items.length === 0">
      <!-- Ghost Hero -->
      <section class="hero hero--empty fadeup">
        <div class="hero__media">
          <div class="placeholder placeholder--b">
            <div class="placeholder__stripes"></div>
          </div>
        </div>
        <div class="hero__body hero__cta">
          <span class="hero__eyebrow">WELCOME TO VELA</span>
          <h1 class="hero__title">你的知識庫還是空的</h1>
          <p class="hero__summary">存入第一筆內容，知識庫就會開始自動成長。</p>
          <div class="cta-input-row">
            <input
              v-model="newUrl"
              class="cta-input"
              placeholder="貼入任何 YouTube 或網頁 URL..."
              :disabled="saving"
              @keydown.enter="quickSave"
            />
            <button class="btn btn--accent" :disabled="saving" @click="quickSave">
              {{ saving ? '存入中...' : '存入' }}
            </button>
          </div>
          <p v-if="saveError" class="cta-error">{{ saveError }}</p>
          <div class="cta-divider"><span>或</span></div>
          <a href="#" class="btn cta-ext-btn">安裝 Chrome Extension →</a>
        </div>
      </section>

    </template>

    <!-- Populated -->
    <template v-else>
      <!-- Hero Gallery -->
      <div v-if="heroItem" class="hero-wrap fadeup">
        <div class="hero-gallery-wrap">
        <button
          v-if="heroPage === 1 && weeklyTagGroups.length"
          class="hero-nav hero-nav--prev"
          aria-label="上一頁"
          @click="goHeroPage(0)"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="10 3 5 8 10 13"/></svg>
        </button>
        <button
          v-if="heroPage === 0 && weeklyTagGroups.length"
          class="hero-nav hero-nav--next"
          aria-label="下一頁"
          @click="goHeroPage(1)"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 3 11 8 6 13"/></svg>
        </button>
        <div
          class="hero-gallery"
          :class="`hero-gallery--p${heroPage}`"
          @touchstart.passive="onDragStart"
          @touchend.passive="onDragEnd"
          @mousedown="onDragStart"
          @mouseup="onDragEnd"
        >
          <!-- Slide 0: TODAY'S REVISIT -->
          <section class="hero-slide hero" @click.stop="onHeroCardClick">
            <div class="hero__media">
              <img v-if="heroItem.thumbnail_url" :src="heroItem.thumbnail_url" class="hero__img" alt="" />
              <div v-else class="placeholder placeholder--b">
                <div class="placeholder__stripes"></div>
                <div class="placeholder__label">[ 縮圖處理中 ]</div>
              </div>
              <span class="source-badge hero__source">{{ sourceLabel(heroItem.url) }}</span>
            </div>
            <div class="hero__body">
              <span class="hero__eyebrow">{{ heroEyebrow }}</span>
              <h1 class="hero__title">{{ cardTitle(heroItem.url, heroItem.title) }}</h1>
              <div v-if="heroTags.length > 0" class="hero__chips">
                <span v-for="(tag, i) in heroTags" :key="tag.id" :class="`tag-chip tag-chip--${tagColor(i)}`">
                  {{ localize(tag.name_i18n, tag.name) }}
                </span>
              </div>
              <div class="hero__actions">
                <button class="btn btn--accent" @click="openItemModal(heroItem.id)">{{ t('home.open_read') }}</button>
              </div>
            </div>
          </section>

          <!-- Slide 1: 本週趨勢 -->
          <section class="hero-slide hero-slide--trend">
            <article class="insight insight--trend">
              <header class="insight__head">
                <span class="ins-badge ins-badge--a">{{ t('home.trend_badge') }}</span>
                <span class="insight__when">{{ t('home.trend_when') }}</span>
              </header>
              <h3 v-if="weeklyTagGroups.length" class="insight__title">
                {{ t('home.trend_top_tag', { tag: localize(weeklyTagGroups[0].tag.name_i18n, weeklyTagGroups[0].tag.name) }) }}
              </h3>
              <h3 v-else class="insight__title">{{ t('home.trend_empty') }}</h3>
              <div v-if="weeklyTagGroups.length" class="topic-bars">
                <div v-for="(g, i) in weeklyTagGroups" :key="g.tag.id" class="topic-bar">
                  <div
                    class="topic-bar__col"
                    :data-pct="Math.round(g.count / totalWeeklyCount * 100)"
                    :style="{ height: Math.max(16, g.count / totalWeeklyCount * 100) + '%', background: `var(--tag-${tagColor(i)})` }"
                  ></div>
                  <div class="topic-bar__label">{{ localize(g.tag.name_i18n, g.tag.name) }}</div>
                </div>
              </div>
              <div v-if="weeklyTagGroups.length" class="insight__foot">
                <span
                  v-for="(g, i) in weeklyTagGroups"
                  :key="g.tag.id"
                  :class="`tag-chip tag-chip--${tagColor(i)}`"
                >{{ localize(g.tag.name_i18n, g.tag.name) }}</span>
              </div>
            </article>
          </section>
        </div>
        </div>

        <!-- Gallery dots -->
        <div v-if="weeklyTagGroups.length" class="hero-dots">
          <button class="hero-dot" :class="{ 'hero-dot--active': heroPage === 0 }" @click="goHeroPage(0)"></button>
          <button class="hero-dot" :class="{ 'hero-dot--active': heroPage === 1 }" @click="goHeroPage(1)"></button>
        </div>
      </div>

      <!-- 新知識 pending list -->
      <section v-if="pendingItems.length > 0" class="pending-section fadeup">
        <header class="pending-section__head">
          <span class="pending-section__dot"></span>
          <span class="pending-section__count">{{ t('home.pending_count', { n: pendingItems.length }) }}</span>
          <button
            class="pending-section__confirm-all"
            :disabled="confirmingAll || confirmingSelected || archivingSelected"
            @click="handleConfirmAll"
          >{{ confirmingAll ? '確認中...' : '全部確認' }}</button>
        </header>

        <!-- Selbar -->
        <div v-if="selectedPendingIds.size > 0" class="selbar">
          <span class="selbar__count">已選 {{ selectedPendingIds.size }} 項</span>
          <div style="display:flex; gap:8px;">
            <button class="btn btn--ghost" :disabled="confirmingSelected || archivingSelected" @click="selectedPendingIds.clear()">取消</button>
            <button
              class="btn btn--accent"
              :disabled="confirmingSelected || archivingSelected"
              @click="handleConfirmSelected"
            >{{ confirmingSelected ? '確認中...' : '確認' }}</button>
            <button
              class="btn btn--danger"
              :disabled="confirmingSelected || archivingSelected"
              @click="handleArchiveSelected"
            >{{ archivingSelected ? '封存中...' : '封存' }}</button>
          </div>
        </div>

        <div class="pending-list">
          <div
            v-for="item in pendingItems"
            :key="item.id"
            class="pending-row"
            :class="{ 'pending-row--selected': selectedPendingIds.has(item.id) }"
            @click="togglePendingItem(item.id, $event)"
          >
            <span class="checkbox">
              <svg v-if="selectedPendingIds.has(item.id)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
            </span>
            <div class="pending-row__icon" :style="`background:${sourceIconBg(item.url)}`">
              {{ sourceEmoji(item.url) }}
            </div>
            <div class="pending-row__main">
              <div class="pending-row__title">{{ cardTitle(item.url, item.title) }}</div>
              <div class="pending-row__meta">
                <span class="source-badge source-badge--sm">{{ sourceLabel(item.url) }}</span>
                <span class="mono">{{ relativeTime(item.saved_at) }}</span>
              </div>
            </div>
            <div class="pending-row__tags">
              <div
                v-for="tag in item.pending_tags"
                :key="tag.id"
                class="pending-tag-chip"
                :class="{ 'pending-tag-chip--acting': tagDismissing[pendingKey(item.id, tag.id)] }"
              >
                <span>#{{ localize(tag.name_i18n, tag.name) }}</span>
                <button
                  :disabled="tagDismissing[pendingKey(item.id, tag.id)]"
                  @click.stop="handleDismissTag(item, tag.id)"
                >×</button>
              </div>
              <template v-if="addingTagFor === item.id">
                <input
                  :ref="(el) => { newTagInputEl = el as HTMLInputElement | null }"
                  v-model="newTagInput"
                  class="pending-tag-input"
                  placeholder="標籤名稱"
                  @keydown.enter.stop="handleAddTag(item)"
                  @keydown.esc.stop="addingTagFor = null; newTagInput = ''"
                  @blur="handleAddTag(item)"
                  @click.stop
                />
              </template>
              <button
                v-else
                class="pending-row__add"
                title="新增標籤"
                @click.stop="startAddingTag(item.id)"
              >+</button>
            </div>
            <div class="pending-row__menu-wrap" @click.stop>
              <button
                class="pending-row__more"
                :class="{ 'pending-row__more--open': openMenuId === item.id }"
                @click.stop="toggleRowMenu(item.id, $event)"
              >···</button>
              <div v-if="openMenuId === item.id" class="pending-row__dropdown">
                <button class="pending-row__drop-btn" @click.stop="handleConfirmItem(item)">確認</button>
                <button class="pending-row__drop-btn pending-row__drop-btn--danger" @click.stop="handleArchiveItem(item)">封存</button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Untagged -->
      <section v-if="untaggedItems.length > 0" class="tagrow">
        <header class="tagrow__head">
          <span class="tagrow__dot" style="background:var(--border2)"></span>
          <span class="tagrow__name">未分類</span>
          <span class="tagrow__count">{{ untaggedItems.length }}</span>
        </header>
        <div class="tagrow__scroll">
          <a
            v-for="item in untaggedItems.slice(0, 6)"
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
                <span v-if="!item.parsed_at" class="processing-badge">AI 處理中</span>
              </div>
            </div>
          </a>
        </div>
      </section>

      <!-- Tag rows -->
      <section v-for="(group, i) in visibleTagGroups" :key="group.tag.id" class="tagrow">
        <header class="tagrow__head">
          <span class="tagrow__dot" :style="`background:var(--tag-${tagColor(i)})`"></span>
          <span class="tagrow__name">{{ localize(group.tag.name_i18n, group.tag.name) }}</span>
          <span class="tagrow__count">{{ group.items.length }}</span>
          <button class="tagrow__share" @click="openShareModal(group.tag.id)">↗ 分享這個標籤</button>
          <NuxtLink :to="`/app/tag/${group.tag.id}`" class="tagrow__all">查看全部 →</NuxtLink>
        </header>
        <div class="tagrow__scroll">
          <a
            v-for="item in group.items.slice(0, 6)"
            :key="item.id"
            class="card"
            :href="`/app/item/${item.id}`"
            @click.prevent="openItemModal(item.id)"
          >
            <div class="card__thumb">
              <img v-if="item.thumbnail_url" :src="item.thumbnail_url" class="card__img" alt="" />
              <div v-else :class="`placeholder placeholder--${tagColor(i)}`">
                <div class="placeholder__stripes"></div>
              </div>
              <span class="source-badge">{{ sourceLabel(item.url) }}</span>
            </div>
            <div class="card__body">
              <h3 class="card__title">{{ cardTitle(item.url, item.title) }}</h3>
              <div class="card__footer">
                <span class="mono">{{ relativeTime(item.saved_at) }}</span>
                <span v-if="!item.parsed_at" class="processing-badge">AI 處理中</span>
                <span v-else :class="`tag-chip tag-chip--${tagColor(i)}`">{{ localize(group.tag.name_i18n, group.tag.name) }}</span>
              </div>
            </div>
          </a>
          <NuxtLink v-if="group.items.length > 6" :to="`/app/tag/${group.tag.id}`" class="card--more">查看更多 +{{ group.items.length - 6 }}</NuxtLink>
        </div>
      </section>

      <!-- Load more tag rows -->
      <div v-if="hasMoreTagGroups" class="tagrows-more">
        <button class="tagrows-more__btn mono" @click="visibleTagCount += TAGROWS_PER_PAGE">
          顯示更多標籤 · 還有 {{ tagGroups.length - visibleTagCount }} 組 ↓
        </button>
      </div>

    </template>
  </main>

  <ShareWizardModal
    :open="shareModalOpen"
    :preset-tag-id="shareModalTagId"
    @close="shareModalOpen = false"
  />
</template>
