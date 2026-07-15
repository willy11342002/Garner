<script setup lang="ts">
import type { Item, CollectionShareItem, Tag } from '~/types/api'
import { needsRetry } from '~/utils/itemStatus'

type AnyItem = Item | CollectionShareItem

interface PlaceSearchResult {
  place_id: string
  lat: number
  lng: number
  name: string
  display_name: string
  type: string
}

interface ItemLocation {
  id: string
  name: string
  lat: number | null
  lng: number | null
  source: 'ai' | 'metadata' | 'user'
  order_index: number
  geocoding_status: 'pending' | 'done' | 'failed'
}

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
const apiFetch = useApiFetch()
const gmap = useGlobalMap()
const { getItem, getItemTags, attachTag, detachTag, updateItem, resumeItem } = useItems()
const { updateArticle } = useArticles()
const { toggle: toggleChain, isInChain } = useChain()

const fetchedItem = ref<Item | null>(null)
const tags = ref<Tag[]>([])
const loading = ref(false)
const error = ref(false)

const item = computed(() => readonly.value ? props.item ?? null : fetchedItem.value)

// ── Tab ───────────────────────────────────────────────────────────────────────
const activeTab = ref<'info' | 'map'>('info')
const mapSlotEl = ref<HTMLElement | null>(null)
const itemLocations = ref<ItemLocation[]>([])
const loadingLocations = ref(false)
const extractingLocations = ref(false)
const searchQuery = ref('')
const searchLoading = ref(false)
const searchHint = ref('')      // status text shown below search box
const savingNewLoc = ref(false)
let _searchDebounceTimer: ReturnType<typeof setTimeout> | null = null
let _searchPins: import('leaflet').Marker[] = []
let _geocodingPollTimer: ReturnType<typeof setTimeout> | null = null

// ── Swipe-down-to-close (mobile) ─────────────────────────────────────────────
const panelRef = ref<HTMLElement | null>(null)
const overlayRef = ref<HTMLElement | null>(null)
let _touchStartY = 0

function onPanelTouchStart(e: TouchEvent) {
  _touchStartY = e.touches[0].clientY
}

function onPanelTouchMove(e: TouchEvent) {
  const panel = panelRef.value
  if (!panel) return
  
  const deltaY = e.touches[0].clientY - _touchStartY
  
  // 當面板滾動到頂，且用戶向下拖拽時
  if (panel.scrollTop <= 0 && deltaY > 0) {
    panel.style.transition = 'none' // 拖拽時不需要動畫，才能即時跟手
    panel.style.bottom = `-${deltaY}px`
  } else {
    panel.style.transition = ''
    panel.style.bottom = ''
  }
}

function onPanelTouchEnd(e: TouchEvent) {
  const panel = panelRef.value
  if (!panel) return

  const deltaY = e.changedTouches[0].clientY - _touchStartY

  // 判斷是否觸發關閉（向下拖拽超過 80px 且處於頂部）
  if (panel.scrollTop <= 0 && deltaY > 80) {
    // 【方案 A：動畫關閉】
    // 給 bottom 加上平滑動畫，並將其設為 -100vh 移出螢幕外
    panel.style.transition = 'bottom .2s ease-out'
    panel.style.bottom = '-100vh'
    
    // 等 200ms 動畫結束後，執行真正的關閉邏輯與清理
    setTimeout(() => {
      doClose()
      if (panel) {
        panel.style.transition = ''
        panel.style.bottom = '' // 重設樣式，避免下次打開時卡在下面
      }
    }, 200)

  } else if (deltaY > 0) {
    // 【方案 B：動畫復位】
    // 有被向下拉但沒超過 80px，平滑彈回原本的 bottom: 0
    panel.style.transition = 'bottom .3s cubic-bezier(0.32, 0.72, 0, 1)'
    panel.style.bottom = '0px'
    
    // 動畫結束後清除 transition 恢復乾淨狀態
    setTimeout(() => {
      if (panel) panel.style.transition = ''
    }, 300)
  }
}

// waitForAny=true: legacy item, poll until at least one location appears then check pending
// waitForAny=false: snapshot path, locations exist but may be pending geocoding
function startGeocodingPoll(waitForAny = false, maxAttempts = 40) {
  if (_geocodingPollTimer) return
  let attempts = 0
  async function poll() {
    if (!props.itemId || attempts >= maxAttempts) {
      _geocodingPollTimer = null
      extractingLocations.value = false
      return
    }
    attempts++
    try {
      const locs = await apiFetch<ItemLocation[]>(`/items/${props.itemId}/locations`)
      itemLocations.value = locs
      const hasAny = locs.length > 0
      const hasPending = locs.some(l => l.geocoding_status === 'pending')
      const keepPolling = (waitForAny && !hasAny) || hasPending
      if (keepPolling) {
        _geocodingPollTimer = setTimeout(poll, 3000)
      } else {
        _geocodingPollTimer = null
        extractingLocations.value = false
        renderItemMarkers()
        gmap.notifyLocationChange()
      }
    } catch {
      _geocodingPollTimer = null
      extractingLocations.value = false
    }
  }
  _geocodingPollTimer = setTimeout(poll, 3000)
}

function stopGeocodingPoll() {
  if (_geocodingPollTimer) { clearTimeout(_geocodingPollTimer); _geocodingPollTimer = null }
  extractingLocations.value = false
}

// Owner key changes with each item so re-opening a different item always re-claims
const mapOwnerKey = computed(() => `modal:${props.itemId ?? ''}`)

// ── Selected location (place panel) ──────────────────────────────────────────
interface PlaceDetails {
  place_id: string
  name: string | null
  rating: number | null
  reviews: Array<{ author: string | null; author_photo: string | null; rating: number | null; text: string | null; relative_time: string | null }> | null
  photos: string[] | null
  address: string | null
  phone: string | null
  opening_hours: { open_now: boolean; weekday_descriptions: string[] } | null
  maps_url: string | null
}

const selectedLoc = ref<typeof itemLocations.value[0] | null>(null)
const placeData = ref<PlaceDetails | null>(null)
const placeLoading = ref(false)
const placeError = ref('')

async function selectLocation(loc: typeof itemLocations.value[0]) {
  selectedLoc.value = loc
  placeData.value = null
  placeError.value = ''
  if (!loc.lat || !loc.lng) return
  placeLoading.value = true
  try {
    const result = await apiFetch<PlaceDetails | null>(
      `/places/lookup?name=${encodeURIComponent(loc.name)}&lat=${loc.lat}&lng=${loc.lng}`
    )
    placeData.value = result ?? null
  } catch {
    placeError.value = t('itemModal.placeLoadError')
  } finally {
    placeLoading.value = false
  }
}

function clearSelectedLoc() {
  selectedLoc.value = null
  placeData.value = null
  placeError.value = ''
}

async function switchToMapTab() {
  activeTab.value = 'map'
  await nextTick()  // wait for mapSlotEl to mount via v-if
  if (!mapSlotEl.value || !props.itemId) return
  await gmap.claim(mapSlotEl.value, mapOwnerKey.value)
  await loadItemLocations()
}

function switchToInfoTab() {
  clearSearch()   // also calls clearSearchPins()
  clearSelectedLoc()
  gmap.release(mapOwnerKey.value)
  activeTab.value = 'info'
}

async function loadItemLocations() {
  if (!props.itemId) return
  loadingLocations.value = true
  try {
    itemLocations.value = await apiFetch<ItemLocation[]>(`/items/${props.itemId}/locations`)
    renderItemMarkers()
  } finally {
    loadingLocations.value = false
  }
}

function renderItemMarkers() {
  const map = gmap.getMap()
  const L = gmap.getL()
  if (!map || !L) return

  gmap.clearAllMarkers()

  const geoLocs = itemLocations.value.filter(l => l.lat !== null && l.lng !== null)
  if (!geoLocs.length) return

  const markerList: import('leaflet').Marker[] = []
  for (const loc of geoLocs) {
    const icon = L.divIcon({
      className: '',
      html: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="32" viewBox="0 0 24 32" class="map-pin">
        <path d="M12 0C5.37 0 0 5.37 0 12c0 8 12 20 12 20S24 20 24 12C24 5.37 18.63 0 12 0z"/>
        <circle cx="12" cy="11" r="4.5" fill="white" fill-opacity="0.92"/>
      </svg>`,
      iconSize: [24, 32],
      iconAnchor: [12, 32],
    })
    const m = L.marker([loc.lat!, loc.lng!], { icon }).addTo(map)
    m.on('click', () => selectLocation(loc))
    gmap.registerMarker(m)
    markerList.push(m)
  }

  if (markerList.length > 0) {
    const group = L.featureGroup(markerList)
    map.fitBounds(group.getBounds().pad(0.4), { maxZoom: 14, animate: false })
  }
}


async function deleteLocation(loc: ItemLocation) {
  if (!props.itemId) return
  await apiFetch(`/items/${props.itemId}/locations/${loc.id}`, { method: 'DELETE' })
  itemLocations.value = itemLocations.value.filter(l => l.id !== loc.id)
  if (selectedLoc.value?.id === loc.id) clearSelectedLoc()
  renderItemMarkers()
}

const showExtractConfirm = ref(false)
const extractQuotaError = ref(false)

function requestExtractLocations() {
  extractQuotaError.value = false
  showExtractConfirm.value = true
}

async function extractLocations() {
  if (!props.itemId) return
  extractingLocations.value = true
  extractQuotaError.value = false
  try {
    const result = await apiFetch<{ locations: ItemLocation[], extracting: boolean }>(
      `/items/${props.itemId}/locations/extract`, { method: 'POST' }
    )
    showExtractConfirm.value = false
    itemLocations.value = result.locations
    renderItemMarkers()
    gmap.notifyLocationChange()
    if (result.extracting) {
      // Legacy item: full pipeline running in background, keep spinner and poll for locations
      startGeocodingPoll(true)
    } else if (result.locations.some(l => l.geocoding_status === 'pending')) {
      // Snapshot path: locations saved, geocoding in background
      startGeocodingPoll(false)
    } else {
      extractingLocations.value = false
    }
  } catch (err: any) {
    extractingLocations.value = false
    if (err?.response?.status === 429) {
      extractQuotaError.value = true  // keep dialog open to show the message
    } else {
      showExtractConfirm.value = false
    }
  }
}

function onSearchInput() {
  if (_searchDebounceTimer) clearTimeout(_searchDebounceTimer)
  const q = searchQuery.value.trim()
  if (q.length < 2) { clearSearchPins(); searchHint.value = ''; return }
  _searchDebounceTimer = setTimeout(() => doSearch(q), 350)
}

async function doSearch(q: string) {
  searchLoading.value = true
  searchHint.value = ''
  try {
    const map = gmap.getMap()
    const params = new URLSearchParams({ q })
    if (map) {
      const bounds = map.getBounds()
      const center = bounds.getCenter()
      const ne = bounds.getNorthEast()
      const radiusMeters = Math.min(Math.round(center.distanceTo(ne)), 50000)
      params.set('lat', center.lat.toString())
      params.set('lng', center.lng.toString())
      params.set('radius', radiusMeters.toString())
    }
    const results = await apiFetch<PlaceSearchResult[]>(`/places/search?${params}`)
    showSearchPins(results)
    searchHint.value = results.length
      ? t('itemModal.searchFound', { n: results.length })
      : t('itemModal.searchNoResult')
  } catch {
    searchHint.value = t('itemModal.searchFailed')
  } finally {
    searchLoading.value = false
  }
}

function clearSearchPins() {
  for (const m of _searchPins) m.remove()
  _searchPins = []
}

function showSearchPins(results: PlaceSearchResult[]) {
  const map = gmap.getMap()
  const L = gmap.getL()
  if (!map || !L) return
  clearSearchPins()
  if (!results.length) return
  for (const r of results) {
    const icon = L.divIcon({
      className: '',
      html: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="32" viewBox="0 0 24 32" class="map-pin map-pin--search">
        <path d="M12 0C5.37 0 0 5.37 0 12c0 8 12 20 12 20S24 20 24 12C24 5.37 18.63 0 12 0z"/>
        <circle cx="12" cy="11" r="4.5" fill="white" fill-opacity="0.92"/>
      </svg>`,
      iconSize: [24, 32],
      iconAnchor: [12, 32],
    })
    const m = L.marker([r.lat, r.lng], { icon }).addTo(map)
    m.bindPopup(
      L.popup({ closeButton: false, className: 'id-loc-popup', offset: [0, -18] })
        .setContent(buildSearchPinPopup(r))
    )
    _searchPins.push(m)
  }
  const group = L.featureGroup(_searchPins)
  map.fitBounds(group.getBounds().pad(0.5), { maxZoom: 14, animate: true })
}

function buildSearchPinPopup(r: PlaceSearchResult): HTMLElement {
  const root = document.createElement('div')
  root.className = 'id-loc-popup__inner'

  const name = document.createElement('div')
  name.className = 'id-loc-popup__name'
  name.textContent = r.name
  root.appendChild(name)

  // Show address without the first part (= name) to avoid duplication
  const addrParts = r.display_name.split(', ').slice(1, 4)
  if (addrParts.length) {
    const addr = document.createElement('div')
    addr.className = 'id-loc-popup__addr'
    addr.textContent = addrParts.join(', ')
    root.appendChild(addr)
  }

  const actions = document.createElement('div')
  actions.className = 'id-loc-popup__actions'

  const addBtn = document.createElement('button')
  addBtn.className = 'id-loc-popup__btn id-loc-popup__btn--confirm'
  addBtn.textContent = t('itemModal.addLandmark')
  addBtn.addEventListener('click', async () => {
    addBtn.disabled = true
    addBtn.textContent = t('itemModal.adding')
    await createLocation(r.name, r.lat, r.lng)
  })
  actions.appendChild(addBtn)
  root.appendChild(actions)
  return root
}

function clearSearch() {
  searchQuery.value = ''
  searchHint.value = ''
  clearSearchPins()
  if (_searchDebounceTimer) { clearTimeout(_searchDebounceTimer); _searchDebounceTimer = null }
}

async function createLocation(name: string, lat: number, lng: number) {
  if (!props.itemId) return
  savingNewLoc.value = true
  try {
    const newLoc = await apiFetch<ItemLocation>(`/items/${props.itemId}/locations`, {
      method: 'POST',
      body: { name, lat, lng },
    })
    itemLocations.value.push(newLoc)
    clearSearchPins()
    clearSearch()
    renderItemMarkers()
  } finally {
    savingNewLoc.value = false
  }
}

// ── Tags ──────────────────────────────────────────────────────────────────────
const addingTag = ref(false)
const newTagInput = ref('')
const tagRemoving = ref<Record<string, boolean>>({})
const tagAdding = ref(false)
const tagInputRef = ref<HTMLInputElement | null>(null)

// ── Inline title editing ─────────────────────────────────────────────────────
const isEditingTitle = ref(false)
const editingTitle = ref('')
const savingTitle = ref(false)
const titleInputRef = ref<HTMLInputElement | null>(null)

function startEditTitle() {
  if (readonly.value) return
  editingTitle.value = (item.value as Item)?.title ?? ''
  isEditingTitle.value = true
  nextTick(() => titleInputRef.value?.focus())
}

async function saveTitle() {
  if (!item.value) return
  const trimmed = editingTitle.value.trim()
  isEditingTitle.value = false
  if (trimmed === ((item.value as Item)?.title ?? '')) return
  savingTitle.value = true
  try {
    await updateArticle(item.value.id, { title: trimmed || null })
    if (fetchedItem.value) fetchedItem.value = { ...fetchedItem.value, title: trimmed || null }
  } finally {
    savingTitle.value = false
  }
}

function cancelEditTitle() {
  isEditingTitle.value = false
  editingTitle.value = ''
}

// ── Reanalyze (stage 3 → 5) ──────────────────────────────────────────────────
const reanalyzing = ref(false)
const showReanalyzeConfirm = ref(false)
const reanalyzeQuotaError = ref(false)
let _reanalyzePollTimer: ReturnType<typeof setTimeout> | null = null

function requestReanalyze() {
  reanalyzeQuotaError.value = false
  showReanalyzeConfirm.value = true
}

async function reanalyze() {
  if (!props.itemId) return
  reanalyzing.value = true
  reanalyzeQuotaError.value = false
  try {
    await apiFetch(`/items/${props.itemId}/reanalyze`, { method: 'POST' })
    showReanalyzeConfirm.value = false
    pollReanalyze()
  } catch (err: any) {
    reanalyzing.value = false
    if (err?.response?.status === 429) {
      reanalyzeQuotaError.value = true  // keep dialog open to show the message
    } else {
      showReanalyzeConfirm.value = false
    }
  }
}

function pollReanalyze(maxAttempts = 60) {
  let attempts = 0
  async function poll() {
    if (!props.itemId || attempts >= maxAttempts) {
      reanalyzing.value = false
      _reanalyzePollTimer = null
      return
    }
    attempts++
    try {
      const updated = await apiFetch<Item>(`/items/${props.itemId}`)
      const done = updated.note_status === 'complete' && updated.embedding_status === 'complete'
      const failed = updated.note_status === 'error'
      if (done || failed) {
        if (done) fetchedItem.value = updated
        reanalyzing.value = false
        _reanalyzePollTimer = null
        return
      }
    } catch {}
    _reanalyzePollTimer = setTimeout(poll, 2000)
  }
  poll()
}

onUnmounted(() => {
  if (_reanalyzePollTimer) clearTimeout(_reanalyzePollTimer)
})

// ── Initial-analysis polling (item opened while still being processed) ─────────
let _analysisPollTimer: ReturnType<typeof setTimeout> | null = null

function stopAnalysisPoll() {
  if (_analysisPollTimer) { clearTimeout(_analysisPollTimer); _analysisPollTimer = null }
}

function pollAnalysis(maxAttempts = 90) {
  stopAnalysisPoll()
  let attempts = 0
  async function poll() {
    if (!props.itemId || attempts >= maxAttempts) { _analysisPollTimer = null; return }
    attempts++
    try {
      const updated = await apiFetch<Item>(`/items/${props.itemId}`)
      if (!isEditingNotes.value) fetchedItem.value = updated
      if (updated.note_status === 'complete' || updated.note_status === 'error') {
        _analysisPollTimer = null
        return
      }
    } catch {}
    _analysisPollTimer = setTimeout(poll, 2000)
  }
  _analysisPollTimer = setTimeout(poll, 2000)
}

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

const retrying = ref(false)

async function retryIngest() {
  if (!props.itemId || retrying.value) return
  retrying.value = true
  try {
    await resumeItem(props.itemId)
    pollAnalysis()
  } finally {
    retrying.value = false
  }
}

// ── Inline note editing ───────────────────────────────────────────────────────
const isEditingNotes = ref(false)
const editingNotesMd = ref('')

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
  updateArticle(item.value.id, { notes_md: notesMd, title: titleTrimmed })
}

// ── Archive ───────────────────────────────────────────────────────────────────
const archiving = ref(false)
const showArchiveConfirm = ref(false)

const TAG_COLORS = ['a', 'b', 'c', 'd', 'e'] as const
function tagColor(i: number) { return TAG_COLORS[i % TAG_COLORS.length] }

function sourceLabel(url: string) {
  if (/youtu/.test(url)) return 'YouTube'
  if (/instagram\.com/.test(url)) return 'IG'
  if (/tiktok\.com|vt\.tiktok\.com/.test(url)) return 'TikTok'
  if (/facebook\.com|fb\.watch/.test(url)) return 'Facebook'
  return 'Article'
}

function cardTitle(url: string, title: string | null) {
  if (title) return title
  try { return new URL(url).hostname.replace(/^www\./, '') }
  catch { return '' }
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
  // Reset map tab when item changes
  if (activeTab.value === 'map') {
    gmap.release(`modal:${prevId ?? ''}`)
    activeTab.value = 'info'
  }
  itemLocations.value = []

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
  lockScroll(false)
  clearSearch()
  stopGeocodingPoll()
  stopAnalysisPoll()
  if (activeTab.value === 'map') gmap.release(mapOwnerKey.value)
})

function doClose() {
  if (activeTab.value === 'map') {
    clearSearch()
    gmap.release(mapOwnerKey.value)
    activeTab.value = 'info'
  }
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
    delete tagRemoving.value[tag.id]
  }
}

// ── Archive handlers ──────────────────────────────────────────────────────────
function requestArchive() {
  if (item.value?.status === 'archived') confirmArchive()
  else showArchiveConfirm.value = true
}

async function confirmArchive() {
  if (!item.value) return
  showArchiveConfirm.value = false
  archiving.value = true
  try {
    const isArchived = item.value.status === 'archived'
    await updateItem(item.value.id, { status: isArchived ? 'active' : 'archived' })
    fetchedItem.value = { ...fetchedItem.value!, status: isArchived ? 'active' : 'archived' }
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
        @click.self="doClose"
        @keydown.esc="doClose"
        tabindex="-1"
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
            <img v-if="item.thumbnail_url" :src="item.thumbnail_url" class="id-media__img" alt="">
            <div v-else class="placeholder placeholder--b id-media__ph">
              <div class="placeholder__stripes"></div>
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
              />
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
                  />
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
                  />
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
            <img v-if="item.thumbnail_url" :src="item.thumbnail_url" class="idp-media__img" alt="">
            <div v-else class="placeholder placeholder--b idp-media__ph">
              <div class="placeholder__stripes"></div>
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
              />
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
                />
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
