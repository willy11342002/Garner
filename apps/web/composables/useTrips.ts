import type {
  Trip,
  TripCreate,
  TripItem,
  TripItemCreate,
  TripItemReorderRequest,
  TripItemUpdate,
  TripListItem,
  TripTag,
  TripTagCreate,
  TripTagUpdate,
  TripUpdate,
} from '~/types/api'

export function useTrips() {
  const apiFetch = useApiFetch()

  async function listTrips(): Promise<TripListItem[]> {
    return apiFetch<TripListItem[]>('/trips/')
  }

  async function getTrip(id: string): Promise<Trip> {
    return apiFetch<Trip>(`/trips/${id}`)
  }

  async function createTrip(data: TripCreate): Promise<Trip> {
    return apiFetch<Trip>('/trips/', { method: 'POST', body: data })
  }

  async function updateTrip(id: string, data: TripUpdate): Promise<Trip> {
    return apiFetch<Trip>(`/trips/${id}`, { method: 'PATCH', body: data })
  }

  async function deleteTrip(id: string): Promise<void> {
    await apiFetch(`/trips/${id}`, { method: 'DELETE' })
  }

  // ── Items ──────────────────────────────────────────────────────────────────

  async function addItem(tripId: string, data: TripItemCreate): Promise<TripItem> {
    return apiFetch<TripItem>(`/trips/${tripId}/items`, { method: 'POST', body: data })
  }

  async function updateItem(tripId: string, itemId: string, data: TripItemUpdate): Promise<TripItem> {
    return apiFetch<TripItem>(`/trips/${tripId}/items/${itemId}`, { method: 'PATCH', body: data })
  }

  async function deleteItem(tripId: string, itemId: string): Promise<void> {
    await apiFetch(`/trips/${tripId}/items/${itemId}`, { method: 'DELETE' })
  }

  async function reorderItems(tripId: string, data: TripItemReorderRequest): Promise<void> {
    await apiFetch(`/trips/${tripId}/items/reorder`, { method: 'PATCH', body: data })
  }

  // ── Tags ───────────────────────────────────────────────────────────────────

  async function listTags(): Promise<TripTag[]> {
    return apiFetch<TripTag[]>('/trip-tags/')
  }

  async function createTag(data: TripTagCreate): Promise<TripTag> {
    return apiFetch<TripTag>('/trip-tags/', { method: 'POST', body: data })
  }

  async function updateTag(id: string, data: TripTagUpdate): Promise<TripTag> {
    return apiFetch<TripTag>(`/trip-tags/${id}`, { method: 'PATCH', body: data })
  }

  async function deleteTag(id: string): Promise<void> {
    await apiFetch(`/trip-tags/${id}`, { method: 'DELETE' })
  }

  return {
    listTrips,
    getTrip,
    createTrip,
    updateTrip,
    deleteTrip,
    addItem,
    updateItem,
    deleteItem,
    reorderItems,
    listTags,
    createTag,
    updateTag,
    deleteTag,
  }
}
