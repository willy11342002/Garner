<script setup lang="ts">
import type { Item, ItemPendingReview, Tag } from '~/types/api'

const itemStore = useItemStore()
const { getItemTags, getPendingReview, confirmItemTag, detachTag, attachTag } = useItems()
const { localize } = useI18nContent()

const loading = ref(true)
const itemTagsMap = ref<Record<string, Tag[]>>({})

const pendingItems = ref<ItemPendingReview[]>([])
const pendingCollapsed = ref(false)
const selectedPendingIds = reactive(new Set<string>())
const tagDismissing = ref<Record<string, boolean>>({})
const confirmingSelected = ref(false)
const archivingSelected = ref(false)
const addingTagFor = ref<string | null>(null)
const newTagInput = ref('')
const openMenuId = ref<string | null>(null)

function closeMenu() { openMenuId.value = null }
function toggleRowMenu(itemId: string, e: MouseEvent) {
  e.stopPropagation()
  openMenuId.value = openMenuId.value === itemId ? null : itemId
}

async function handleConfirmItem(item: ItemPendingReview) {
  openMenuId.value = null
  for (const tag of [...item.pending_tags]) {
    await confirmItemTag(item.id, tag.id)
  }
  pendingItems.value = pendingItems.value.filter(i => i.id !== item.id)
  itemTagsMap.value[item.id] = await getItemTags(item.id)
}

async function handleArchiveItem(item: ItemPendingReview) {
  openMenuId.value = null
  await itemStore.patch(item.id, { status: 'archived' })
  const idx = itemStore.items.findIndex(i => i.id === item.id)
  if (idx !== -1) itemStore.items.splice(idx, 1)
  pendingItems.value = pendingItems.value.filter(i => i.id !== item.id)
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
      pendingItems.value = pendingItems.value.filter(i => i.id !== itemId)
      itemTagsMap.value[itemId] = await getItemTags(itemId)
      selectedPendingIds.delete(itemId)
    }
  } finally {
    confirmingSelected.value = false
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

const heroItem = computed(() => itemStore.items.find(i => !!i.parsed_at) ?? null)

const heroTags = computed(() =>
  heroItem.value ? (itemTagsMap.value[heroItem.value.id] ?? []) : []
)

const TAGROWS_PER_PAGE = 3
const visibleTagCount = ref(TAGROWS_PER_PAGE)

const tagGroups = computed(() => {
  const groups = new Map<string, { tag: Tag; items: Item[] }>()
  for (const item of itemStore.items) {
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
  await itemStore.load()
  const [, pending] = await Promise.all([
    Promise.all(
      itemStore.items.map(async item => {
        itemTagsMap.value[item.id] = await getItemTags(item.id)
      })
    ),
    getPendingReview(),
  ])
  pendingItems.value = pending
  loading.value = false
})

onUnmounted(() => {
  document.removeEventListener('click', closeMenu)
})
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
      <!-- Hero -->
      <section v-if="heroItem" class="hero fadeup">
        <div class="hero__media">
          <img v-if="heroItem.thumbnail_url" :src="heroItem.thumbnail_url" class="hero__img" alt="" />
          <div v-else class="placeholder placeholder--b">
            <div class="placeholder__stripes"></div>
            <div class="placeholder__label">[ 縮圖處理中 ]</div>
          </div>
          <div class="hero__mediaTag mono" style="color:var(--text-dim); font-size:10px; letter-spacing:.08em;">
            TODAY'S REVISIT · {{ daysSince(heroItem.saved_at) }} DAYS AGO
          </div>
          <span class="source-badge hero__source">{{ sourceLabel(heroItem.url) }}</span>
        </div>
        <div class="hero__body">
          <span class="hero__eyebrow">TODAY'S REVISIT</span>
          <h1 class="hero__title">{{ cardTitle(heroItem.url, heroItem.title) }}</h1>
          <p v-if="heroItem.summary || heroItem.summary_i18n" class="hero__summary">{{ localize(heroItem.summary_i18n, heroItem.summary) }}</p>
          <div v-if="heroTags.length > 0" class="hero__chips">
            <span
              v-for="(tag, i) in heroTags"
              :key="tag.id"
              :class="`tag-chip tag-chip--${tagColor(i)}`"
            >{{ localize(tag.name_i18n, tag.name) }}</span>
          </div>
          <div class="hero__actions">
            <NuxtLink :to="`/app/item/${heroItem.id}`" class="btn btn--accent">開啟閱讀 →</NuxtLink>
          </div>
        </div>
      </section>

      <!-- 新知識 pending list -->
      <section v-if="pendingItems.length > 0" class="pending-section fadeup">
        <header class="pending-section__head">
          <span class="pending-section__dot"></span>
          <span class="pending-section__count">{{ pendingItems.length }} 筆待整理</span>
          <button class="pending-section__toggle mono" @click="pendingCollapsed = !pendingCollapsed">
            {{ pendingCollapsed ? '展開 ↓' : '收起 ↑' }}
          </button>
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

        <div v-if="!pendingCollapsed" class="pending-list">
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
                  v-model="newTagInput"
                  class="pending-tag-input"
                  placeholder="標籤名稱"
                  autofocus
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
                @click.stop="addingTagFor = item.id; newTagInput = ''"
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
          <NuxtLink
            v-for="item in untaggedItems.slice(0, 6)"
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
              </div>
            </div>
          </NuxtLink>
        </div>
      </section>

      <!-- Tag rows -->
      <section v-for="(group, i) in visibleTagGroups" :key="group.tag.id" class="tagrow">
        <header class="tagrow__head">
          <span class="tagrow__dot" :style="`background:var(--tag-${tagColor(i)})`"></span>
          <span class="tagrow__name">{{ localize(group.tag.name_i18n, group.tag.name) }}</span>
          <span class="tagrow__count">{{ group.items.length }}</span>
          <NuxtLink to="/app/share" class="tagrow__share">↗ 分享這個標籤</NuxtLink>
          <NuxtLink :to="`/app/tag/${group.tag.id}`" class="tagrow__all">查看全部 →</NuxtLink>
        </header>
        <div class="tagrow__scroll">
          <NuxtLink
            v-for="item in group.items.slice(0, 6)"
            :key="item.id"
            class="card"
            :to="`/app/item/${item.id}`"
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
          </NuxtLink>
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
</template>
