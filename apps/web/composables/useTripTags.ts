/**
 * 旅遊行程的標籤目錄：清單、重新命名、刪除、看板欄位的拖曳排序與新增。
 *
 * 從 pages/app/trips.vue 抽出來。標籤同時被「看板欄位」與「卡片編輯器」使用，
 * 所以 availableTags 由這裡持有，兩邊共用同一份。
 *
 * 排序只存在 localStorage（後端沒有欄位），因此每次載入標籤後要呼叫
 * `applyStoredTagOrder()`，任何會改變順序或增刪的操作都要呼叫 `saveTagOrder()`。
 *
 * 卡片編輯器裡的「行內新增標籤」沒有放進來：它除了建立標籤還要把新標籤掛到
 * 當前卡片並觸發 PATCH，橫跨兩個關注點，留在頁面當薄薄的橋接層。
 */

import type { Ref } from 'vue'
import type { Trip, TripItem, TripTag } from '~/types/api'

const TAG_ORDER_KEY = 'trips:tagOrder'

export function useTripTags(current: Ref<Trip | null>) {
  const { t } = useI18n()
  const { updateTag, deleteTag, createTag } = useTrips()

  const availableTags = ref<TripTag[]>([])

  // ── 排序（僅存 localStorage）──────────────────────────────────────────────
  function loadTagOrder(): string[] {
    try {
      const raw = localStorage.getItem(TAG_ORDER_KEY)
      const parsed = raw ? JSON.parse(raw) : []
      return Array.isArray(parsed) ? parsed : []
    } catch {
      return []
    }
  }

  function saveTagOrder() {
    try {
      localStorage.setItem(TAG_ORDER_KEY, JSON.stringify(availableTags.value.map(t => t.id)))
    } catch { /* ignore */ }
  }

  function applyStoredTagOrder() {
    const order = loadTagOrder()
    if (!order.length) return
    availableTags.value.sort((a, b) => {
      const ia = order.indexOf(a.id)
      const ib = order.indexOf(b.id)
      if (ia === -1 && ib === -1) return 0
      if (ia === -1) return 1   // 未記錄的（新標籤）排最後
      if (ib === -1) return -1
      return ia - ib
    })
  }

  // ── 重新命名 ─────────────────────────────────────────────────────────────
  const editingTagId = ref<string | null>(null)
  const editingTagName = ref('')
  const tagEditInput = ref<HTMLInputElement | null>(null)

  function startEditTag(tagId: string, name: string) {
    editingTagId.value = tagId
    editingTagName.value = name
    nextTick(() => { tagEditInput.value?.select() })
  }

  async function finishEditTag(tagId: string) {
    if (editingTagId.value === null) return  // cancelled
    const newName = editingTagName.value.trim()
    editingTagId.value = null
    if (!newName) return
    const tag = availableTags.value.find(t => t.id === tagId)
    if (!tag || newName === tag.name) return
    const prevName = tag.name
    tag.name = newName
    try {
      await updateTag(tagId, { name: newName })
    } catch {
      tag.name = prevName
    }
  }

  function cancelEditTag(e: KeyboardEvent) {
    editingTagId.value = null
    ;(e.target as HTMLElement).blur()
  }

  // ── 刪除 ─────────────────────────────────────────────────────────────────
  async function handleDeleteTag(tagId: string, name: string) {
    if (!confirm(t('trips.confirm.deleteTag', { name }))) return
    const idx = availableTags.value.findIndex(t => t.id === tagId)
    if (idx === -1) return
    const removed = availableTags.value[idx]
    availableTags.value.splice(idx, 1)
    // 同步把此標籤從目前行程的卡片上移除（後端 delete 會 cascade）
    const detached: Array<{ item: TripItem; pos: number; tag: TripItem['tags'][number] }> = []
    for (const item of current.value?.items ?? []) {
      const ti = item.tags.findIndex(t => t.trip_tag_id === tagId)
      if (ti !== -1) {
        detached.push({ item, pos: ti, tag: item.tags[ti] })
        item.tags.splice(ti, 1)
      }
    }
    saveTagOrder()
    try {
      await deleteTag(tagId)
    } catch {
      availableTags.value.splice(idx, 0, removed)
      for (const d of detached) d.item.tags.splice(d.pos, 0, d.tag)
      saveTagOrder()
    }
  }

  // ── 看板欄位拖曳排序 ──────────────────────────────────────────────────────
  const dragTagId = ref<string | null>(null)
  const dragOverTagId = ref<string | null>(null)

  function onTagDragStart(tagId: string, e: DragEvent) {
    if (tagId === '__none__' || editingTagId.value === tagId) return
    dragTagId.value = tagId
    if (e.dataTransfer) {
      e.dataTransfer.effectAllowed = 'move'
      e.dataTransfer.setData('text/plain', tagId)
    }
  }

  function onTagDragEnd() {
    dragTagId.value = null
    dragOverTagId.value = null
  }

  function onTagDrop(targetId: string) {
    const fromId = dragTagId.value
    dragTagId.value = null
    dragOverTagId.value = null
    if (!fromId || fromId === targetId) return
    const arr = availableTags.value
    const fromIdx = arr.findIndex(t => t.id === fromId)
    const toIdx = arr.findIndex(t => t.id === targetId)
    if (fromIdx === -1 || toIdx === -1) return
    const [moved] = arr.splice(fromIdx, 1)
    arr.splice(toIdx, 0, moved)
    saveTagOrder()
  }

  // ── 看板新增欄位 ──────────────────────────────────────────────────────────
  const addingBoardTag = ref(false)
  const boardTagName = ref('')
  const boardTagInputEl = ref<HTMLInputElement | null>(null)

  function startAddBoardTag() {
    addingBoardTag.value = true
    boardTagName.value = ''
    nextTick(() => boardTagInputEl.value?.focus())
  }

  async function confirmBoardTag() {
    const name = boardTagName.value.trim()
    addingBoardTag.value = false
    boardTagName.value = ''
    if (!name) return
    const tempId = `temp-${Date.now()}`
    availableTags.value.push({ id: tempId, name, color: null })
    try {
      const tag = await createTag({ name })
      const idx = availableTags.value.findIndex(t => t.id === tempId)
      if (idx !== -1) availableTags.value[idx] = tag
    } catch {
      availableTags.value = availableTags.value.filter(t => t.id !== tempId)
    }
  }

  function cancelBoardTag(e: KeyboardEvent) {
    addingBoardTag.value = false
    boardTagName.value = ''
    ;(e.target as HTMLElement).blur()
  }

  return {
    availableTags,
    applyStoredTagOrder,
    saveTagOrder,
    // rename
    editingTagId, editingTagName, tagEditInput,
    startEditTag, finishEditTag, cancelEditTag,
    // delete
    handleDeleteTag,
    // drag-reorder
    dragTagId, dragOverTagId,
    onTagDragStart, onTagDragEnd, onTagDrop,
    // board add
    addingBoardTag, boardTagName, boardTagInputEl,
    startAddBoardTag, confirmBoardTag, cancelBoardTag,
  }
}
