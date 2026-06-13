<script setup lang="ts">
import type { LatLngBounds } from 'leaflet'

interface MapLocation {
  id: string
  name: string
  lat: number
  lng: number
  source: string
  content_id: string
  item_id: string
  item_title: string | null
  item_thumbnail: string | null
  item_source_type: string | null
}

interface PlaceReview {
  author: string | null
  author_photo: string | null
  rating: number | null
  text: string | null
  relative_time: string | null
}

interface PlaceDetails {
  place_id: string
  name: string | null
  rating: number | null
  reviews: PlaceReview[] | null
  photos: string[] | null
  address: string | null
  phone: string | null
  opening_hours: { open_now: boolean; weekday_descriptions: string[] } | null
  maps_url: string | null
}

const apiFetch = useApiFetch()
const itemStore = useItemStore()
const gmap = useGlobalMap()

// ── Map state ─────────────────────────────────────────────────────────────────
const mapContainer = ref<HTMLElement | null>(null)
let localMarkers: Map<string, ReturnType<typeof gmap.getL>['Marker'] extends undefined ? never : import('leaflet').Marker> = new Map()

const locations = ref<MapLocation[]>([])
const allLocatedItemIds = ref<Set<string>>(new Set())
const loadingMap = ref(true)
const errorMsg = ref('')

// ── Drawer state ──────────────────────────────────────────────────────────────
const drawerOpen = ref(false)
const drawerLocationName = ref('')
const drawerItems = ref<MapLocation[]>([])
const drawerTab = ref<'place' | 'items'>('place')

// Place info state
const placeData = ref<PlaceDetails | null>(null)
const placeLoading = ref(false)
const placeError = ref('')

// ── No-location items ─────────────────────────────────────────────────────────
const noLocationItems = computed(() =>
  itemStore.items.filter(item => !allLocatedItemIds.value.has(item.id) && item.status === 'active')
)

const extractingIds = ref<Set<string>>(new Set())

async function extractLocations(itemId: string) {
  if (extractingIds.value.has(itemId)) return
  extractingIds.value = new Set([...extractingIds.value, itemId])
  try {
    const locs = await apiFetch<Array<{ id: string }>>(`/items/${itemId}/locations/extract`, { method: 'POST' })
    if (locs.length > 0) {
      allLocatedItemIds.value = new Set([...allLocatedItemIds.value, itemId])
      await loadLocationsInBounds()
    }
  } catch {}
  finally {
    const s = new Set(extractingIds.value)
    s.delete(itemId)
    extractingIds.value = s
  }
}

// ── Map setup ─────────────────────────────────────────────────────────────────
async function setupMap() {
  if (!mapContainer.value) return
  localMarkers = new Map()
  await gmap.claim(mapContainer.value, 'home')
  gmap.onMoveEnd(loadLocationsInBounds)

  try {
    const all = await apiFetch<MapLocation[]>('/locations?bounds=-90,-180,90,180')
    allLocatedItemIds.value = new Set(all.map(l => l.item_id))
  } catch {}

  await loadLocationsInBounds()
  loadingMap.value = false
}

async function reclaimMap() {
  if (!mapContainer.value) return
  localMarkers = new Map()
  await gmap.claim(mapContainer.value, 'home')
  gmap.onMoveEnd(loadLocationsInBounds)
  await loadLocationsInBounds()
}

// ── Fetch locations ───────────────────────────────────────────────────────────
async function loadLocationsInBounds() {
  const map = gmap.getMap()
  if (!map) return

  const bounds: LatLngBounds = map.getBounds()
  const sw = bounds.getSouthWest()
  const ne = bounds.getNorthEast()
  const boundsParam = `${sw.lat},${sw.lng},${ne.lat},${ne.lng}`

  try {
    const data = await apiFetch<MapLocation[]>(`/locations?bounds=${boundsParam}`)
    locations.value = data
    updateMarkers(data)
  } catch {
    errorMsg.value = '無法載入地點資料'
  }
}

// ── Markers ───────────────────────────────────────────────────────────────────
function updateMarkers(locs: MapLocation[]) {
  const map = gmap.getMap()
  const L = gmap.getL()
  if (!map || !L) return

  // Remove markers no longer in viewport
  const newIds = new Set(locs.map(l => l.id))
  for (const [id, marker] of localMarkers) {
    if (!newIds.has(id)) {
      gmap.removeMarker(marker)
      localMarkers.delete(id)
    }
  }

  // Group by (lat, lng) for clustering display
  const grouped = new Map<string, MapLocation[]>()
  for (const loc of locs) {
    const key = `${loc.lat},${loc.lng}`
    if (!grouped.has(key)) grouped.set(key, [])
    grouped.get(key)!.push(loc)
  }

  for (const group of grouped.values()) {
    const first = group[0]
    if (localMarkers.has(first.id)) continue

    const count = group.length

    const countLabel = count > 1
      ? `<text x="12" y="14.5" text-anchor="middle" font-size="7" font-weight="800" fill="#1d4ed8">${count}</text>`
      : ''
    const icon = L.divIcon({
      className: '',
      html: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="32" viewBox="0 0 24 32" class="map-pin">
        <path d="M12 0C5.37 0 0 5.37 0 12c0 8 12 20 12 20S24 20 24 12C24 5.37 18.63 0 12 0z"/>
        <circle cx="12" cy="11" r="${count > 1 ? 5.5 : 4.5}" fill="white" fill-opacity="0.92"/>
        ${countLabel}
      </svg>`,
      iconSize: [24, 32],
      iconAnchor: [12, 32],
    })

    const marker = L.marker([first.lat, first.lng], { icon }).addTo(map)
    marker.on('click', () => openDrawer(group))
    gmap.registerMarker(marker)
    localMarkers.set(first.id, marker)
  }
}

// ── Drawer ────────────────────────────────────────────────────────────────────
async function openDrawer(group: MapLocation[]) {
  const loc = group[0]
  drawerLocationName.value = loc.name
  drawerItems.value = group
  drawerOpen.value = true
  drawerTab.value = 'place'
  placeData.value = null
  placeError.value = ''
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

function closeDrawer() {
  drawerOpen.value = false
}

// ── Actions ───────────────────────────────────────────────────────────────────
async function deleteLocation(loc: MapLocation) {
  await apiFetch(`/items/${loc.item_id}/locations/${loc.id}`, { method: 'DELETE' })
  locations.value = locations.value.filter(l => l.id !== loc.id)
  drawerItems.value = drawerItems.value.filter(l => l.id !== loc.id)
  if (drawerItems.value.length === 0) closeDrawer()
  const stillHas = locations.value.some(l => l.item_id === loc.item_id)
  if (!stillHas) {
    allLocatedItemIds.value = new Set([...allLocatedItemIds.value].filter(id => id !== loc.item_id))
  }
  await loadLocationsInBounds()
}

function openItem(itemId: string) {
  const { open } = useItemModal()
  open(itemId)
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────
const isMounted = ref(false)

onMounted(() => {
  isMounted.value = true
  setupMap()
})

onUnmounted(() => {
  isMounted.value = false
  gmap.release('home')
})

// Re-claim when modal releases the map
watch(gmap.currentOwner, async (owner) => {
  if (owner !== null || !isMounted.value) return
  await reclaimMap()
})
</script>

<template>
  <div class="map-view">
    <!-- Loading state -->
    <div v-if="loadingMap" class="map-loading">
      <span>地圖載入中…</span>
    </div>

    <!-- Error -->
    <div v-if="errorMsg" class="map-error">{{ errorMsg }}</div>

    <!-- Map container slot — the global containerEl will be appended here -->
    <div ref="mapContainer" class="map-container" />

    <!-- Location drawer -->
    <Transition name="drawer">
      <div v-if="drawerOpen" class="map-drawer">

        <!-- Header -->
        <div class="map-drawer__header">
          <h3 class="map-drawer__title">{{ drawerLocationName }}</h3>
          <button class="map-drawer__close" @click="closeDrawer">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- Tabs -->
        <div class="map-drawer__tabs">
          <button
            class="map-drawer__tab"
            :class="{ 'map-drawer__tab--active': drawerTab === 'place' }"
            @click="drawerTab = 'place'"
          >地點資訊</button>
          <button
            class="map-drawer__tab"
            :class="{ 'map-drawer__tab--active': drawerTab === 'items' }"
            @click="drawerTab = 'items'"
          >知識 ({{ drawerItems.length }})</button>
        </div>

        <!-- ── Tab: 地點資訊 ── -->
        <div v-if="drawerTab === 'place'" class="map-drawer__place">
          <PlaceInfoPanel
            :place-data="placeData"
            :place-loading="placeLoading"
            :place-error="placeError"
          />
        </div>

        <!-- ── Tab: 知識 ── -->
        <div v-if="drawerTab === 'items'" class="map-drawer__items">
          <div v-for="loc in drawerItems" :key="loc.id" class="map-drawer__item">
            <div class="map-drawer__item-card" @click="openItem(loc.item_id)">
              <img v-if="loc.item_thumbnail" :src="loc.item_thumbnail" class="map-drawer__item-thumb" alt="" />
              <div v-else class="map-drawer__item-thumb map-drawer__item-thumb--empty" />
              <div class="map-drawer__item-body">
                <span class="map-drawer__item-title">{{ loc.item_title || '（無標題）' }}</span>
                <span class="map-drawer__item-meta">
                  <span class="map-drawer__badge" :class="`map-drawer__badge--${loc.source}`">
                    {{ loc.source === 'metadata' ? 'metadata' : 'AI' }}
                  </span>
                </span>
              </div>
            </div>
            <div class="map-drawer__item-actions">
              <button
                class="map-drawer__action map-drawer__action--delete"
                @click.stop="deleteLocation(loc)"
              >刪除</button>
            </div>
          </div>
        </div>

      </div>
    </Transition>

    <!-- No-location items section -->
    <div v-if="noLocationItems.length > 0" class="map-no-location">
      <div class="map-no-location__header">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="10" r="3"/><path d="M12 2a8 8 0 0 0-8 8c0 5.25 8 14 8 14s8-8.75 8-14a8 8 0 0 0-8-8z"/></svg>
        <span>{{ noLocationItems.length }} 筆內容尚無地點資訊</span>
      </div>
      <div class="map-no-location__list">
        <div v-for="item in noLocationItems.slice(0, 20)" :key="item.id" class="map-no-location__row">
          <img v-if="item.thumbnail_url" :src="item.thumbnail_url" class="map-no-location__thumb" alt="" />
          <div v-else class="map-no-location__thumb map-no-location__thumb--empty" />
          <span class="map-no-location__name">{{ item.title || '（無標題）' }}</span>
          <button
            class="map-no-location__extract"
            :disabled="extractingIds.has(item.id)"
            @click="extractLocations(item.id)"
          >
            {{ extractingIds.has(item.id) ? '抽取中…' : '補抓地點' }}
          </button>
        </div>
        <p v-if="noLocationItems.length > 20" class="map-no-location__more">
          還有 {{ noLocationItems.length - 20 }} 筆…
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.map-view {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 500px;
}

.map-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
  z-index: 10;
  font-size: 14px;
  color: var(--text-mid);
}

.map-error {
  padding: 10px 14px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.25);
  border-radius: 8px;
  font-size: 13px;
  color: #dc2626;
}

.map-container {
  width: 100%;
  height: 520px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--border);
  z-index: 0;
}

/* ── Drawer ── */
.map-drawer {
  position: absolute;
  top: 0;
  right: 0;
  width: 300px;
  max-height: 520px;
  overflow-y: auto;
  background: var(--bg);
  border: 1px solid var(--border2);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.14);
  z-index: 1000;
}

.map-drawer__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 14px 0;
}

.map-drawer__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  margin: 0;
  flex: 1;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.map-drawer__close {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-mid);
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  flex-shrink: 0;
  margin-left: 8px;
  transition: background 0.12s;
}
.map-drawer__close:hover { background: var(--surface2); }

/* ── Tabs ── */
.map-drawer__tabs {
  display: flex;
  padding: 10px 14px 0;
  gap: 4px;
  border-bottom: 1px solid var(--border);
}

.map-drawer__tab {
  font-size: 12.5px;
  font-weight: 500;
  padding: 6px 10px;
  border: none;
  background: none;
  cursor: pointer;
  color: var(--text-mid);
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: color 0.12s, border-color 0.12s;
}
.map-drawer__tab--active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

/* ── Place tab ── */
.map-drawer__place {
  padding: 12px 14px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* ── Items tab ── */
.map-drawer__items {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 8px 0 0;
}

.map-drawer__item {
  border-top: 1px solid var(--border);
  overflow: hidden;
}
.map-drawer__item:first-child { border-top: none; }

.map-drawer__item-card {
  display: flex;
  gap: 10px;
  padding: 10px 14px;
  cursor: pointer;
  transition: background 0.12s;
}
.map-drawer__item-card:hover { background: var(--surface2); }

.map-drawer__item-thumb {
  width: 52px;
  height: 52px;
  object-fit: cover;
  border-radius: 6px;
  flex-shrink: 0;
  background: var(--surface2);
}
.map-drawer__item-thumb--empty { background: var(--surface2); }

.map-drawer__item-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  min-width: 0;
}

.map-drawer__item-title {
  font-size: 12.5px;
  font-weight: 500;
  color: var(--text);
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.map-drawer__item-meta {
  display: flex;
  gap: 4px;
  align-items: center;
  flex-wrap: wrap;
}

.map-drawer__badge {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.map-drawer__badge--ai {
  background: var(--accent-dim);
  color: var(--accent);
  border: 1px solid var(--accent-bdr);
}
.map-drawer__badge--metadata {
  background: rgba(16, 185, 129, 0.1);
  color: #059669;
  border: 1px solid rgba(16, 185, 129, 0.25);
}
.map-drawer__item-actions {
  display: flex;
  gap: 6px;
  padding: 6px 14px;
  background: var(--surface2);
  border-top: 1px solid var(--border);
}

.map-drawer__action {
  font-size: 11.5px;
  font-weight: 500;
  padding: 4px 10px;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: opacity 0.12s;
}
.map-drawer__action:hover { opacity: 0.8; }

.map-drawer__action--delete {
  background: rgba(239, 68, 68, 0.08);
  color: #dc2626;
  border-color: rgba(239, 68, 68, 0.2);
}

/* ── No-location section ── */
.map-no-location {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
}

.map-no-location__header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-mid);
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
}

.map-no-location__list {
  display: flex;
  flex-direction: column;
  max-height: 240px;
  overflow-y: auto;
}

.map-no-location__row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  border-bottom: 1px solid var(--border);
}
.map-no-location__row:last-child { border-bottom: none; }

.map-no-location__thumb {
  width: 36px;
  height: 36px;
  border-radius: 5px;
  object-fit: cover;
  flex-shrink: 0;
}
.map-no-location__thumb--empty { background: var(--border); }

.map-no-location__name {
  flex: 1;
  font-size: 12.5px;
  color: var(--text);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.map-no-location__extract {
  font-size: 11.5px;
  font-weight: 500;
  padding: 4px 10px;
  border-radius: 6px;
  border: 1px solid var(--accent-bdr);
  background: var(--accent-dim);
  color: var(--accent);
  cursor: pointer;
  flex-shrink: 0;
  transition: opacity 0.12s;
  white-space: nowrap;
}
.map-no-location__extract:disabled { opacity: 0.5; cursor: not-allowed; }
.map-no-location__extract:not(:disabled):hover { opacity: 0.8; }

.map-no-location__more {
  font-size: 12px;
  color: var(--text-mid);
  padding: 8px 14px;
  margin: 0;
}

/* ── Drawer transition ── */
.drawer-enter-active,
.drawer-leave-active {
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.18s ease;
}
.drawer-enter-from,
.drawer-leave-to {
  transform: translateX(16px);
  opacity: 0;
}
</style>

<style>
/* Global: Leaflet marker overrides (must be unscoped) */
.map-pin {
  display: block;
  overflow: visible;
  cursor: pointer;
  filter: drop-shadow(0 2px 5px rgba(0,0,0,0.3));
  transition: transform 0.12s, filter 0.12s;
}
.map-pin:hover {
  transform: scale(1.18) translateY(-2px);
  filter: drop-shadow(0 4px 8px rgba(0,0,0,0.38));
}

.map-pin { fill: #3b82f6; }
.map-pin--search { fill: #f59e0b; }
</style>
