<script setup lang="ts">
import type { Item, CollectionShareItem, Tag } from '~/types/api'

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

const apiFetch = useApiFetch()
const gmap = useGlobalMap()
const { getItem, getItemTags, attachTag, detachTag, updateItem } = useItems()
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
  if (panel.scrollTop <= 0 && deltaY > 0) {
    panel.style.transition = 'none'
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
  if (panel.scrollTop <= 0 && deltaY > 80) {
    panel.style.transition = 'transform .2s ease'
    panel.style.transform = 'translateY(100%)'
    setTimeout(doClose, 200)
  } else {
    panel.style.transition = 'transform .3s cubic-bezier(0.32,0.72,0,1)'
    panel.style.transform = ''
    setTimeout(() => { if (panel) panel.style.transition = '' }, 300)
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
    placeError.value = '無法載入地點資訊'
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

async function extractLocations() {
  if (!props.itemId) return
  extractingLocations.value = true
  try {
    const result = await apiFetch<{ locations: ItemLocation[], extracting: boolean }>(
      `/items/${props.itemId}/locations/extract`, { method: 'POST' }
    )
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
  } catch {
    extractingLocations.value = false
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
      ? `找到 ${results.length} 個結果，點 pin 確認後新增`
      : '找不到相關地點'
  } catch {
    searchHint.value = '搜尋失敗，請稍後再試'
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
  addBtn.textContent = '+ 新增地標'
  addBtn.addEventListener('click', async () => {
    addBtn.disabled = true
    addBtn.textContent = '新增中…'
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
let _reanalyzePollTimer: ReturnType<typeof setTimeout> | null = null

async function reanalyze() {
  if (!props.itemId) return
  reanalyzing.value = true
  try {
    await apiFetch(`/items/${props.itemId}/reanalyze`, { method: 'POST' })
    pollReanalyze()
  } catch {
    reanalyzing.value = false
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
  if (/youtu/.test(url)) return '▶ YouTube'
  if (/instagram\.com/.test(url)) return 'IG'
  return 'Article'
}

function cardTitle(url: string, title: string | null) {
  if (title) return title
  try { return new URL(url).hostname.replace(/^www\./, '') }
  catch { return '' }
}

function relativeTime(dateStr: string) {
  const d = Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000)
  if (d === 0) return '今天'
  if (d === 1) return '1 天前'
  return `${d} 天前`
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
            {{ error ? '載入失敗，請重新整理' : '載入中...' }}
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
                  {{ isEditingNotes ? '保存' : '編輯筆記' }}
                </button>
                <button
                  v-if="!readonly && activeTab === 'info' && !isEditingNotes"
                  class="btn"
                  :disabled="reanalyzing || isAnalyzing"
                  @click="reanalyze"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>
                  </svg>
                  {{ (reanalyzing || isAnalyzing) ? '分析中…' : '重新分析' }}
                </button>
                <button
                  v-if="!readonly && activeTab === 'map'"
                  class="btn btn--accent"
                  :disabled="extractingLocations"
                  @click="extractLocations"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="10" r="3"/><path d="M12 2a8 8 0 0 0-8 8c0 5.25 8 14 8 14s8-8.75 8-14a8 8 0 0 0-8-8z"/>
                  </svg>
                  {{ extractingLocations ? '抓取中…' : '重新抓取地標' }}
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
                  {{ archiving ? '處理中…' : (item as Item).status === 'archived' ? '復原' : '封存' }}
                </button>
              </div>
            </div>

            <!-- Tab bar (only in private mode) -->
            <div v-if="!readonly" class="id-tabs">
              <button
                class="id-tab"
                :class="{ 'id-tab--active': activeTab === 'info' }"
                @click="switchToInfoTab"
              >筆記</button>
              <button
                class="id-tab"
                :class="{ 'id-tab--active': activeTab === 'map' }"
                @click="switchToMapTab"
              >地圖</button>
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
                    placeholder="標籤名稱"
                    @keydown.enter="handleAddTag"
                    @keydown.esc.stop="addingTag = false; newTagInput = ''"
                    @blur="handleAddTag"
                  />
                </template>
                <button v-else class="id-tag__add" :disabled="tagAdding" @click="startAddingTag">
                  + 新增標籤
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
                  筆記分析失敗，可點上方「重新分析」重試
                </div>
                <div
                  v-else-if="!readonly && !(item as Item).parsed_at"
                  class="notes-analyzing"
                >
                  <span class="notes-analyzing__spinner" />
                  <span class="notes-analyzing__text">筆記分析中…</span>
                </div>
                <p v-else class="id-body__summary-empty">尚無筆記</p>
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
                    placeholder="搜尋地點，結果會標在地圖上…"
                    autocomplete="off"
                    :disabled="savingNewLoc"
                    @input="onSearchInput"
                    @keydown.enter.prevent="onSearchInput"
                    @keydown.esc="clearSearch"
                  />
                  <span v-if="searchLoading" class="id-map-search__saving">搜尋中…</span>
                  <span v-else-if="savingNewLoc" class="id-map-search__saving">新增中…</span>
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
                    所有地標
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
                  <div v-if="loadingLocations" class="id-map-locations__loading">載入地點中…</div>
                  <template v-else-if="itemLocations.length">
                    <div v-for="loc in itemLocations" :key="loc.id" class="id-map-loc" @click="selectLocation(loc)">
                      <svg class="id-map-loc__pin" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                        <circle cx="12" cy="10" r="3"/><path d="M12 2a8 8 0 0 0-8 8c0 5.25 8 14 8 14s8-8.75 8-14a8 8 0 0 0-8-8z"/>
                      </svg>
                      <span class="id-map-loc__name">{{ loc.name }}</span>
                      <span v-if="loc.geocoding_status === 'pending'" class="id-map-loc__nogeo id-map-loc__nogeo--pending">座標取得中…</span>
                      <span v-else-if="loc.geocoding_status === 'failed'" class="id-map-loc__nogeo id-map-loc__nogeo--failed">無法取得座標</span>
                      <span class="id-map-loc__badge" :class="`id-map-loc__badge--${loc.source}`">
                        {{ loc.source === 'metadata' ? 'meta' : loc.source === 'user' ? '手動' : 'AI' }}
                      </span>
                      <button class="id-map-loc__btn id-map-loc__btn--delete" @click.stop="deleteLocation(loc)">刪除</button>
                    </div>
                  </template>
                  <div v-else class="id-map-locations__empty">
                    <span>此內容尚無地點資訊</span>
                    <button
                      class="id-map-loc__btn id-map-loc__btn--extract"
                      :disabled="extractingLocations"
                      @click="extractLocations"
                    >
                      {{ extractingLocations ? '抽取中…' : '補抓地點' }}
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
      <div v-if="loading" class="idp-state">載入中...</div>
      <div v-else-if="error" class="idp-state">載入失敗，請重新整理</div>
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
                  placeholder="標籤名稱"
                  @keydown.enter="handleAddTag"
                  @keydown.esc.stop="addingTag = false; newTagInput = ''"
                  @blur="handleAddTag"
                />
              </template>
              <button v-else class="id-tag__add" :disabled="tagAdding" @click="startAddingTag">
                + 新增標籤
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
                筆記分析失敗，可點上方「重新分析」重試
              </div>
              <div
                v-else-if="!readonly && !(item as Item).parsed_at"
                class="notes-analyzing"
              >
                <span class="notes-analyzing__spinner" />
                <span class="notes-analyzing__text">筆記分析中…</span>
              </div>
              <p v-else class="id-body__summary-empty">尚無筆記</p>
            </div>

            <div class="id-body__actions">
              <button
                v-if="!readonly"
                class="btn btn--accent"
                :disabled="savingNotes"
                @click="isEditingNotes ? saveNotes() : startEditNotes()"
              >
                {{ isEditingNotes ? (savingNotes ? '儲存中…' : '保存') : '編輯筆記' }}
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
                {{ archiving ? '處理中…' : (item as Item).status === 'archived' ? '復原' : '封存' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Archive confirm（兩種模式共用） -->
    <div v-if="showArchiveConfirm" class="modal-mask" @click.self="showArchiveConfirm = false">
      <div class="modal">
        <h2>確認封存</h2>
        <p>封存後此內容將從首頁與搜尋結果中隱藏，可前往<b>封存庫</b>隨時復原。</p>
        <div class="modal__actions">
          <button class="btn btn--warn" style="flex:1;" :disabled="archiving" @click="confirmArchive">
            {{ archiving ? '處理中…' : '封存' }}
          </button>
          <button class="btn" :disabled="archiving" @click="showArchiveConfirm = false">取消</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
