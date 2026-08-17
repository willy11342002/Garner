<script setup lang="ts">
import type { Item, CollectionShareItem, Tag } from '~/types/api'
import { needsRetry } from '~/utils/itemStatus'

type AnyItem = Item | CollectionShareItem

const props = defineProps<{
  itemId?: string | null
  item?: AnyItem | null
  page?: boolean
  startInEdit?: boolean
}>()
const emit = defineEmits<{ close: []; archived: [] }>()

const isOpen = computed(() => !!(props.itemId || props.item))
const readonly = computed(() => !props.itemId)

const { t } = useI18n()
const { getItem, getItemTags, attachTag, detachTag, updateItem } = useItems()
const { updateArticle } = useArticles()
const { isBroken, markBroken } = useImageFallback()

const fetchedItem = ref<Item | null>(null)
const tags = ref<Tag[]>([])
const loading = ref(false)
const error = ref(false)

const item = computed(() => readonly.value ? props.item ?? null : fetchedItem.value)

// ── Tab / 地圖 ────────────────────────────────────────────────────────────────
// 地圖分頁的所有邏輯（地點載入、marker、搜尋 pin、geocoding 輪詢）在
// composables/useItemMap.ts。activeTab 由這裡持有並傳進去，因為切分頁牽涉
// gmap 的 claim / release，兩邊要看同一個 ref。
const activeTab = ref<'info' | 'map'>('info')
const {
  mapSlotEl, itemLocations, loadingLocations, extractingLocations,
  searchQuery, searchLoading, searchHint, savingNewLoc,
  selectedLoc, placeData, placeLoading, placeError,
  showExtractConfirm, extractQuotaError,
  switchToMapTab, switchToInfoTab,
  selectLocation, clearSelectedLoc, deleteLocation,
  requestExtractLocations, extractLocations,
  onSearchInput, clearSearch, resetForItem, leaveMapTab,
} = useItemMap(toRef(props, 'itemId'), activeTab)

// ── Swipe-down-to-close (mobile) ─────────────────────────────────────────────
// 手勢邏輯抽到 composables/useSwipeToClose.ts，與 pages/app/trips.vue 共用。
const overlayRef = ref<HTMLElement | null>(null)
const {
  panelRef,
  onTouchStart: onPanelTouchStart,
  onTouchMove: onPanelTouchMove,
  onTouchEnd: onPanelTouchEnd,
} = useSwipeToClose(() => doClose())


// ── Tags ──────────────────────────────────────────────────────────────────────
const addingTag = ref(false)
const newTagInput = ref('')
const tagRemoving = ref<Record<string, boolean>>({})
const tagAdding = ref(false)
const tagInputRef = ref<HTMLInputElement | null>(null)

// ── Inline title editing ─────────────────────────────────────────────────────
// 進入 / 儲存由 startEditNotes() / saveNotes() 一併處理（標題與筆記同一個編輯流程），
// 這裡只留狀態與取消。
const isEditingTitle = ref(false)
const editingTitle = ref('')
const titleInputRef = ref<HTMLInputElement | null>(null)

function cancelEditTitle() {
  isEditingTitle.value = false
  editingTitle.value = ''
}

// ── Inline note editing（狀態宣告在此，因為下面的輪詢要讀 isEditingNotes）──────
const isEditingNotes = ref(false)
const editingNotesMd = ref('')
// template 從以前就綁了 savingNotes（:disabled 與「儲存中」文案），但一直沒有宣告，
// 所以那顆按鈕的 disabled 永遠是 undefined、儲存中狀態從沒顯示過。補回來。
const savingNotes = ref(false)

// ── 輪詢（重新分析 / 初始分析）───────────────────────────────────────────────
// 實作在 composables/useItemPolling.ts。isEditingNotes 傳進去是為了讓輪詢在
// 使用者編輯筆記時不要覆蓋他打到一半的內容。
const {
  reanalyzing, showReanalyzeConfirm, reanalyzeQuotaError,
  requestReanalyze, reanalyze,
  pollAnalysis, stopAnalysisPoll,
  retrying, retryIngest,
} = useItemPolling(toRef(props, 'itemId'), fetchedItem, isEditingNotes)

// Item is still in its initial analysis (note stage not finished, no error).
const isAnalyzing = computed(() => {
  const it = item.value as Item | null
  if (!it || readonly.value) return false
  return !it.notes_md && it.note_status !== 'complete' && it.note_status !== 'error' && !it.parsed_at
})

// Stalled (no progress in 5+ min) or a stage exhausted its retries — either
// way the ingest pipeline needs a manual nudge via POST /items/{id}/resume.
const showRetry = computed(() => {
  const it = item.value as Item | null
  if (!it || readonly.value) return false
  return needsRetry(it)
})

// ── Inline note editing：操作（狀態宣告在上面輪詢區塊之前）────────────────────
function startEditNotes() {
  editingNotesMd.value = (item.value as Item)?.notes_md ?? ''
  isEditingNotes.value = true
  editingTitle.value = (item.value as Item)?.title ?? ''
  isEditingTitle.value = true
  nextTick(() => titleInputRef.value?.focus())
}

async function saveNotes() {
  if (!item.value) return
  const titleTrimmed = editingTitle.value.trim() || null
  const notesMd = editingNotesMd.value
  if (fetchedItem.value) fetchedItem.value = { ...fetchedItem.value, notes_md: notesMd, title: titleTrimmed }
  isEditingNotes.value = false
  isEditingTitle.value = false
  savingNotes.value = true
  try {
    await updateArticle(item.value.id, { notes_md: notesMd, title: titleTrimmed })
  } finally {
    savingNotes.value = false
  }
}

// ── Archive ───────────────────────────────────────────────────────────────────
const archiving = ref(false)
const showArchiveConfirm = ref(false)


function sourceLabel(url: string) {
  return SOURCE_DISPLAY_NAMES[sourceKindFromUrl(url)]
}



function relativeTime(dateStr: string) {
  const d = Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000)
  if (d === 0) return t('itemModal.today')
  if (d === 1) return t('itemModal.dayAgo')
  return t('itemModal.daysAgo', { n: d })
}

async function load(id: string) {
  loading.value = true
  error.value = false
  fetchedItem.value = null
  tags.value = []
  isEditingNotes.value = false
  stopAnalysisPoll()
  try {
    const [fi, ft] = await Promise.all([getItem(id), getItemTags(id)])
    fetchedItem.value = fi
    tags.value = ft
    if (props.startInEdit) startEditNotes()
    // Opened while still being analyzed → poll until the note stage finishes.
    if (!fi.notes_md && fi.note_status !== 'complete' && fi.note_status !== 'error') {
      pollAnalysis()
    }
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

const lockScroll = (lock: boolean) => {
  if (!import.meta.client || props.page) return
  document.body.style.overflow = lock ? 'hidden' : ''
}

watch(() => props.itemId, (id, prevId) => {
  resetForItem(prevId)   // 釋放前一筆的地圖擁有權、回到資訊分頁、清空地點

  if (id) {
    lockScroll(true)
    load(id)
  } else if (!props.item) {
    lockScroll(false)
    fetchedItem.value = null
    tags.value = []
  }
}, { immediate: true })

watch(() => props.item, (v) => {
  lockScroll(!!v)
}, { immediate: true })

onUnmounted(() => {
  // 地圖相關的清理（搜尋、geocoding 輪詢、gmap 釋放）由 useItemMap 自己的
  // onUnmounted 負責，這裡只處理元件自己的東西。
  lockScroll(false)
  stopAnalysisPoll()
})

function doClose() {
  leaveMapTab()
  showArchiveConfirm.value = false
  isEditingNotes.value = false
  editingNotesMd.value = ''
  isEditingTitle.value = false
  editingTitle.value = ''
  stopAnalysisPoll()
  emit('close')
}

// ── Tag handlers ──────────────────────────────────────────────────────────────
async function startAddingTag() {
  addingTag.value = true
  await nextTick()
  tagInputRef.value?.focus()
}

async function handleAddTag() {
  const name = newTagInput.value.trim()
  addingTag.value = false
  newTagInput.value = ''
  if (!name || !item.value) return
  tagAdding.value = true
  try {
    const tag = await attachTag(item.value.id, name)
    if (tag) tags.value.push(tag)
  } finally {
    tagAdding.value = false
  }
}

async function handleRemoveTag(tag: Tag) {
  if (!item.value) return
  tagRemoving.value[tag.id] = true
  try {
    await detachTag(item.value.id, tag.id)
    tags.value = tags.value.filter(t => t.id !== tag.id)
  } finally {
    const { [tag.id]: _done, ...rest } = tagRemoving.value
    tagRemoving.value = rest
  }
}

// ── Archive handlers ──────────────────────────────────────────────────────────
// 一律走 fetchedItem 而不是 item：封存只對自己擁有的 Item 有意義，
// readonly 模式下的 props.item 可能是 CollectionShareItem（沒有 status 欄位）。
// template 也已用 v-if="!readonly" 把這兩顆按鈕擋在唯讀模式外。
function requestArchive() {
  if (fetchedItem.value?.status === 'archived') confirmArchive()
  else showArchiveConfirm.value = true
}

async function confirmArchive() {
  const target = fetchedItem.value
  if (!target) return
  showArchiveConfirm.value = false
  archiving.value = true
  try {
    const isArchived = target.status === 'archived'
    await updateItem(target.id, { status: isArchived ? 'active' : 'archived' })
    fetchedItem.value = { ...target, status: isArchived ? 'active' : 'archived' }
    emit('archived')
  } finally {
    archiving.value = false
  }
}
</script>

<template>
  <Teleport to="body" :disabled="page">

    <!-- ── Modal mode ── -->
    <template v-if="!page">
      <div
        v-if="isOpen"
        ref="overlayRef"
        class="id-overlay"
        tabindex="-1"
        @click.self="doClose"
        @keydown.esc="doClose"
      >
        <div
          ref="panelRef"
          class="id-panel"
          @touchstart.passive="onPanelTouchStart"
          @touchmove.passive="onPanelTouchMove"
          @touchend.passive="onPanelTouchEnd"
        >
          <button class="id-close" @click="doClose">×</button>
          <div v-if="loading || error" class="id-spinner id-spinner--panel">
            {{ error ? t('itemModal.loadFailed') : t('itemModal.loading') }}
          </div>
          <template v-else-if="item">

          <div class="id-media">
            <img
              v-if="item.thumbnail_url && !isBroken(item.thumbnail_url)"
              :src="item.thumbnail_url"
              class="id-media__img"
              alt=""
              @error="markBroken(item.thumbnail_url)"
            >
            <div v-else class="placeholder placeholder--b id-media__ph">
              <div class="placeholder__stripes"/>
            </div>
            <a :href="item.url" target="_blank" rel="noopener" class="source-badge id-media__badge">{{ sourceLabel(item.url) }}</a>
          </div>

          <div class="id-body">
            <div v-if="(item as Item).saved_at" class="id-body__meta mono">{{ relativeTime((item as Item).saved_at) }}</div>
            <div class="id-body__header">
              <input
                v-if="isEditingTitle"
                ref="titleInputRef"
                v-model="editingTitle"
                class="id-body__title-input"
                @keydown.enter.prevent="() => {}"
                @keydown.esc.stop="cancelEditTitle"
              >
              <h1 v-else class="id-body__title">{{ cardTitle(item.url, item.title) }}</h1>
              <div class="id-body__actions">
                <button
                  v-if="!readonly && activeTab === 'info'"
                  class="btn btn--accent"
                  @click="isEditingNotes ? saveNotes() : startEditNotes()"
                >
                  {{ isEditingNotes ? t('itemModal.save') : t('itemModal.editNotes') }}
                </button>
                <button
                  v-if="!readonly && activeTab === 'info' && !isEditingNotes"
                  class="btn"
                  :disabled="reanalyzing || isAnalyzing"
                  @click="requestReanalyze"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>
                  </svg>
                  {{ (reanalyzing || isAnalyzing) ? t('itemModal.analyzing') : t('itemModal.reanalyze') }}
                </button>
                <button
                  v-if="!readonly && activeTab === 'map'"
                  class="btn btn--accent"
                  :disabled="extractingLocations"
                  @click="requestExtractLocations"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="10" r="3"/><path d="M12 2a8 8 0 0 0-8 8c0 5.25 8 14 8 14s8-8.75 8-14a8 8 0 0 0-8-8z"/>
                  </svg>
                  {{ extractingLocations ? t('itemModal.extracting') : t('itemModal.reExtractLandmarks') }}
                </button>
                <button v-if="!readonly" class="btn" :disabled="archiving" @click="requestArchive">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0">
                    <template v-if="(item as Item).status === 'archived'">
                      <path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>
                    </template>
                    <template v-else>
                      <rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/><line x1="12" y1="12" x2="12" y2="16"/><line x1="10" y1="14" x2="14" y2="14"/>
                    </template>
                  </svg>
                  {{ archiving ? t('itemModal.processing') : (item as Item).status === 'archived' ? t('itemModal.restore') : t('itemModal.archive') }}
                </button>
              </div>
            </div>

            <!-- Tab bar (only in private mode) -->
            <div v-if="!readonly" class="id-tabs">
              <button
                class="id-tab"
                :class="{ 'id-tab--active': activeTab === 'info' }"
                @click="switchToInfoTab"
              >{{ t('itemModal.tabNotes') }}</button>
              <button
                class="id-tab"
                :class="{ 'id-tab--active': activeTab === 'map' }"
                @click="switchToMapTab"
              >{{ t('itemModal.tabMap') }}</button>
            </div>

            <!-- Info tab: tags + notes -->
            <template v-if="activeTab === 'info'">
              <div class="id-body__tags">
                <span
                  v-for="(tag, i) in tags"
                  :key="tag.id"
                  :class="`tag-chip tag-chip--${tagColor(i)} id-tag`"
                  :style="tagRemoving[tag.id] ? 'opacity:0.4;pointer-events:none' : ''"
                >
                  {{ tag.name }}
                  <button class="id-tag__remove" @click="handleRemoveTag(tag)">×</button>
                </span>
                <template v-if="addingTag">
                  <input
                    ref="tagInputRef"
                    v-model="newTagInput"
                    class="id-tag__input"
                    :placeholder="t('itemModal.tagPlaceholder')"
                    @keydown.enter="handleAddTag"
                    @keydown.esc.stop="addingTag = false; newTagInput = ''"
                    @blur="handleAddTag"
                  >
                </template>
                <button v-else class="id-tag__add" :disabled="tagAdding" @click="startAddingTag">
                  {{ t('itemModal.addTag') }}
                </button>
              </div>

              <div class="id-body__summary">
                <TiptapEditor
                  v-if="isEditingNotes"
                  v-model="editingNotesMd"
                  :readonly="false"
                />
                <TiptapEditor
                  v-else-if="(item as Item).notes_md"
                  :model-value="(item as Item).notes_md"
                  :readonly="true"
                />
                <div
                  v-else-if="showRetry"
                  class="notes-analyzing notes-analyzing--err"
                >
                  <span>{{ t('itemModal.noteAnalyzeFailed') }}</span>
                  <button class="btn btn--accent" :disabled="retrying" @click="retryIngest">
                    {{ retrying ? t('itemModal.processing') : t('itemModal.retry') }}
                  </button>
                </div>
                <div
                  v-else-if="!readonly && !(item as Item).parsed_at"
                  class="notes-analyzing"
                >
                  <span class="notes-analyzing__spinner" />
                  <span class="notes-analyzing__text">{{ t('itemModal.noteAnalyzing') }}</span>
                </div>
                <p v-else class="id-body__summary-empty">{{ t('itemModal.noNotes') }}</p>
              </div>
            </template>

            <!-- Map tab -->
            <template v-else-if="activeTab === 'map'">
              <!-- Search box -->
              <div class="id-map-search">
                <div class="id-map-search__wrap">
                  <svg class="id-map-search__icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                  </svg>
                  <input
                    v-model="searchQuery"
                    type="text"
                    class="id-map-search__input"
                    :placeholder="t('itemModal.searchPlacePlaceholder')"
                    autocomplete="off"
                    :disabled="savingNewLoc"
                    @input="onSearchInput"
                    @keydown.enter.prevent="onSearchInput"
                    @keydown.esc="clearSearch"
                  >
                  <span v-if="searchLoading" class="id-map-search__saving">{{ t('itemModal.searching') }}</span>
                  <span v-else-if="savingNewLoc" class="id-map-search__saving">{{ t('itemModal.adding') }}</span>
                  <button v-else-if="searchQuery" class="id-map-search__clear" @click="clearSearch">×</button>
                </div>
                <div v-if="searchHint" class="id-map-search__hint">{{ searchHint }}</div>
              </div>

              <!-- Map container: global Leaflet instance gets appended here -->
              <div ref="mapSlotEl" class="id-map-slot" />

              <!-- Place info panel (shown when a marker is selected) -->
              <template v-if="selectedLoc">
                <div class="id-map-place-header">
                  <button class="id-map-place-back" @click="clearSelectedLoc">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg>
                    {{ t('itemModal.allLandmarks') }}
                  </button>
                  <span class="id-map-place-name">{{ selectedLoc.name }}</span>
                </div>
                <PlaceInfoPanel
                  :place-data="placeData"
                  :place-loading="placeLoading"
                  :place-error="placeError"
                  show-delete
                  @delete="deleteLocation(selectedLoc)"
                />
              </template>

              <!-- Locations list (default) -->
              <template v-else>
                <div class="id-map-locations">
                  <div v-if="loadingLocations" class="id-map-locations__loading">{{ t('itemModal.loadingLocations') }}</div>
                  <template v-else-if="itemLocations.length">
                    <div v-for="loc in itemLocations" :key="loc.id" class="id-map-loc" @click="selectLocation(loc)">
                      <svg class="id-map-loc__pin" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                        <circle cx="12" cy="10" r="3"/><path d="M12 2a8 8 0 0 0-8 8c0 5.25 8 14 8 14s8-8.75 8-14a8 8 0 0 0-8-8z"/>
                      </svg>
                      <span class="id-map-loc__name">{{ loc.name }}</span>
                      <span v-if="loc.geocoding_status === 'pending'" class="id-map-loc__nogeo id-map-loc__nogeo--pending">{{ t('itemModal.geocoding') }}</span>
                      <span v-else-if="loc.geocoding_status === 'failed'" class="id-map-loc__nogeo id-map-loc__nogeo--failed">{{ t('itemModal.geocodeFailed') }}</span>
                      <span class="id-map-loc__badge" :class="`id-map-loc__badge--${loc.source}`">
                        {{ loc.source === 'metadata' ? 'meta' : loc.source === 'user' ? t('itemModal.sourceManual') : 'AI' }}
                      </span>
                      <button class="id-map-loc__btn id-map-loc__btn--delete" @click.stop="deleteLocation(loc)">{{ t('itemModal.delete') }}</button>
                    </div>
                  </template>
                  <div v-else class="id-map-locations__empty">
                    <span>{{ t('itemModal.noLocations') }}</span>
                    <button
                      class="id-map-loc__btn id-map-loc__btn--extract"
                      :disabled="extractingLocations"
                      @click="requestExtractLocations"
                    >
                      {{ extractingLocations ? t('itemModal.extractingShort') : t('itemModal.supplementLandmarks') }}
                    </button>
                  </div>
                </div>
              </template>
            </template>

          </div>
          </template>
        </div>
      </div>
    </template>

    <!-- ── Page mode ── -->
    <template v-else>
      <div v-if="loading" class="idp-state">{{ t('itemModal.loading') }}</div>
      <div v-else-if="error" class="idp-state">{{ t('itemModal.loadFailed') }}</div>
      <div v-else-if="item" class="idp-wrap">
        <div class="idp-panel">
          <div class="idp-media">
            <img
              v-if="item.thumbnail_url && !isBroken(item.thumbnail_url)"
              :src="item.thumbnail_url"
              class="idp-media__img"
              alt=""
              @error="markBroken(item.thumbnail_url)"
            >
            <div v-else class="placeholder placeholder--b idp-media__ph">
              <div class="placeholder__stripes"/>
            </div>
            <span class="source-badge idp-media__badge">{{ sourceLabel(item.url) }}</span>
          </div>

          <div class="idp-body">
            <div v-if="(item as Item).saved_at" class="id-body__meta mono">{{ relativeTime((item as Item).saved_at) }}</div>
              <input
                v-if="isEditingTitle"
                ref="titleInputRef"
                v-model="editingTitle"
                class="id-body__title-input"
                @keydown.enter.prevent="() => {}"
                @keydown.esc.stop="cancelEditTitle"
              >
              <h1 v-else class="id-body__title">{{ cardTitle(item.url, item.title) }}</h1>

            <div v-if="!readonly" class="id-body__tags">
              <span
                v-for="(tag, i) in tags"
                :key="tag.id"
                :class="`tag-chip tag-chip--${tagColor(i)} id-tag`"
                :style="tagRemoving[tag.id] ? 'opacity:0.4;pointer-events:none' : ''"
              >
                {{ tag.name }}
                <button class="id-tag__remove" @click="handleRemoveTag(tag)">×</button>
              </span>
              <template v-if="addingTag">
                <input
                  ref="tagInputRef"
                  v-model="newTagInput"
                  class="id-tag__input"
                  :placeholder="t('itemModal.tagPlaceholder')"
                  @keydown.enter="handleAddTag"
                  @keydown.esc.stop="addingTag = false; newTagInput = ''"
                  @blur="handleAddTag"
                >
              </template>
              <button v-else class="id-tag__add" :disabled="tagAdding" @click="startAddingTag">
                {{ t('itemModal.addTag') }}
              </button>
            </div>

            <div class="id-body__summary">
              <TiptapEditor
                v-if="isEditingNotes"
                v-model="editingNotesMd"
                :readonly="false"
              />
              <TiptapEditor
                v-else-if="(item as Item).notes_md"
                :model-value="(item as Item).notes_md"
                :readonly="true"
              />
              <div
                v-else-if="!readonly && (item as Item).note_status === 'error'"
                class="notes-analyzing notes-analyzing--err"
              >
                {{ t('itemModal.noteAnalyzeFailed') }}
              </div>
              <div
                v-else-if="!readonly && !(item as Item).parsed_at"
                class="notes-analyzing"
              >
                <span class="notes-analyzing__spinner" />
                <span class="notes-analyzing__text">{{ t('itemModal.noteAnalyzing') }}</span>
              </div>
              <p v-else class="id-body__summary-empty">{{ t('itemModal.noNotes') }}</p>
            </div>

            <div class="id-body__actions">
              <button
                v-if="!readonly"
                class="btn btn--accent"
                :disabled="savingNotes"
                @click="isEditingNotes ? saveNotes() : startEditNotes()"
              >
                {{ isEditingNotes ? (savingNotes ? t('itemModal.saving') : t('itemModal.save')) : t('itemModal.editNotes') }}
              </button>
              <button v-if="!readonly" class="btn" :disabled="archiving" @click="requestArchive">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0">
                  <template v-if="(item as Item).status === 'archived'">
                    <path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>
                  </template>
                  <template v-else>
                    <rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/><line x1="12" y1="12" x2="12" y2="16"/><line x1="10" y1="14" x2="14" y2="14"/>
                  </template>
                </svg>
                {{ archiving ? t('itemModal.processing') : (item as Item).status === 'archived' ? t('itemModal.restore') : t('itemModal.archive') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Archive confirm（兩種模式共用） -->
    <div v-if="showArchiveConfirm" class="modal-mask" @click.self="showArchiveConfirm = false">
      <div class="modal">
        <h2>{{ t('itemModal.archiveConfirmTitle') }}</h2>
        <i18n-t keypath="itemModal.archiveConfirmBody" tag="p">
          <template #archive><b>{{ t('itemModal.archiveLink') }}</b></template>
        </i18n-t>
        <div class="modal__actions">
          <button class="btn btn--warn" style="flex:1;" :disabled="archiving" @click="confirmArchive">
            {{ archiving ? t('itemModal.processing') : t('itemModal.archive') }}
          </button>
          <button class="btn" :disabled="archiving" @click="showArchiveConfirm = false">{{ t('itemModal.cancel') }}</button>
        </div>
      </div>
    </div>

    <!-- Reanalyze confirm -->
    <div v-if="showReanalyzeConfirm" class="modal-mask" @click.self="!reanalyzing && (showReanalyzeConfirm = false)">
      <div class="modal">
        <h2>{{ t('itemModal.reanalyze') }}</h2>
        <i18n-t keypath="itemModal.reanalyzeConfirmBody" tag="p">
          <template #cost><b>{{ t('itemModal.quotaCost') }}</b></template>
        </i18n-t>
        <p v-if="reanalyzeQuotaError" style="color: var(--danger, #e55); font-size: 13px;">
          {{ t('itemModal.reanalyzeQuotaFull') }}
        </p>
        <div class="modal__actions">
          <button class="btn btn--accent" style="flex:1;" :disabled="reanalyzing" @click="reanalyze">
            {{ reanalyzing ? t('itemModal.processing') : t('itemModal.reanalyzeConfirmBtn') }}
          </button>
          <button class="btn" :disabled="reanalyzing" @click="showReanalyzeConfirm = false">{{ t('itemModal.cancel') }}</button>
        </div>
      </div>
    </div>

    <!-- Re-extract landmarks confirm -->
    <div v-if="showExtractConfirm" class="modal-mask" @click.self="!extractingLocations && (showExtractConfirm = false)">
      <div class="modal">
        <h2>{{ t('itemModal.reExtractLandmarks') }}</h2>
        <i18n-t keypath="itemModal.extractConfirmBody" tag="p">
          <template #cost><b>{{ t('itemModal.quotaCost') }}</b></template>
        </i18n-t>
        <p v-if="extractQuotaError" style="color: var(--danger, #e55); font-size: 13px;">
          {{ t('itemModal.extractQuotaFull') }}
        </p>
        <div class="modal__actions">
          <button class="btn btn--accent" style="flex:1;" :disabled="extractingLocations" @click="extractLocations">
            {{ extractingLocations ? t('itemModal.processing') : t('itemModal.extractConfirmBtn') }}
          </button>
          <button class="btn" :disabled="extractingLocations" @click="showExtractConfirm = false">{{ t('itemModal.cancel') }}</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
