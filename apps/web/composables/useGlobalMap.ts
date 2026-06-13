import type { Map as LeafletMap, Marker as LeafletMarker } from 'leaflet'

// ── Module-level singleton ────────────────────────────────────────────────────
// All state lives outside the composable function so it persists across
// component lifecycles for the entire browser session.

let leaflet: typeof import('leaflet')['default'] | null = null
let mapInstance: LeafletMap | null = null
let containerEl: HTMLElement | null = null
let initPromise: Promise<void> | null = null

const currentOwner = ref<string | null>(null)
const locationVersion = ref(0)
const markerRegistry = new Set<LeafletMarker>()
const activeListenerCleanups: Array<() => void> = []

function clearActiveListeners() {
  for (const fn of activeListenerCleanups) fn()
  activeListenerCleanups.length = 0
}

function clearAllMarkers() {
  for (const m of markerRegistry) m.remove()
  markerRegistry.clear()
}

function getOrCreateParking(): HTMLElement {
  let el = document.getElementById('gmap-parking')
  if (!el) {
    el = document.createElement('div')
    el.id = 'gmap-parking'
    // Off-screen but with real dimensions so Leaflet initialises without errors
    el.style.cssText = 'position:fixed;top:-9000px;left:-9000px;width:800px;height:600px;pointer-events:none;visibility:hidden;'
    document.body.appendChild(el)
  }
  return el
}

function ensureInit(): Promise<void> {
  if (!initPromise) initPromise = _init()
  return initPromise
}

async function _init() {
  if (!import.meta.client) return

  const parking = getOrCreateParking()
  containerEl = document.createElement('div')
  containerEl.style.cssText = 'width:100%;height:100%;'
  parking.appendChild(containerEl)

  const L = (await import('leaflet')).default
  await import('leaflet/dist/leaflet.css')
  leaflet = L

  // Fix default icon paths broken by bundlers
  delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
    iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
    shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  })

  mapInstance = L.map(containerEl, { center: [23.5, 121], zoom: 7 })
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  }).addTo(mapInstance)
}

// ── Public composable ─────────────────────────────────────────────────────────
export function useGlobalMap() {
  /**
   * Physically move the map container into `targetEl` and take ownership.
   * Clears all previous markers and event listeners automatically.
   */
  async function claim(targetEl: HTMLElement, owner: string) {
    await ensureInit()
    clearActiveListeners()
    clearAllMarkers()
    currentOwner.value = owner
    targetEl.appendChild(containerEl!)
    await nextTick()
    mapInstance!.invalidateSize()
  }

  /**
   * Move the container back to the off-screen parking slot and relinquish
   * ownership. No-op if the caller is not the current owner.
   */
  function release(owner: string) {
    if (currentOwner.value !== owner) return
    clearActiveListeners()
    currentOwner.value = null
    const parking = getOrCreateParking()
    if (containerEl) parking.appendChild(containerEl)
  }

  /** Register a moveend+zoomend listener that is auto-removed on next claim. */
  function onMoveEnd(handler: () => void) {
    if (!mapInstance) return
    mapInstance.on('moveend', handler)
    mapInstance.on('zoomend', handler)
    activeListenerCleanups.push(() => {
      mapInstance!.off('moveend', handler)
      mapInstance!.off('zoomend', handler)
    })
  }

  /** Track a marker so clearAllMarkers() can clean it up. */
  function registerMarker(marker: LeafletMarker): LeafletMarker {
    markerRegistry.add(marker)
    return marker
  }

  /** Remove a specific marker from both Leaflet and the registry. */
  function removeMarker(marker: LeafletMarker) {
    markerRegistry.delete(marker)
    marker.remove()
  }

  return {
    /** Reactive — watch this to know when another component has taken the map. */
    currentOwner: readonly(currentOwner),
    /** Increment to signal that locations have changed and map should refresh. */
    locationVersion: readonly(locationVersion),
    notifyLocationChange: () => { locationVersion.value++ },
    claim,
    release,
    onMoveEnd,
    clearAllMarkers,
    registerMarker,
    removeMarker,
    getMap: () => mapInstance,
    getL: () => leaflet,
  }
}
