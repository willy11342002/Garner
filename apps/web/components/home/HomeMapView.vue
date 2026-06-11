<script setup lang="ts">
import type { Map as LeafletMap, Marker as LeafletMarker, LatLngBounds } from 'leaflet'

interface MapLocation {
  id: string
  name: string
  lat: number
  lng: number
  source: string
  confirmed: boolean
  content_id: string
  item_id: string
  item_title: string | null
  item_thumbnail: string | null
  item_source_type: string | null
}

const apiFetch = useApiFetch()
const itemStore = useItemStore()

// ── Map state ─────────────────────────────────────────────────────────────────
const mapContainer = ref<HTMLElement | null>(null)
let map: LeafletMap | null = null
let markers: Map<string, LeafletMarker> = new Map()

const locations = ref<MapLocation[]>([])
const allLocatedItemIds = ref<Set<string>>(new Set())
const loadingMap = ref(true)
const errorMsg = ref('')

// ── Drawer state ──────────────────────────────────────────────────────────────
const drawerOpen = ref(false)
const drawerLocationName = ref('')
const drawerItems = ref<MapLocation[]>([])

// ── No-location items ─────────────────────────────────────────────────────────
const noLocationItems = computed(() => {
  return itemStore.items.filter(
    item => !allLocatedItemIds.value.has(item.id) && item.status === 'active'
  )
})

const extractingIds = ref<Set<string>>(new Set())

async function extractLocations(itemId: string) {
  if (extractingIds.value.has(itemId)) return
  const s = new Set(extractingIds.value)
  s.add(itemId)
  extractingIds.value = s

  try {
    const locs = await apiFetch<Array<{ id: string; item_id?: string }>>(`/items/${itemId}/locations/extract`, { method: 'POST' })
    if (locs.length > 0) {
      const ids = new Set(allLocatedItemIds.value)
      ids.add(itemId)
      allLocatedItemIds.value = ids
      await loadLocationsInBounds()
    }
  } catch {}  finally {
    const s2 = new Set(extractingIds.value)
    s2.delete(itemId)
    extractingIds.value = s2
  }
}

// ── Map init ──────────────────────────────────────────────────────────────────
async function initMap() {
  if (!mapContainer.value) return

  const L = (await import('leaflet')).default
  await import('leaflet/dist/leaflet.css')

  // Fix default icon paths (Leaflet + bundler issue)
  delete (L.Icon.Default.prototype as any)._getIconUrl
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
    iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
    shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  })

  map = L.map(mapContainer.value, {
    center: [23.5, 121],  // center on Taiwan by default
    zoom: 7,
    zoomControl: true,
  })

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  }).addTo(map)

  map.on('moveend', loadLocationsInBounds)
  map.on('zoomend', loadLocationsInBounds)

  // Fetch all locations worldwide once to determine which items have locations
  try {
    const all = await apiFetch<MapLocation[]>('/locations?bounds=-90,-180,90,180')
    allLocatedItemIds.value = new Set(all.map(l => l.item_id))
  } catch {}

  await loadLocationsInBounds()
  loadingMap.value = false
}

// ── Fetch locations ───────────────────────────────────────────────────────────
async function loadLocationsInBounds() {
  if (!map) return

  const bounds: LatLngBounds = map.getBounds()
  const sw = bounds.getSouthWest()
  const ne = bounds.getNorthEast()
  const boundsParam = `${sw.lat},${sw.lng},${ne.lat},${ne.lng}`

  try {
    const data = await apiFetch<MapLocation[]>(`/locations?bounds=${boundsParam}`)
    locations.value = data
    updateMarkers(data)
  } catch (e) {
    errorMsg.value = '無法載入地點資料'
  }
}

// ── Markers ───────────────────────────────────────────────────────────────────
async function updateMarkers(locs: MapLocation[]) {
  if (!map) return
  const L = (await import('leaflet')).default

  // Remove old markers not in the new set
  const newIds = new Set(locs.map(l => l.id))
  for (const [id, marker] of markers) {
    if (!newIds.has(id)) {
      marker.remove()
      markers.delete(id)
    }
  }

  // Group by (lat, lng) for clustering
  const grouped = new Map<string, MapLocation[]>()
  for (const loc of locs) {
    const key = `${loc.lat},${loc.lng}`
    if (!grouped.has(key)) grouped.set(key, [])
    grouped.get(key)!.push(loc)
  }

  // Add new markers
  for (const group of grouped.values()) {
    const first = group[0]
    const key = first.id

    if (markers.has(key)) continue  // already on map

    const isConfirmed = group.every(l => l.confirmed)
    const count = group.length

    // Custom icon based on confirmation status and cluster count
    const icon = L.divIcon({
      className: '',
      html: `<div class="map-marker ${isConfirmed ? 'map-marker--confirmed' : 'map-marker--pending'}">${count > 1 ? count : ''}</div>`,
      iconSize: [32, 32],
      iconAnchor: [16, 16],
    })

    const marker = L.marker([first.lat!, first.lng!], { icon }).addTo(map!)
    marker.on('click', () => openDrawer(group))
    markers.set(key, marker)
  }
}

// ── Drawer ────────────────────────────────────────────────────────────────────
function openDrawer(group: MapLocation[]) {
  drawerLocationName.value = group[0].name
  drawerItems.value = group
  drawerOpen.value = true
}

function closeDrawer() {
  drawerOpen.value = false
}

// ── Actions ───────────────────────────────────────────────────────────────────
async function confirmLocation(loc: MapLocation) {
  await apiFetch(`/items/${loc.item_id}/locations/${loc.id}`, {
    method: 'PATCH',
    body: { confirmed: true },
  })
  loc.confirmed = true
  await loadLocationsInBounds()
}

async function deleteLocation(loc: MapLocation) {
  await apiFetch(`/items/${loc.item_id}/locations/${loc.id}`, { method: 'DELETE' })
  locations.value = locations.value.filter(l => l.id !== loc.id)
  drawerItems.value = drawerItems.value.filter(l => l.id !== loc.id)
  if (drawerItems.value.length === 0) closeDrawer()
  // Re-check if the item still has any locations
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
onMounted(initMap)

onUnmounted(() => {
  map?.remove()
  map = null
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

    <!-- Map container -->
    <div ref="mapContainer" class="map-container" />

    <!-- Location drawer -->
    <Transition name="drawer">
      <div v-if="drawerOpen" class="map-drawer">
        <div class="map-drawer__header">
          <h3 class="map-drawer__title">{{ drawerLocationName }}</h3>
          <button class="map-drawer__close" @click="closeDrawer">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <div class="map-drawer__items">
          <div
            v-for="loc in drawerItems"
            :key="loc.id"
            class="map-drawer__item"
          >
            <div class="map-drawer__item-card" @click="openItem(loc.item_id)">
              <img
                v-if="loc.item_thumbnail"
                :src="loc.item_thumbnail"
                class="map-drawer__item-thumb"
                alt=""
              />
              <div v-else class="map-drawer__item-thumb map-drawer__item-thumb--empty" />
              <div class="map-drawer__item-body">
                <span class="map-drawer__item-title">{{ loc.item_title || '（無標題）' }}</span>
                <span class="map-drawer__item-meta">
                  <span class="map-drawer__badge" :class="`map-drawer__badge--${loc.source}`">
                    {{ loc.source === 'metadata' ? 'metadata' : 'AI' }}
                  </span>
                  <span v-if="!loc.confirmed" class="map-drawer__badge map-drawer__badge--pending">未確認</span>
                </span>
              </div>
            </div>
            <div class="map-drawer__item-actions">
              <button
                v-if="!loc.confirmed"
                class="map-drawer__action map-drawer__action--confirm"
                title="確認此地點"
                @click.stop="confirmLocation(loc)"
              >確認</button>
              <button
                class="map-drawer__action map-drawer__action--delete"
                title="刪除此地點"
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
        <div
          v-for="item in noLocationItems.slice(0, 20)"
          :key="item.id"
          class="map-no-location__row"
        >
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
  padding: 16px;
}

.map-drawer__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.map-drawer__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  margin: 0;
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
  transition: background 0.12s;
}
.map-drawer__close:hover { background: var(--surface2); }

.map-drawer__items {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.map-drawer__item {
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}

.map-drawer__item-card {
  display: flex;
  gap: 10px;
  padding: 10px;
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
.map-drawer__item-thumb--empty {
  background: var(--surface2);
}

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
.map-drawer__badge--pending {
  background: rgba(234, 179, 8, 0.1);
  color: #b45309;
  border: 1px solid rgba(234, 179, 8, 0.25);
}

.map-drawer__item-actions {
  display: flex;
  gap: 6px;
  padding: 6px 10px;
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

.map-drawer__action--confirm {
  background: var(--accent-dim);
  color: var(--accent);
  border-color: var(--accent-bdr);
}

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
  background: var(--surface2);
}
.map-no-location__thumb--empty {
  background: var(--border);
}

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
.map-no-location__extract:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
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
/* Global: Leaflet marker overrides (unscoped) */
.map-marker {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  border: 2px solid white;
  box-shadow: 0 2px 6px rgba(0,0,0,0.25);
  transition: transform 0.12s;
  cursor: pointer;
}
.map-marker:hover { transform: scale(1.15); }

.map-marker--confirmed {
  background: #3b82f6;
  color: white;
}

.map-marker--pending {
  background: rgba(59, 130, 246, 0.45);
  color: white;
}
</style>
