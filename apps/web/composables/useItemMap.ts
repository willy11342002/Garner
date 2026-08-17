/**
 * ItemDetailModal 的地圖分頁：地點載入、marker 渲染、地點搜尋與新增、geocoding 輪詢。
 *
 * 從 components/item/ItemDetailModal.vue 抽出來（原本佔該檔 script 約三分之一）。
 * 目前只有那一個使用者，抽出來是為了讓元件回到「畫面組裝」而不是塞滿地圖邏輯。
 *
 * 與元件的耦合刻意收斂成兩個參數：
 * - `itemId`：目前開啟的收藏（null 代表沒開）
 * - `activeTab`：資訊／地圖分頁。切換分頁牽涉 gmap 的 claim / release，
 *   所以由這裡代管，元件只要把同一個 ref 傳進來。
 */

import type { Ref } from 'vue'

export interface ItemLocation {
  id: string
  name: string
  lat: number | null
  lng: number | null
  source: 'ai' | 'metadata' | 'user'
  order_index: number
  geocoding_status: 'pending' | 'done' | 'failed'
}

export interface PlaceSearchResult {
  place_id: string
  lat: number
  lng: number
  name: string
  display_name: string
  type: string
}

export interface PlaceDetails {
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

export function useItemMap(
  itemId: Ref<string | null | undefined>,
  activeTab: Ref<'info' | 'map'>,
) {
  const { t } = useI18n()
  const apiFetch = useApiFetch()
  const gmap = useGlobalMap()

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

  // Owner key changes with each item so re-opening a different item always re-claims
  const mapOwnerKey = computed(() => `modal:${itemId.value ?? ''}`)

  // ── Geocoding poll ──────────────────────────────────────────────────────────
  // waitForAny=true: legacy item, poll until at least one location appears then check pending
  // waitForAny=false: snapshot path, locations exist but may be pending geocoding
  function startGeocodingPoll(waitForAny = false, maxAttempts = 40) {
    if (_geocodingPollTimer) return
    let attempts = 0
    async function poll() {
      if (!itemId.value || attempts >= maxAttempts) {
        _geocodingPollTimer = null
        extractingLocations.value = false
        return
      }
      attempts++
      try {
        const locs = await apiFetch<ItemLocation[]>(`/items/${itemId.value}/locations`, { skipWhenHidden: true })
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

  // ── Selected location (place panel) ─────────────────────────────────────────
  const selectedLoc = ref<ItemLocation | null>(null)
  const placeData = ref<PlaceDetails | null>(null)
  const placeLoading = ref(false)
  const placeError = ref('')

  async function selectLocation(loc: ItemLocation) {
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

  // ── Tab switching ───────────────────────────────────────────────────────────
  async function switchToMapTab() {
    activeTab.value = 'map'
    await nextTick()  // wait for mapSlotEl to mount via v-if
    if (!mapSlotEl.value || !itemId.value) return
    await gmap.claim(mapSlotEl.value, mapOwnerKey.value)
    await loadItemLocations()
  }

  function switchToInfoTab() {
    clearSearch()   // also calls clearSearchPins()
    clearSelectedLoc()
    gmap.release(mapOwnerKey.value)
    activeTab.value = 'info'
  }

  // ── Locations ───────────────────────────────────────────────────────────────
  async function loadItemLocations() {
    if (!itemId.value) return
    loadingLocations.value = true
    try {
      itemLocations.value = await apiFetch<ItemLocation[]>(`/items/${itemId.value}/locations`)
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
    if (!itemId.value) return
    await apiFetch(`/items/${itemId.value}/locations/${loc.id}`, { method: 'DELETE' })
    itemLocations.value = itemLocations.value.filter(l => l.id !== loc.id)
    if (selectedLoc.value?.id === loc.id) clearSelectedLoc()
    renderItemMarkers()
  }

  // ── Re-extract locations ────────────────────────────────────────────────────
  const showExtractConfirm = ref(false)
  const extractQuotaError = ref(false)

  function requestExtractLocations() {
    extractQuotaError.value = false
    showExtractConfirm.value = true
  }

  async function extractLocations() {
    if (!itemId.value) return
    extractingLocations.value = true
    extractQuotaError.value = false
    try {
      const result = await apiFetch<{ locations: ItemLocation[], extracting: boolean }>(
        `/items/${itemId.value}/locations/extract`, { method: 'POST' }
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

  // ── Place search ────────────────────────────────────────────────────────────
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
    if (!itemId.value) return
    savingNewLoc.value = true
    try {
      const newLoc = await apiFetch<ItemLocation>(`/items/${itemId.value}/locations`, {
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

  // ── 生命週期 ────────────────────────────────────────────────────────────────
  /** 切換到另一筆收藏時呼叫：釋放前一筆的地圖擁有權並回到資訊分頁。 */
  function resetForItem(prevId: string | null | undefined) {
    if (activeTab.value === 'map') {
      gmap.release(`modal:${prevId ?? ''}`)
      activeTab.value = 'info'
    }
    itemLocations.value = []
  }

  /** 關閉彈窗時呼叫：只在停留於地圖分頁時才需要收拾。 */
  function leaveMapTab() {
    if (activeTab.value === 'map') {
      clearSearch()
      gmap.release(mapOwnerKey.value)
      activeTab.value = 'info'
    }
  }

  onUnmounted(() => {
    clearSearch()
    stopGeocodingPoll()
    if (activeTab.value === 'map') gmap.release(mapOwnerKey.value)
  })

  return {
    mapSlotEl,
    itemLocations,
    loadingLocations,
    extractingLocations,
    searchQuery,
    searchLoading,
    searchHint,
    savingNewLoc,
    selectedLoc,
    placeData,
    placeLoading,
    placeError,
    showExtractConfirm,
    extractQuotaError,
    switchToMapTab,
    switchToInfoTab,
    selectLocation,
    clearSelectedLoc,
    deleteLocation,
    requestExtractLocations,
    extractLocations,
    onSearchInput,
    clearSearch,
    resetForItem,
    leaveMapTab,
  }
}
