<template>
  <div class="trips-app">
    <!-- ===== Sidebar ===== -->
    <aside class="trips-side">
      <div class="trips-side__head">
        <span class="trips-side__lbl">旅遊行程</span>
        <span class="trips-side__count">{{ trips.length }}</span>
        <button class="trips-side__newbtn" title="新增行程" :disabled="creating" @click="handleCreate">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
        </button>
      </div>
      <div class="trips-rlist">
        <div v-if="loadingList" class="trips-rlist__loading">載入中…</div>
        <div v-else-if="trips.length === 0" class="trips-rlist__empty">還沒有行程，點 + 開始規劃</div>
        <button
          v-for="t in trips"
          :key="t.id"
          class="trips-ritem"
          :class="{ 'is-active': selectedId === t.id }"
          @click="select(t.id)"
        >
          <h3 class="trips-ritem__title">{{ t.title }}</h3>
          <p v-if="t.summary" class="trips-ritem__desc">{{ t.summary }}</p>
          <div class="trips-ritem__meta">
            <span v-if="t.start_date" class="trips-ritem__date">{{ formatDateRange(t.start_date, t.end_date) }}</span>
            <span class="trips-ritem__count">{{ t.item_count }} 項</span>
          </div>
        </button>
      </div>
    </aside>

    <!-- ===== Main ===== -->
    <main class="trips-main">
      <div v-if="!selectedId" class="trips-empty">
        <p>選擇左側行程，或點 + 建立新行程</p>
      </div>

      <template v-else-if="current">
        <div class="trips-scroll">
          <div class="trips-doc">

            <!-- Title row -->
            <div class="trips-doc__top">
              <div class="trips-doc__titlewrap">
                <h1
                  class="trips-doc__title"
                  contenteditable="true"
                  spellcheck="false"
                  ref="titleEl"
                  @blur="onTitleBlur"
                  @keydown.enter.prevent="($event.target as HTMLElement).blur()"
                >{{ current.title }}</h1>
                <div class="trips-doc__sub">
                  {{ current.items.length }} 項
                  <template v-if="current.start_date"> · {{ formatDateRange(current.start_date, current.end_date) }}</template>
                  <template v-if="current.sources.length">
                    · <button class="trips-doc__srcbtn" @click="sourcesOpen = true">從 {{ current.sources.length }} 則收藏彙整</button>
                  </template>
                </div>
              </div>
              <div class="trips-doc__actions">
                <button class="btn" @click="handleAddItem">+ 新增卡片</button>
                <button class="btn btn--danger" @click="handleDelete">刪除</button>
              </div>
            </div>

            <!-- View switcher -->
            <div class="trips-views">
              <button
                v-for="v in VIEWS"
                :key="v.key"
                class="trips-vtab"
                :class="{ 'is-active': activeView === v.key }"
                @click="activeView = v.key"
              >
                <span class="trips-vtab__n">{{ v.n }}</span>
                {{ v.label }}
              </button>
            </div>

            <!-- Board view (by tags) -->
            <div v-show="activeView === 'board'" class="trips-board">
              <div v-for="col in boardColumns" :key="col.id" class="trips-bcol">
                <div class="trips-bcol__head">
                  <!-- Editable tag name (only for real tags, not "無標籤") -->
                  <template v-if="col.id !== '__none__'">
                    <input
                      v-if="editingTagId === col.id"
                      :ref="el => { if (el) tagEditInput = el as HTMLInputElement }"
                      v-model="editingTagName"
                      class="trips-bcol__taginput"
                      @blur="finishEditTag(col.id)"
                      @keydown.enter.prevent="($event.target as HTMLElement).blur()"
                      @keydown.escape="cancelEditTag($event)"
                    />
                    <span
                      v-else
                      class="tag-chip"
                      :class="col.color ? `tag-chip--${col.color}` : 'tag-chip--plain'"
                      title="點擊重新命名"
                      @click="startEditTag(col.id, col.name)"
                    >{{ col.name }}</span>
                  </template>
                  <span v-else class="tag-chip tag-chip--plain">{{ col.name }}</span>
                  <span class="trips-colcount">{{ itemsByTag(col.id).length }}</span>
                </div>
                <div class="trips-bcol__cards">
                  <div
                    v-for="item in itemsByTag(col.id)"
                    :key="item.id"
                    class="trips-tcard"
                    @click="openItemEditor(item)"
                  >
                    <div class="trips-tcard__name">
                      <span v-if="item.emoji" class="trips-tcard__emoji">{{ item.emoji }}</span>
                      {{ item.title }}
                    </div>
                    <div class="trips-tcard__meta">
                      <span v-if="item.booked" class="trips-booked">✓ 已預定</span>
                      <span v-if="item.start_date" class="trips-tcard__time">{{ formatDateRange(item.start_date, item.end_date) }}</span>
                      <span v-if="item.start_time" class="trips-tcard__time">{{ item.start_time }}</span>
                      <a v-if="isUrl(item.place_name)" :href="item.place_name!" target="_blank" class="trips-tcard__place" @click.stop title="開啟地圖">📍</a>
                    </div>
                  </div>
                </div>
              </div>
              <!-- Add tag column -->
              <div class="trips-bcol trips-bcol--addtag">
                <div v-if="addingBoardTag" class="trips-bcol__head">
                  <input
                    ref="boardTagInputEl"
                    v-model="boardTagName"
                    class="trips-bcol__taginput"
                    placeholder="標籤名稱"
                    @blur="confirmBoardTag"
                    @keydown.enter.prevent="($event.target as HTMLElement).blur()"
                    @keydown.escape="cancelBoardTag($event)"
                  />
                </div>
                <button v-else class="trips-addcol-btn" @click="startAddBoardTag">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
                  新增標籤
                </button>
              </div>
            </div>

            <!-- Date view -->
            <div v-show="activeView === 'date'" class="trips-dboard">
              <div class="trips-dcol">
                <div class="trips-dcol__head">
                  <div class="trips-dcol__month">未排程</div>
                  <div class="trips-dcol__d" style="font-size:14px">無日期</div>
                </div>
                <div class="trips-dcol__cards">
                  <div
                    v-for="item in unscheduledItems"
                    :key="item.id"
                    class="trips-tcard"
                    @click="openItemEditor(item)"
                  >
                    <div class="trips-tcard__name">
                      <span v-if="item.emoji" class="trips-tcard__emoji">{{ item.emoji }}</span>
                      {{ item.title }}
                    </div>
                    <div class="trips-tcard__meta">
                      <span v-for="tag in item.tags" :key="tag.trip_tag_id" class="tag-chip tag-chip--plain" style="font-size:10px">{{ tag.name }}</span>
                      <span v-if="item.booked" class="trips-booked">✓ 已預定</span>
                    </div>
                  </div>
                  <div v-if="unscheduledItems.length === 0" class="trips-empty-note">—</div>
                </div>
              </div>
              <div v-for="day in tripDays" :key="day" class="trips-dcol">
                <div class="trips-dcol__head">
                  <div class="trips-dcol__month">{{ formatMonth(day) }}</div>
                  <div class="trips-dcol__date">
                    <span class="trips-dcol__d">{{ formatDay(day) }}</span>
                    <span class="trips-dcol__dow">{{ formatDow(day) }}</span>
                  </div>
                </div>
                <div class="trips-dcol__cards">
                  <div
                    v-for="item in itemsByDate(day)"
                    :key="item.id"
                    class="trips-tcard"
                    @click="openItemEditor(item)"
                  >
                    <div class="trips-tcard__name">
                      <span v-if="item.emoji" class="trips-tcard__emoji">{{ item.emoji }}</span>
                      {{ item.title }}
                    </div>
                    <div class="trips-tcard__meta">
                      <span v-if="item.booked" class="trips-booked">✓ 已預定</span>
                      <span v-if="item.start_time" class="trips-tcard__time">{{ item.start_time }}</span>
                      <a v-if="isUrl(item.place_name)" :href="item.place_name!" target="_blank" class="trips-tcard__place" @click.stop>📍</a>
                    </div>
                  </div>
                  <div v-if="itemsByDate(day).length === 0" class="trips-empty-note">— 自由活動 —</div>
                </div>
              </div>
            </div>

          </div>
        </div>
      </template>

      <div v-else-if="loadingDetail" class="trips-empty">載入中…</div>
    </main>

    <!-- ===== Item editor Modal ===== -->
    <Transition name="modal">
      <div v-if="editingItem !== null" class="trips-modal-overlay" @click.self="closeItemEditor">
        <div class="trips-modal">
          <div class="trips-modal__head">
            <button class="trips-modal__close" @click="closeItemEditor">✕</button>
          </div>
          <div class="trips-modal__body">

            <!-- Title + Emoji button on same row -->
            <div class="trips-field">
              <span class="trips-field__lbl">名稱</span>
              <div class="trips-titlerow">
                <button
                  ref="emojiTriggerEl"
                  class="trips-emoji-trigger"
                  type="button"
                  :title="editForm.emoji ? '更換 Emoji' : '選擇 Emoji'"
                  @click="toggleEmojiPicker"
                >{{ editForm.emoji || '😊' }}</button>
                <input v-model="editForm.title" class="trips-field__input" placeholder="景點名稱…" />
              </div>
            </div>

            <!-- Booked -->
            <label class="trips-field trips-field--inline">
              <input type="checkbox" v-model="editForm.booked" />
              <span class="trips-field__lbl">已預定票券</span>
            </label>

            <!-- Date + Time combined -->
            <div class="trips-field">
              <span class="trips-field__lbl">時間</span>
              <div class="trips-field__timerow">
                <input v-model="editForm.start_date" type="date" class="trips-field__input trips-field__dt" />
                <input v-model="editForm.start_time" type="time" class="trips-field__input trips-field__tm" />
                <span class="trips-field__sep">→</span>
                <input v-model="editForm.end_date" type="date" class="trips-field__input trips-field__dt" />
                <input v-model="editForm.end_time" type="time" class="trips-field__input trips-field__tm" />
              </div>
            </div>

            <!-- Place URL -->
            <label class="trips-field">
              <span class="trips-field__lbl">地標連結</span>
              <input
                v-model="editForm.place_name"
                type="url"
                class="trips-field__input"
                placeholder="https://maps.app.goo.gl/…"
              />
            </label>

            <!-- Tags -->
            <div class="trips-field">
              <span class="trips-field__lbl">標籤</span>
              <div class="trips-tags-wrap">
                <button
                  v-for="tag in availableTags"
                  :key="tag.id"
                  class="trips-pill"
                  :class="{ 'is-active': editForm.tag_ids.includes(tag.id) }"
                  @click="toggleTag(tag.id)"
                >{{ tag.name }}</button>
                <div v-if="addingTag" class="trips-newtag">
                  <input
                    ref="newTagInputEl"
                    v-model="newTagName"
                    class="trips-newtag__input"
                    placeholder="標籤名稱"
                    @keydown.enter="confirmNewTag"
                    @keydown.escape="cancelNewTag"
                    @blur="cancelNewTag"
                  />
                </div>
                <button v-else class="trips-pill" @click="startAddTag">+ 新標籤</button>
              </div>
            </div>

            <!-- Note (Tiptap) -->
            <div class="trips-field trips-field--note">
              <span class="trips-field__lbl">備註</span>
              <div class="trips-tiptap-wrap">
                <TiptapEditor v-model="editForm.note" />
              </div>
            </div>

          </div>

          <div class="trips-modal__foot">
            <button v-if="editingItem.id" class="btn btn--danger" :disabled="savingItem" @click="handleDeleteItem">刪除</button>
            <button class="btn btn--accent" :disabled="savingItem || !editForm.title.trim()" @click="handleSaveItem">
              {{ savingItem ? '儲存中…' : '儲存' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Emoji picker (Teleport to body to escape overflow) -->
    <Teleport to="body">
      <div v-if="showEmojiPicker" class="tep" :style="emojiPickerStyle">
        <div class="tep__grid">
          <button
            v-for="e in filteredEmojis"
            :key="e"
            class="tep__btn"
            @click="pickEmoji(e)"
          >{{ e }}</button>
          <div v-if="filteredEmojis.length === 0" class="tep__empty">沒有結果</div>
        </div>
        <input
          v-model="emojiSearch"
          class="tep__search"
          placeholder="搜尋（咖啡、飯店、海灘…）"
          @keydown.escape="showEmojiPicker = false"
        />
      </div>
    </Teleport>

    <!-- Source list modal -->
    <SourceListModal
      :open="sourcesOpen"
      :sources="current?.sources ?? []"
      :title="`從 ${current?.sources.length ?? 0} 則收藏彙整`"
      @close="sourcesOpen = false"
      @select="onSelectSource"
    />
  </div>
</template>

<script setup lang="ts">
import type { Trip, TripItem, TripListItem, TripTag } from '~/types/api'

definePageMeta({ ssr: false })
useHead({ title: 'Garner — 旅遊行程' })

const { listTrips, getTrip, createTrip, updateTrip, deleteTrip, addItem, updateItem, deleteItem, listTags, createTag, updateTag } = useTrips()
const { open: openItemModal } = useItemModal()

// ── Constants ──────────────────────────────────────────────────────────────
const VIEWS = [
  { key: 'board' as const, label: '行程分類', n: '1' },
  { key: 'date' as const, label: '依照日期', n: '2' },
]

const EMOJI_MAP: Array<{ e: string; k: string }> = [
  // 景點
  { e: '🏯', k: '城堡古蹟景點' }, { e: '🗼', k: '塔景點東京' }, { e: '⛩️', k: '鳥居神社景點' },
  { e: '🎡', k: '摩天輪遊樂場景點' }, { e: '🎢', k: '雲霄飛車遊樂場' }, { e: '🏛️', k: '博物館景點' },
  { e: '🗽', k: '自由女神像景點紐約' }, { e: '🏟️', k: '體育場競技場' }, { e: '🌊', k: '海浪海洋' },
  { e: '🏔️', k: '山景點高山' }, { e: '🗻', k: '富士山景點' }, { e: '🌋', k: '火山景點' },
  { e: '🏝️', k: '小島景點' }, { e: '🏖️', k: '海灘沙灘景點' }, { e: '🌅', k: '日出日落景點' },
  { e: '🌉', k: '夜晚橋景點' }, { e: '🌄', k: '山日出景點' }, { e: '🌃', k: '夜景城市景點' },
  // 美食
  { e: '🍜', k: '拉麵麵食美食' }, { e: '🍣', k: '壽司生魚片日本美食' }, { e: '🍱', k: '便當美食' },
  { e: '🍛', k: '咖哩美食' }, { e: '🍲', k: '火鍋鍋物美食' }, { e: '🍤', k: '炸蝦天婦羅美食' },
  { e: '🥘', k: '燉菜美食鍋物' }, { e: '🍷', k: '紅酒葡萄酒' }, { e: '🍻', k: '啤酒' },
  { e: '☕', k: '咖啡飲料' }, { e: '🍰', k: '蛋糕甜點' }, { e: '🍕', k: '披薩美食' },
  { e: '🍔', k: '漢堡美食' }, { e: '🥗', k: '沙拉' }, { e: '🧇', k: '鬆餅早餐' }, { e: '🍦', k: '冰淇淋甜點' },
  // 交通
  { e: '✈️', k: '飛機航班交通' }, { e: '🚂', k: '火車交通' }, { e: '🚌', k: '公車交通' },
  { e: '🚕', k: '計程車Uber交通' }, { e: '🚗', k: '租車自駕交通' }, { e: '🛵', k: '機車摩托車交通' },
  { e: '🚲', k: '腳踏車單車交通' }, { e: '🚢', k: '郵輪船交通' }, { e: '🚁', k: '直升機交通' },
  { e: '⛵', k: '帆船交通' }, { e: '🚐', k: '小巴交通' }, { e: '🛺', k: '嘟嘟車交通' },
  { e: '🏎️', k: '賽車' }, { e: '🛳️', k: '大船郵輪交通' },
  // 住宿
  { e: '🏨', k: '飯店旅館住宿' }, { e: '🏠', k: '民宿家住宿' }, { e: '🛖', k: '小屋住宿' },
  { e: '⛺', k: '露營帳篷住宿' }, { e: '🏕️', k: '露營住宿' }, { e: '🛏️', k: '床睡覺住宿' },
  // 其他
  { e: '📷', k: '相機拍照' }, { e: '🎫', k: '票券門票' }, { e: '🎟️', k: '票券' },
  { e: '🛍️', k: '購物' }, { e: '🎒', k: '背包' }, { e: '🧳', k: '行李箱行李' },
  { e: '🗺️', k: '地圖' }, { e: '🧭', k: '指南針' }, { e: '📍', k: '地標位置' },
  { e: '📌', k: '圖釘標記' }, { e: '❤️', k: '愛心最愛' }, { e: '⭐', k: '星星推薦' },
  { e: '🌸', k: '櫻花花' }, { e: '🎉', k: '慶祝' }, { e: '💡', k: '提示注意' }, { e: '🔑', k: '鑰匙' },
]

// ── State ──────────────────────────────────────────────────────────────────
const trips = ref<TripListItem[]>([])
const loadingList = ref(true)
const selectedId = ref<string | null>(null)
const current = ref<Trip | null>(null)
const loadingDetail = ref(false)
const creating = ref(false)
const activeView = ref<'board' | 'date'>('board')
const titleEl = ref<HTMLElement | null>(null)
const availableTags = ref<TripTag[]>([])
const sourcesOpen = ref(false)

function onSelectSource(id: string) {
  sourcesOpen.value = false
  openItemModal(id)
}

// Emoji picker
const emojiTriggerEl = ref<HTMLButtonElement | null>(null)
const showEmojiPicker = ref(false)
const emojiSearch = ref('')
const emojiPickerStyle = ref<Record<string, string>>({})

// Board tag editing
const editingTagId = ref<string | null>(null)
const editingTagName = ref('')
const tagEditInput = ref<HTMLInputElement | null>(null)

// Board add tag column
const addingBoardTag = ref(false)
const boardTagName = ref('')
const boardTagInputEl = ref<HTMLInputElement | null>(null)

// Modal inline tag add
const addingTag = ref(false)
const newTagName = ref('')
const newTagInputEl = ref<HTMLInputElement | null>(null)

// ── Lifecycle ──────────────────────────────────────────────────────────────
onMounted(async () => {
  loadingList.value = true
  document.addEventListener('click', handleOutsideClick, true)
  try {
    [trips.value, availableTags.value] = await Promise.all([listTrips(), listTags()])
    // 從 chat「開啟行程」帶 ?open=<id> 進來時，自動選取該行程
    const openId = useRoute().query.open as string | undefined
    if (openId && trips.value.some(t => t.id === openId)) {
      select(openId)
    }
    if (availableTags.value.length === 0) {
      const defaults = [
        { name: '景點', color: 'd' }, { name: '美食', color: 'e' },
        { name: '交通', color: 'b' }, { name: '住宿', color: 'a' },
      ]
      for (const d of defaults) {
        try {
          const tag = await createTag(d)
          availableTags.value.push(tag)
        } catch { /* ignore */ }
      }
    }
  } finally {
    loadingList.value = false
  }
})

onUnmounted(() => {
  document.removeEventListener('click', handleOutsideClick, true)
})

function handleOutsideClick(e: MouseEvent) {
  if (!showEmojiPicker.value) return
  const target = e.target as HTMLElement
  if (target.closest('.tep') || target.closest('.trips-emoji-trigger')) return
  showEmojiPicker.value = false
}

// ── Trip selection ─────────────────────────────────────────────────────────
async function select(id: string) {
  selectedId.value = id
  loadingDetail.value = true
  current.value = null
  try {
    current.value = await getTrip(id)
  } finally {
    loadingDetail.value = false
  }
}

async function handleCreate() {
  if (creating.value) return
  creating.value = true
  const tempId = `temp-${Date.now()}`
  const tempItem: TripListItem = {
    id: tempId, title: '新行程', summary: null,
    start_date: null, end_date: null,
    source_count: 0, item_count: 0, last_edited_by: 'user',
    created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
  }
  trips.value.unshift(tempItem)
  selectedId.value = tempId
  try {
    const trip = await createTrip({ title: '新行程' })
    const idx = trips.value.findIndex(t => t.id === tempId)
    if (idx !== -1) trips.value[idx] = { ...tempItem, id: trip.id }
    selectedId.value = trip.id
    current.value = trip
    nextTick(() => titleEl.value?.focus())
  } catch {
    trips.value = trips.value.filter(t => t.id !== tempId)
    selectedId.value = null
  } finally {
    creating.value = false
  }
}

async function handleDelete() {
  if (!current.value) return
  if (!confirm(`確定刪除「${current.value.title}」？`)) return
  const deletedId = current.value.id
  const deletedTrip = current.value
  const idx = trips.value.findIndex(t => t.id === deletedId)
  const removed = idx !== -1 ? trips.value[idx] : null
  if (idx !== -1) trips.value.splice(idx, 1)
  selectedId.value = null
  current.value = null
  try {
    await deleteTrip(deletedId)
  } catch {
    if (removed && idx !== -1) trips.value.splice(idx, 0, removed)
    selectedId.value = deletedId
    current.value = deletedTrip
  }
}

async function onTitleBlur(e: Event) {
  if (!current.value) return
  const newTitle = (e.target as HTMLElement).innerText.trim()
  if (!newTitle || newTitle === current.value.title) return
  const prevTitle = current.value.title
  current.value.title = newTitle
  const idx = trips.value.findIndex(t => t.id === current.value!.id)
  if (idx !== -1) trips.value[idx].title = newTitle
  try {
    await updateTrip(current.value.id, { title: newTitle })
  } catch {
    current.value.title = prevTitle
    if (idx !== -1) trips.value[idx].title = prevTitle
  }
}

// ── Board (by tags) ────────────────────────────────────────────────────────
const boardColumns = computed(() => [
  ...availableTags.value,
  { id: '__none__', name: '無標籤', color: null as string | null },
])

function itemsByTag(tagId: string) {
  if (!current.value) return []
  const items = current.value.items
  if (tagId === '__none__') {
    return items.filter(i => i.tags.length === 0).sort((a, b) => a.order_index - b.order_index)
  }
  return items
    .filter(i => i.tags.some(t => t.trip_tag_id === tagId))
    .sort((a, b) => a.order_index - b.order_index)
}

// ── Date / Timeline ────────────────────────────────────────────────────────
const tripDays = computed<string[]>(() => {
  if (!current.value) return []
  const days = new Set<string>()
  for (const item of current.value.items) {
    if (item.start_date) days.add(item.start_date)
    if (item.end_date) days.add(item.end_date)
  }
  return [...days].sort()
})

const unscheduledItems = computed(() =>
  (current.value?.items ?? []).filter(i => !i.start_date && !i.end_date).sort((a, b) => a.order_index - b.order_index)
)

function itemsByDate(day: string) {
  return (current.value?.items ?? [])
    .filter(i => i.start_date === day || (i.start_date && i.end_date && i.start_date <= day && i.end_date >= day))
    .sort((a, b) => {
      if (a.start_time && b.start_time) return a.start_time.localeCompare(b.start_time)
      return a.order_index - b.order_index
    })
}


// ── Formatting ─────────────────────────────────────────────────────────────
function formatDateRange(start: string | null, end: string | null) {
  if (!start) return ''
  const s = new Date(start).toLocaleDateString('zh-TW', { month: 'short', day: 'numeric' })
  if (!end || end === start) return s
  const e = new Date(end).toLocaleDateString('zh-TW', { month: 'short', day: 'numeric' })
  return `${s} – ${e}`
}

function formatMonth(d: string) { return new Date(d).toLocaleDateString('zh-TW', { month: 'short' }) }
function formatDay(d: string) { return new Date(d).getDate().toString() }
function formatDow(d: string) { return ['日','一','二','三','四','五','六'][new Date(d).getDay()] }
function isUrl(s: string | null | undefined): boolean {
  if (!s) return false
  try { new URL(s); return true } catch { return false }
}

// ── Emoji picker ───────────────────────────────────────────────────────────
const PICKER_W = 320
const PICKER_H = 310

const filteredEmojis = computed(() => {
  const q = emojiSearch.value.trim()
  if (!q) return EMOJI_MAP.map(e => e.e)
  return EMOJI_MAP.filter(({ k }) => k.includes(q)).map(e => e.e)
})

function toggleEmojiPicker() {
  if (showEmojiPicker.value) {
    showEmojiPicker.value = false
    return
  }
  if (!emojiTriggerEl.value) return
  const rect = emojiTriggerEl.value.getBoundingClientRect()
  let top = rect.bottom + 6
  let left = rect.left

  // Clamp horizontally
  if (left + PICKER_W > window.innerWidth - 8) {
    left = window.innerWidth - PICKER_W - 8
  }
  if (left < 8) left = 8

  // Flip upward if not enough space below
  if (top + PICKER_H > window.innerHeight - 8) {
    top = rect.top - PICKER_H - 6
  }

  emojiPickerStyle.value = { top: `${top}px`, left: `${left}px` }
  emojiSearch.value = ''
  showEmojiPicker.value = true
}

function pickEmoji(e: string) {
  editForm.value.emoji = e
  showEmojiPicker.value = false
}

// ── Item editor ────────────────────────────────────────────────────────────
interface EditForm {
  title: string
  emoji: string
  booked: boolean
  start_date: string
  end_date: string
  start_time: string
  end_time: string
  place_name: string
  note: string
  tag_ids: string[]
}

const editingItem = ref<Partial<TripItem> | null>(null)
const savingItem = ref(false)
const editForm = ref<EditForm>({
  title: '', emoji: '', booked: false,
  start_date: '', end_date: '', start_time: '', end_time: '',
  place_name: '', note: '', tag_ids: [],
})

function openItemEditor(item: TripItem) {
  editingItem.value = item
  editForm.value = {
    title: item.title,
    emoji: item.emoji ?? '',
    booked: item.booked,
    start_date: item.start_date ?? '',
    end_date: item.end_date ?? '',
    start_time: item.start_time ?? '',
    end_time: item.end_time ?? '',
    place_name: item.place_name ?? '',
    note: item.note ?? '',
    tag_ids: item.tags.map(t => t.trip_tag_id),
  }
}

function handleAddItem() {
  editingItem.value = {}
  editForm.value = {
    title: '', emoji: '', booked: false,
    start_date: '', end_date: '', start_time: '', end_time: '',
    place_name: '', note: '', tag_ids: [],
  }
}

function closeItemEditor() {
  editingItem.value = null
  showEmojiPicker.value = false
}

function buildPayload() {
  return {
    title: editForm.value.title.trim(),
    emoji: editForm.value.emoji || null,
    booked: editForm.value.booked,
    start_date: editForm.value.start_date || null,
    end_date: editForm.value.end_date || null,
    start_time: editForm.value.start_time || null,
    end_time: editForm.value.end_time || null,
    place_name: editForm.value.place_name || null,
    note: editForm.value.note || null,
    tag_ids: editForm.value.tag_ids,
  }
}

function sidebarItemCount(tripId: string, delta: number) {
  const idx = trips.value.findIndex(t => t.id === tripId)
  if (idx !== -1) trips.value[idx].item_count += delta
}

async function handleSaveItem() {
  if (!current.value || savingItem.value || !editForm.value.title.trim()) return
  savingItem.value = true
  const payload = buildPayload()
  const tripId = current.value.id

  if (editingItem.value?.id) {
    const itemId = editingItem.value.id
    const itemIdx = current.value.items.findIndex(i => i.id === itemId)
    const prevItem = itemIdx !== -1 ? { ...current.value.items[itemIdx] } : null
    const optimisticTags = availableTags.value
      .filter(t => payload.tag_ids.includes(t.id))
      .map(t => ({ trip_tag_id: t.id, name: t.name, color: t.color }))
    if (itemIdx !== -1) {
      current.value.items[itemIdx] = { ...current.value.items[itemIdx], ...payload, tags: optimisticTags }
    }
    closeItemEditor()
    try {
      const updated = await updateItem(tripId, itemId, payload)
      const finalIdx = current.value.items.findIndex(i => i.id === itemId)
      if (finalIdx !== -1) current.value.items[finalIdx] = updated
    } catch {
      if (prevItem && itemIdx !== -1) current.value.items[itemIdx] = prevItem
    }
  } else {
    const tempId = `temp-${Date.now()}`
    const tempTags = availableTags.value
      .filter(t => payload.tag_ids.includes(t.id))
      .map(t => ({ trip_tag_id: t.id, name: t.name, color: t.color }))
    const tempItem: TripItem = {
      id: tempId, trip_id: tripId, user_item_id: null,
      order_index: current.value.items.length,
      kind: 'event', category: null,
      geocoding_status: 'done', tags: tempTags,
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
      lat: null, lng: null,
      ...payload,
    }
    current.value.items.push(tempItem)
    sidebarItemCount(tripId, 1)
    closeItemEditor()
    try {
      const created = await addItem(tripId, { ...payload, order_index: tempItem.order_index })
      const idx = current.value.items.findIndex(i => i.id === tempId)
      if (idx !== -1) current.value.items[idx] = created
    } catch {
      current.value.items = current.value.items.filter(i => i.id !== tempId)
      sidebarItemCount(tripId, -1)
    }
  }
  savingItem.value = false
}

async function handleDeleteItem() {
  if (!current.value || !editingItem.value?.id || savingItem.value) return
  if (!confirm('確定刪除這張卡片？')) return
  const tripId = current.value.id
  const itemId = editingItem.value.id
  const itemIdx = current.value.items.findIndex(i => i.id === itemId)
  const removed = itemIdx !== -1 ? current.value.items[itemIdx] : null
  if (itemIdx !== -1) current.value.items.splice(itemIdx, 1)
  sidebarItemCount(tripId, -1)
  closeItemEditor()
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
}

// ── Board tag editing ──────────────────────────────────────────────────────
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

// ── Board add tag column ───────────────────────────────────────────────────
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

// ── Modal inline tag add (optimistic) ─────────────────────────────────────
function startAddTag() {
  addingTag.value = true
  newTagName.value = ''
  nextTick(() => newTagInputEl.value?.focus())
}

async function confirmNewTag() {
  const name = newTagName.value.trim()
  addingTag.value = false
  newTagName.value = ''
  if (!name) return
  const tempId = `temp-${Date.now()}`
  availableTags.value.push({ id: tempId, name, color: null })
  editForm.value.tag_ids.push(tempId)
  try {
    const tag = await createTag({ name })
    const idx = availableTags.value.findIndex(t => t.id === tempId)
    if (idx !== -1) availableTags.value[idx] = tag
    const tidIdx = editForm.value.tag_ids.indexOf(tempId)
    if (tidIdx !== -1) editForm.value.tag_ids[tidIdx] = tag.id
  } catch {
    availableTags.value = availableTags.value.filter(t => t.id !== tempId)
    editForm.value.tag_ids = editForm.value.tag_ids.filter(id => id !== tempId)
  }
}

function cancelNewTag() {
  addingTag.value = false
  newTagName.value = ''
}
</script>

<style scoped>
.trips-app {
  display: flex;
  height: calc(100vh - 56px);
  overflow: hidden;
}

/* ── Sidebar ── */
.trips-side {
  flex: 0 0 280px;
  border-right: 1px solid var(--border);
  background: color-mix(in oklab, var(--bg) 55%, var(--surface));
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.trips-side__head {
  padding: 18px 18px 12px;
  display: flex;
  align-items: center;
  gap: 9px;
}
.trips-side__lbl { font-family: var(--font-brand); font-weight: 600; font-size: 15px; color: var(--text); }
.trips-side__count {
  font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim);
  background: var(--surface2); border: 1px solid var(--border); padding: 1px 8px; border-radius: 20px;
}
.trips-side__newbtn {
  margin-left: auto; width: 28px; height: 28px; border-radius: 8px;
  display: inline-flex; align-items: center; justify-content: center;
  color: var(--text-dim); border: 1px solid var(--border); background: transparent; transition: all .14s ease;
}
.trips-side__newbtn:hover { color: var(--accent); border-color: var(--accent-bdr); background: var(--accent-dim); }
.trips-side__newbtn svg { width: 14px; height: 14px; }

.trips-rlist {
  flex: 1 1 auto; overflow-y: auto; padding: 4px 10px 18px;
  display: flex; flex-direction: column; gap: 4px;
}
.trips-rlist__loading, .trips-rlist__empty {
  font-size: 12px; color: var(--text-dim); padding: 16px 4px; text-align: center;
}
.trips-ritem {
  display: block; width: 100%; text-align: left; padding: 13px 14px; border-radius: 12px;
  border: 1px solid transparent; cursor: pointer;
  transition: background .14s ease, border-color .14s ease; background: transparent; color: inherit;
}
.trips-ritem:hover { background: var(--surface2); }
.trips-ritem.is-active { background: var(--surface2); border-color: var(--border2); }
.trips-ritem__title {
  font-size: 13.5px; font-weight: 600; line-height: 1.45; color: var(--text); margin: 0 0 5px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.trips-ritem__desc {
  font-size: 11.5px; color: var(--text-mid); line-height: 1.5; margin: 0 0 6px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.trips-ritem__meta { display: flex; align-items: center; gap: 8px; }
.trips-ritem__date { font-family: var(--font-mono); font-size: 10px; color: var(--text-dim); }
.trips-ritem__count { font-family: var(--font-mono); font-size: 10px; color: var(--text-dim); }

/* ── Main ── */
.trips-main { flex: 1 1 auto; display: flex; flex-direction: column; min-width: 0; min-height: 0; }
.trips-scroll { flex: 1 1 auto; overflow: hidden; display: flex; flex-direction: column; }
.trips-doc { flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; max-width: 1280px; width: 100%; margin: 0 auto; padding: 30px 44px 0; }
.trips-empty { display: flex; align-items: center; justify-content: center; flex: 1; color: var(--text-dim); font-size: 14px; }

/* Title row */
.trips-doc__top { display: flex; align-items: flex-start; gap: 16px; margin-bottom: 18px; }
.trips-doc__titlewrap { flex: 1; min-width: 0; }
.trips-doc__title {
  font-family: var(--font-brand); font-weight: 700; font-size: 32px;
  letter-spacing: -0.02em; line-height: 1.15; margin: 0 0 10px; outline: none; border-radius: 6px;
}
.trips-doc__title:focus { background: var(--surface2); }
.trips-doc__sub { font-family: var(--font-mono); font-size: 11.5px; color: var(--text-dim); }
.trips-doc__actions { display: flex; gap: 8px; flex-shrink: 0; padding-top: 6px; }

/* Sources trigger */
.trips-doc__srcbtn {
  font-family: var(--font-mono); font-size: 11.5px; color: var(--text-dim);
  background: none; border: none; padding: 0; cursor: pointer;
  text-decoration: underline; text-underline-offset: 2px; transition: color .14s ease;
}
.trips-doc__srcbtn:hover { color: var(--accent); }

/* Views */
.trips-views { display: flex; align-items: center; gap: 4px; margin-bottom: 22px; border-bottom: 1px solid var(--border); }
.trips-vtab {
  display: inline-flex; align-items: center; gap: 7px; font-size: 13px; font-weight: 500; color: var(--text-mid);
  padding: 9px 13px; border-radius: 9px 9px 0 0; border: 1px solid transparent; border-bottom: none;
  margin-bottom: -1px; cursor: pointer; transition: all .14s ease; position: relative; background: transparent;
}
.trips-vtab:hover { color: var(--text); background: var(--surface2); }
.trips-vtab__n { font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); }
.trips-vtab.is-active { color: var(--text); }
.trips-vtab.is-active::after {
  content: ''; position: absolute; left: 6px; right: 6px; bottom: -1px;
  height: 2px; background: var(--accent); border-radius: 2px;
}

/* Cards */
.trips-tcard {
  display: flex; flex-direction: column; gap: 6px; padding: 11px 13px; border-radius: 11px;
  background: var(--surface); border: 1px solid var(--border); cursor: pointer; transition: all .15s ease;
}
.trips-tcard:hover { border-color: var(--border2); transform: translateY(-2px); box-shadow: 0 10px 26px -14px var(--shadow); }
.trips-tcard__name { display: flex; align-items: flex-start; gap: 7px; font-size: 13px; font-weight: 500; color: var(--text); line-height: 1.4; }
.trips-tcard__emoji { flex: 0 0 auto; }
.trips-tcard__meta { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.trips-tcard__time { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); }
.trips-tcard__place { font-size: 13px; text-decoration: none; }
.trips-booked {
  display: inline-flex; align-items: center; gap: 3px; font-family: var(--font-mono); font-size: 9.5px; font-weight: 500;
  color: var(--tag-a); background: color-mix(in oklab, var(--tag-a) 14%, transparent);
  border: 1px solid color-mix(in oklab, var(--tag-a) 28%, transparent); padding: 2px 7px; border-radius: 6px;
}
.trips-empty-note { font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); padding: 8px 2px; }

/* Board */
.trips-board {
  flex: 1 1 auto; min-height: 0;
  display: flex; gap: 16px;
  overflow-x: auto; overflow-y: hidden;
  padding-bottom: 16px;
  align-items: stretch;
}
.trips-bcol { flex: 0 0 256px; display: flex; flex-direction: column; min-height: 0; }
.trips-bcol--addtag { flex: 0 0 160px; justify-content: flex-start; padding-top: 2px; }
.trips-bcol__head { display: flex; align-items: center; gap: 9px; padding: 0 2px; margin-bottom: 10px; flex-shrink: 0; }
.trips-bcol__cards { flex: 1 1 auto; overflow-y: auto; min-height: 0; display: flex; flex-direction: column; gap: 8px; padding-bottom: 4px; }
.trips-bcol__taginput {
  flex: 1; min-width: 0;
  background: var(--surface2);
  border: 1px solid var(--accent);
  border-radius: 20px;
  padding: 3px 10px;
  font-size: 12px;
  color: var(--text);
  outline: none;
}
.trips-colcount { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); }
.trips-addcol-btn {
  display: flex; align-items: center; gap: 7px;
  padding: 7px 12px; border-radius: 10px;
  border: 1px dashed var(--border2);
  background: transparent; color: var(--text-dim);
  font-size: 12.5px; cursor: pointer;
  transition: all .14s ease; white-space: nowrap;
}
.trips-addcol-btn svg { width: 13px; height: 13px; flex-shrink: 0; }
.trips-addcol-btn:hover { border-color: var(--accent-bdr); color: var(--accent); background: var(--accent-dim); }

/* Date board */
.trips-dboard { display: flex; gap: 16px; overflow-x: auto; padding-bottom: 12px; align-items: flex-start; }
.trips-dcol { flex: 0 0 240px; display: flex; flex-direction: column; gap: 10px; }
.trips-dcol__head { padding: 0 2px; margin-bottom: 2px; }
.trips-dcol__month { font-family: var(--font-mono); font-size: 10px; color: var(--text-dim); text-transform: uppercase; letter-spacing: .08em; margin-bottom: 2px; }
.trips-dcol__date { display: flex; align-items: baseline; gap: 6px; }
.trips-dcol__d { font-family: var(--font-brand); font-weight: 700; font-size: 17px; color: var(--text); letter-spacing: -0.01em; }
.trips-dcol__dow { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); }
.trips-dcol__cards { display: flex; flex-direction: column; gap: 8px; }

/* ── Modal ── */
.trips-modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.46); z-index: 200;
  display: flex; align-items: center; justify-content: center; padding: 24px;
}
.trips-modal {
  width: clamp(70vw, calc(100vw - 48px), 100vw);
  max-width: 100vw;
  max-height: 88vh;
  background: var(--bg);
  border: 1px solid var(--border2);
  border-radius: 16px;
  box-shadow: 0 24px 64px -16px rgba(0,0,0,.5);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.trips-modal__head {
  padding: 18px 20px 16px; border-bottom: 1px solid var(--border);
  display: flex; align-items: center; flex-shrink: 0;
}
.trips-modal__close { color: var(--text-dim); font-size: 16px; background: none; border: none; cursor: pointer; padding: 4px 8px; border-radius: 6px; }
.trips-modal__close:hover { background: var(--surface2); color: var(--text); }
.trips-modal__body { flex: 1 1 auto; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 18px; }
.trips-modal__foot { padding: 14px 20px; border-top: 1px solid var(--border); display: flex; justify-content: flex-end; gap: 8px; flex-shrink: 0; }

/* Fields */
.trips-field { display: flex; flex-direction: column; gap: 6px; }
.trips-field--inline { flex-direction: row; align-items: center; gap: 10px; }
.trips-field--note { gap: 8px; }
.trips-field__lbl { font-size: 12px; font-weight: 500; color: var(--text-mid); }
.trips-field__input {
  background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
  padding: 8px 11px; font-size: 13.5px; color: var(--text); outline: none; transition: border-color .15s;
}
.trips-field__input:focus { border-color: var(--accent); }

/* Title + emoji on same row */
.trips-titlerow { display: flex; align-items: center; gap: 8px; }
.trips-titlerow .trips-field__input { flex: 1; }
.trips-emoji-trigger {
  flex: 0 0 auto;
  width: 44px; height: 40px;
  font-size: 22px;
  line-height: 1;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: border-color .15s, background .15s;
}
.trips-emoji-trigger:hover { border-color: var(--accent); background: var(--accent-dim); }

/* Date + time combined */
.trips-field__timerow { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.trips-field__dt { width: 148px; }
.trips-field__tm { width: 138px; }
.trips-field__sep { color: var(--text-dim); font-size: 12px; }

/* Tiptap in modal */
.trips-tiptap-wrap {
  border: 1px solid var(--border); border-radius: 8px; min-height: 100px;
  overflow: hidden; background: var(--surface);
}
.trips-tiptap-wrap:focus-within { border-color: var(--accent); }
.trips-tiptap-wrap :deep(.ProseMirror) {
  padding: 8px 8px 8px 56px;
}

/* Tags */
.trips-tags-wrap { display: flex; flex-wrap: wrap; gap: 7px; align-items: center; }
.trips-pill {
  padding: 5px 12px; border-radius: 20px; font-size: 12px;
  border: 1px solid var(--border); background: var(--surface); color: var(--text-mid);
  cursor: pointer; transition: all .14s ease;
}
.trips-pill:hover { border-color: var(--border2); color: var(--text); }
.trips-pill.is-active { background: var(--accent-dim); border-color: var(--accent-bdr); color: var(--accent); }
.trips-newtag { display: inline-flex; align-items: center; }
.trips-newtag__input {
  background: var(--surface); border: 1px solid var(--accent); border-radius: 20px;
  padding: 4px 12px; font-size: 12px; color: var(--text); outline: none; width: 120px;
}

/* Transitions */
.modal-enter-active, .modal-leave-active { transition: opacity .18s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-active .trips-modal, .modal-leave-active .trips-modal { transition: transform .18s ease, opacity .18s ease; }
.modal-enter-from .trips-modal, .modal-leave-to .trips-modal { transform: scale(0.96); opacity: 0; }

@media (max-width: 900px) {
  .trips-side { display: none; }
  .trips-doc { padding: 22px 18px 48px; }
  .trips-modal-overlay { padding: 0; align-items: flex-end; }
  .trips-modal { width: 100vw; max-width: 100vw; max-height: 92vh; border-radius: 16px 16px 0 0; }
}
</style>

<!-- Emoji picker: not scoped, teleported to body -->
<style>
.tep {
  position: fixed;
  z-index: 9999;
  background: var(--bg);
  border: 1px solid var(--border2);
  border-radius: 14px;
  padding: 10px 10px 0;
  box-shadow: 0 12px 40px -8px rgba(0,0,0,.55);
  width: 320px;
  display: flex;
  flex-direction: column;
  gap: 0;
}
.tep__grid {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 1px;
  max-height: 240px;
  overflow-y: auto;
}
.tep__btn {
  font-size: 20px;
  line-height: 1;
  padding: 5px 2px;
  border-radius: 7px;
  border: none;
  background: transparent;
  cursor: pointer;
  transition: background .1s ease;
  text-align: center;
}
.tep__btn:hover { background: var(--surface2); }
.tep__empty { font-size: 12px; color: var(--text-dim); padding: 16px; text-align: center; grid-column: 1 / -1; }
.tep__search {
  margin: 8px 0 0;
  padding: 8px 11px;
  background: var(--surface);
  border: none;
  border-top: 1px solid var(--border);
  border-radius: 0 0 12px 12px;
  font-size: 12.5px;
  color: var(--text);
  outline: none;
  width: 100%;
  box-sizing: border-box;
}
.tep__search::placeholder { color: var(--text-dim); }
.tep__search:focus { background: var(--surface2); }
</style>
