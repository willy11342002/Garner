/**
 * 旅遊行程的卡片編輯器：表單狀態與「每個欄位各自 PATCH」的自動儲存。
 *
 * 從 pages/app/trips.vue 抽出來。這裡沒有儲存按鈕——每個欄位變更就送一次 PATCH，
 * 並先做樂觀更新、失敗再回滾。備註欄打字頻繁，去抖動 700ms，離開卡片時 flush。
 *
 * 需要頁面的三個 ref：
 * - `current`：目前開啟的行程（卡片就住在 current.items 裡）
 * - `trips`：左側清單，新增／刪除卡片時要同步該行程的 item_count
 * - `availableTags`：標籤目錄，儲存標籤時要組樂觀更新用的資料
 */

import type { Ref } from 'vue'
import type { Trip, TripItem, TripListItem, TripTag } from '~/types/api'

export interface EditForm {
  title: string
  emoji: string
  booked: boolean
  ticket_url: string
  start_date: string
  end_date: string
  start_time: string
  end_time: string
  place_name: string
  note: string
  tag_ids: string[]
}

type SaveKey = 'title' | 'emoji' | 'booked' | 'ticket_url' | 'place_name'
  | 'start_date' | 'end_date' | 'start_time' | 'end_time' | 'note'

export function useTripItemEditor(
  current: Ref<Trip | null>,
  trips: Ref<TripListItem[]>,
  availableTags: Ref<TripTag[]>,
) {
  const { t } = useI18n()
  const { addItem, updateItem, deleteItem } = useTrips()

  /** 把 API 錯誤轉成看得懂的訊息：後端有給 detail 就用它，否則依 status 分類。 */
  function errorText(err: unknown, fallbackKey: string): string {
    const { kind, detail } = classifyApiError(err, 'trips')
    return detail ?? (kind === 'unknown' ? t(fallbackKey) : t(API_ERROR_I18N_KEYS[kind]))
  }

  const editingItem = ref<Partial<TripItem> | null>(null)
  const isSaving = ref(false)
  const editingPlace = ref(false)  // 地標：有值時預設顯示「開啟地圖」按鈕，按編輯才切成 input
  const editingTicket = ref(false) // 票券連結：同地標的切換行為
  const editForm = ref<EditForm>({
    title: '', emoji: '', booked: false, ticket_url: '',
    start_date: '', end_date: '', start_time: '', end_time: '',
    place_name: '', note: '', tag_ids: [],
  })

  // populateForm 期間抑制自動儲存，避免載入卡片時誤觸 PATCH
  const suppressAutoSave = ref(false)

  function populateForm(item: Partial<TripItem>) {
    suppressAutoSave.value = true
    editingPlace.value = false   // 有地標就先顯示按鈕
    editingTicket.value = false  // 有票券連結就先顯示按鈕
    editForm.value = {
      title: item.title ?? '',
      emoji: item.emoji ?? '',
      booked: item.booked ?? false,
      ticket_url: item.ticket_url ?? '',
      start_date: item.start_date ?? '',
      end_date: item.end_date ?? '',
      start_time: item.start_time ?? '',
      end_time: item.end_time ?? '',
      place_name: item.place_name ?? '',
      note: item.note ?? '',
      tag_ids: (item.tags ?? []).map(t => t.trip_tag_id),
    }
    nextTick(() => { suppressAutoSave.value = false })
  }

  function openItemEditor(item: TripItem) {
    editingItem.value = item
    populateForm(item)
  }

  /** 左側行程清單的卡片數。新增／刪除卡片時要同步。 */
  function sidebarItemCount(tripId: string, delta: number) {
    const idx = trips.value.findIndex(t => t.id === tripId)
    if (idx !== -1) trips.value[idx].item_count += delta
  }

  // 新增：直接建立一張空白卡片再開編輯（無儲存按鈕，後續編輯各自 PATCH）
  async function handleAddItem() {
    if (!current.value) return
    const tripId = current.value.id
    try {
      const created = await addItem(tripId, { title: t('trips.defaultItemName'), order_index: current.value.items.length })
      current.value.items.push(created)
      sidebarItemCount(tripId, 1)
      openItemEditor(created)
    } catch (err) {
      useToast().show(errorText(err, 'trips.addFailed'), 'error')
    }
  }

  // ── 自動儲存：每個欄位變更各自發送 PATCH ───────────────────────────────────
  async function patchField(patch: Record<string, unknown>, optimistic: Partial<TripItem>) {
    if (!current.value || !editingItem.value?.id) return
    const tripId = current.value.id
    const itemId = editingItem.value.id
    const idx = current.value.items.findIndex(i => i.id === itemId)
    if (idx === -1) return
    const prev = { ...current.value.items[idx] }
    current.value.items[idx] = { ...current.value.items[idx], ...optimistic }
    if (editingItem.value?.id === itemId) editingItem.value = current.value.items[idx]
    try {
      const updated = await updateItem(tripId, itemId, patch)
      const i2 = current.value.items.findIndex(i => i.id === itemId)
      if (i2 !== -1) current.value.items[i2] = updated
      if (editingItem.value?.id === itemId) editingItem.value = updated
    } catch (err) {
      const i2 = current.value.items.findIndex(i => i.id === itemId)
      if (i2 !== -1) current.value.items[i2] = prev
      if (editingItem.value?.id === itemId) editingItem.value = prev
      // 之前這裡不分青紅皂白顯示「儲存失敗，已復原」，把 422 / 500 / 斷網
      // 全部壓成同一句，使用者與開發者都拿不到線索。
      useToast().show(errorText(err, 'trips.saveFailed'), 'error')
    }
  }

  function saveField(key: SaveKey) {
    if (suppressAutoSave.value) return
    let value: unknown = editForm.value[key]
    if (key === 'title') {
      value = (value as string).trim() || t('trips.defaultItemName')
      editForm.value.title = value as string
    } else if (typeof value === 'string') {
      value = value || null
    }
    patchField({ [key]: value }, { [key]: value } as Partial<TripItem>)
  }

  function saveTags() {
    if (suppressAutoSave.value) return
    const optimisticTags = availableTags.value
      .filter(t => editForm.value.tag_ids.includes(t.id))
      .map(t => ({ trip_tag_id: t.id, name: t.name, color: t.color }))
    patchField({ tag_ids: [...editForm.value.tag_ids] }, { tags: optimisticTags })
  }

  function onTitleCommit() { saveField('title') }
  function commitPlace() { editingPlace.value = false; saveField('place_name') }
  function commitTicket() { editingTicket.value = false; saveField('ticket_url') }

  // 備註打字頻繁：去抖動後再送，離開卡片時 flush
  let noteTimer: ReturnType<typeof setTimeout> | null = null
  function flushNoteSave() {
    if (noteTimer) { clearTimeout(noteTimer); noteTimer = null; saveField('note') }
  }
  watch(() => editForm.value.note, () => {
    if (suppressAutoSave.value) return
    if (noteTimer) clearTimeout(noteTimer)
    noteTimer = setTimeout(() => { noteTimer = null; saveField('note') }, 700)
  })

  async function handleDeleteItem() {
    if (!current.value || !editingItem.value?.id || isSaving.value) return
    if (!confirm(t('trips.confirm.deleteCard'))) return
    const tripId = current.value.id
    const itemId = editingItem.value.id
    const itemIdx = current.value.items.findIndex(i => i.id === itemId)
    const removed = itemIdx !== -1 ? current.value.items[itemIdx] : null
    if (itemIdx !== -1) current.value.items.splice(itemIdx, 1)
    sidebarItemCount(tripId, -1)
    closeEditor()
    try {
      await deleteItem(tripId, itemId)
    } catch {
      if (removed && itemIdx !== -1) current.value.items.splice(itemIdx, 0, removed)
      sidebarItemCount(tripId, 1)
    }
  }

  function toggleTag(tagId: string) {
    const ids = editForm.value.tag_ids
    const idx = ids.indexOf(tagId)
    if (idx === -1) ids.push(tagId)
    else ids.splice(idx, 1)
    saveTags()
  }

  /**
   * 關閉編輯器。會先 flush 尚未送出的備註，所以打到一半關掉不會掉資料。
   * 呼叫端若還有自己的收尾（例如關掉 emoji 選擇器）請在外面接著做。
   */
  function closeEditor(): Promise<void> {
    flushNoteSave()
    editingItem.value = null
    return nextTick()
  }

  return {
    editingItem,
    isSaving,
    editingPlace,
    editingTicket,
    editForm,
    populateForm,
    openItemEditor,
    handleAddItem,
    sidebarItemCount,
    saveField,
    saveTags,
    onTitleCommit,
    commitPlace,
    commitTicket,
    flushNoteSave,
    handleDeleteItem,
    toggleTag,
    closeEditor,
  }
}
