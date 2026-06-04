<template>
  <div class="colmgr">
    <!-- ── Left: list ── -->
    <aside class="colmgr-list">
      <div class="colmgr-list__head">
        <h2 class="colmgr-list__title">我的集合</h2>
        <button class="btn btn--accent colmgr-list__new" @click="startCreate">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
          新增
        </button>
      </div>

      <!-- inline create form -->
      <form v-if="creating" class="colmgr-create" @submit.prevent="submitCreate">
        <input
          ref="createInput"
          v-model="newTitle"
          class="colmgr-create__input"
          placeholder="集合名稱..."
          maxlength="80"
          @keydown.esc="creating = false"
        >
        <div class="colmgr-create__actions">
          <button type="button" class="btn" @click="creating = false">取消</button>
          <button type="submit" class="btn btn--accent" :disabled="!newTitle.trim() || saving">建立</button>
        </div>
      </form>

      <div v-if="listLoading" class="colmgr-list__loading">
        <span v-for="n in 4" :key="n" class="colmgr-skel"></span>
      </div>
      <div v-else-if="!collections.length && !creating" class="colmgr-list__empty">
        還沒有集合，點「新增」開始建立
      </div>
      <button
        v-for="col in collections"
        :key="col.id"
        class="colmgr-item"
        :class="{ 'colmgr-item--active': selectedId === col.id }"
        @click="trySelectCollection(col.id)"
      >
        <span class="colmgr-item__title">{{ col.title }}</span>
        <div class="colmgr-item__meta">
          <span :class="`vis-dot vis-dot--${col.visibility}`"></span>
          <span class="colmgr-item__vis">{{ visLabel(col.visibility) }}</span>
        </div>
      </button>
    </aside>

    <!-- ── Right: edit panel ── -->
    <section v-if="selected" class="colmgr-edit">
      <div class="colmgr-edit__inner">

        <!-- title -->
        <div class="colmgr-section">
          <label class="colmgr-label">標題</label>
          <input v-model="editTitle" class="colmgr-input" maxlength="80" placeholder="集合名稱">
        </div>

        <!-- visibility -->
        <div class="colmgr-section">
          <label class="colmgr-label">可見度</label>
          <div class="vis-group">
            <button
              v-for="opt in VIS_OPTIONS"
              :key="opt.value"
              class="vis-btn"
              :class="{ 'vis-btn--active': editVisibility === opt.value }"
              @click="editVisibility = opt.value"
            >
              <span :class="`vis-dot vis-dot--${opt.value}`"></span>
              {{ opt.label }}
            </button>
          </div>
          <p class="colmgr-hint">
            <template v-if="editVisibility === 'public' || editVisibility === 'link'">
              <a :href="`/share/${selected.slug}`" target="_blank" class="colmgr-link">/share/{{ selected.slug }}</a>
            </template>
            <template v-else>
              <NuxtLink :to="`/app/collection/${selected.id}`" class="colmgr-link">/app/collection/{{ selected.id }}</NuxtLink>
            </template>
          </p>
        </div>

        <!-- items list -->
        <div class="colmgr-section">
          <label class="colmgr-label">
            內容
            <span class="colmgr-label__count">{{ displayItems.length }} 件</span>
            <span v-if="pendingAdditions.length || pendingRemovals.size" class="colmgr-label__dirty">未儲存</span>
          </label>

          <div v-if="detailLoading" class="colmgr-items-loading">
            <span v-for="n in 3" :key="n" class="colmgr-item-skel"></span>
          </div>
          <div v-else class="colmgr-items">
            <div
              v-for="item in displayItems"
              :key="item.id"
              class="colmgr-row"
              :class="{ 'colmgr-row--pending-add': isPendingAdd(item), 'colmgr-row--pending-remove': isPendingRemove(item) }"
            >
              <div class="colmgr-row__thumb">
                <img v-if="item.thumbnail_url" :src="item.thumbnail_url" :alt="item.title ?? ''">
                <div v-else class="placeholder placeholder--b"><div class="placeholder__stripes"></div></div>
              </div>
              <span class="colmgr-row__title">{{ item.title || item.url }}</span>
              <button
                v-if="isPendingRemove(item)"
                class="colmgr-row__undo"
                title="復原"
                @click="undoRemove(item)"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M3 9h13a5 5 0 0 1 0 10H7"/><polyline points="3 9 7 5 3 1"/></svg>
              </button>
              <button
                v-else
                class="colmgr-row__remove"
                title="移除"
                @click="markRemove(item)"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
              </button>
            </div>
            <p v-if="!displayItems.length" class="colmgr-items__empty">尚無內容，從下方搜尋加入</p>
          </div>

          <!-- add from library -->
          <div class="colmgr-add">
            <div class="colmgr-add__bar">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
              <input
                v-model="addQuery"
                class="colmgr-add__input"
                placeholder="從知識庫搜尋加入..."
                @input="onAddInput"
                @keydown.esc="closeAddSearch"
              >
              <button v-if="addQuery" class="colmgr-add__clear" @click="closeAddSearch">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
              </button>
            </div>
            <div v-if="addResults.length" class="colmgr-add__results">
              <button
                v-for="item in addResults"
                :key="item.id"
                class="colmgr-add__row"
                :class="{ 'colmgr-add__row--added': isAlreadyAdded(item) }"
                @click="toggleAdd(item)"
              >
                <div class="colmgr-add__thumb">
                  <img v-if="item.thumbnail_url" :src="item.thumbnail_url" :alt="item.title ?? ''">
                  <div v-else class="placeholder placeholder--c"><div class="placeholder__stripes"></div></div>
                </div>
                <span class="colmgr-add__title">{{ item.title || item.url }}</span>
                <svg v-if="isAlreadyAdded(item)" class="colmgr-add__check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
              </button>
            </div>
            <p v-else-if="addQuery && !addSearching" class="colmgr-add__empty">找不到符合的內容</p>
          </div>
        </div>

        <!-- bottom actions -->
        <div class="colmgr-actions">
          <button
            class="btn btn--accent colmgr-actions__save"
            :disabled="!isDirty || saving"
            @click="save"
          >
            {{ saving ? '儲存中...' : '保存' }}
          </button>
          <span v-if="saveSuccess" class="colmgr-actions__ok">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
            已儲存
          </span>
          <button class="btn colmgr-actions__discard" :disabled="!isDirty || saving" @click="discardChanges">
            捨棄變更
          </button>
          <div class="colmgr-actions__sep"></div>
          <template v-if="confirmingDelete">
            <span class="colmgr-danger__warn">確定刪除「{{ selected.title }}」？</span>
            <button class="btn" :disabled="deleting" @click="confirmingDelete = false">取消</button>
            <button class="btn btn--danger" :disabled="deleting" @click="deleteCollection">
              {{ deleting ? '刪除中...' : '確定刪除' }}
            </button>
          </template>
          <button v-else class="btn btn--ghost colmgr-danger__trigger" @click="confirmingDelete = true">
            刪除集合
          </button>
        </div>

      </div>
    </section>

    <div v-else-if="!listLoading" class="colmgr-placeholder">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" width="36" height="36"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>
      <p>選擇左側集合開始編輯</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Collection, CollectionDetail, Item } from '~/types/api'
useHead({ title: 'Vela — 我的集合' })

definePageMeta({ ssr: false })

const VIS_OPTIONS = [
  { value: 'private', label: '私人' },
  { value: 'link',    label: '連結' },
  { value: 'public',  label: '公開' },
] as const

type Visibility = 'private' | 'link' | 'public'

const apiFetch = useApiFetch()
const { searchItems } = useSearch()

// ── list ──
const collections = ref<Collection[]>([])
const listLoading = ref(true)
const selectedId = ref<string | null>(null)

// ── create ──
const creating = ref(false)
const newTitle = ref('')
const saving = ref(false)
const createInput = ref<HTMLInputElement | null>(null)

// ── detail ──
const selected = ref<CollectionDetail | null>(null)
const detailLoading = ref(false)

// ── edit state (staged, not sent until save) ──
const editTitle = ref('')
const editVisibility = ref<Visibility>('private')
const pendingAdditions = ref<Item[]>([])      // items to add
const pendingRemovals = ref(new Set<string>()) // content_ids to remove

// ── add search ──
const addQuery = ref('')
const addResults = ref<Item[]>([])
const addSearching = ref(false)
let addTimer: ReturnType<typeof setTimeout>

// ── save ──
const saveSuccess = ref(false)
let saveSuccessTimer: ReturnType<typeof setTimeout>

// ── delete ──
const confirmingDelete = ref(false)
const deleting = ref(false)

// ── computed ──
const isDirty = computed(() => {
  if (!selected.value) return false
  return (
    editTitle.value !== selected.value.title ||
    editVisibility.value !== selected.value.visibility ||
    pendingAdditions.value.length > 0 ||
    pendingRemovals.value.size > 0
  )
})

const displayItems = computed(() => {
  if (!selected.value) return []
  const base = selected.value.items.filter(i => !pendingRemovals.value.has(i.id))
  return [...base, ...pendingAdditions.value.map(toDisplayItem)]
})

function toDisplayItem(item: Item): Item {
  return { ...item, id: item.content_id! }
}

function isPendingAdd(item: Item) {
  return pendingAdditions.value.some(p => p.content_id === item.id)
}

function isPendingRemove(item: Item) {
  return pendingRemovals.value.has(item.id)
}

function isAlreadyAdded(item: Item) {
  if (!item.content_id) return false
  const inCollection = selected.value?.items.some(i => i.id === item.content_id) ?? false
  const inPending = pendingAdditions.value.some(p => p.content_id === item.content_id)
  return inCollection || inPending
}

function visLabel(v: string) {
  return { private: '私人', link: '連結', public: '公開' }[v] ?? v
}

// ── list ──
async function fetchList() {
  listLoading.value = true
  try {
    collections.value = await apiFetch<Collection[]>('/collections/')
  } finally {
    listLoading.value = false
  }
}

// ── select ──
async function loadDetail(id: string) {
  detailLoading.value = true
  selected.value = null
  pendingAdditions.value = []
  pendingRemovals.value = new Set()
  addQuery.value = ''
  addResults.value = []
  confirmingDelete.value = false
  saveSuccess.value = false
  try {
    const detail = await apiFetch<CollectionDetail>(`/collections/${id}`)
    selected.value = detail
    editTitle.value = detail.title
    editVisibility.value = detail.visibility as Visibility
  } finally {
    detailLoading.value = false
  }
}

async function trySelectCollection(id: string) {
  if (selectedId.value === id) return
  selectedId.value = id
  await loadDetail(id)
}

// ── create ──
function startCreate() {
  creating.value = true
  newTitle.value = ''
  nextTick(() => createInput.value?.focus())
}

function makeSlug(title: string) {
  return title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40)
    + '-' + Math.random().toString(36).slice(2, 6)
}

async function submitCreate() {
  const title = newTitle.value.trim()
  if (!title || saving.value) return
  saving.value = true
  try {
    const col = await apiFetch<Collection>('/collections/', {
      method: 'POST',
      body: { title, visibility: 'private', slug: makeSlug(title) },
    })
    collections.value.unshift(col)
    creating.value = false
    newTitle.value = ''
    selectedId.value = col.id
    await loadDetail(col.id)
  } finally {
    saving.value = false
  }
}

// ── item staging ──
function markRemove(item: Item) {
  // item.id here is content_id (from collection detail)
  pendingRemovals.value.add(item.id)
}

function undoRemove(item: Item) {
  pendingRemovals.value.delete(item.id)
}

// ── add search ──
function onAddInput() {
  clearTimeout(addTimer)
  if (!addQuery.value.trim()) { addResults.value = []; return }
  addSearching.value = true
  addTimer = setTimeout(async () => {
    try {
      addResults.value = await searchItems(addQuery.value)
    } finally {
      addSearching.value = false
    }
  }, 350)
}

function closeAddSearch() {
  addQuery.value = ''
  addResults.value = []
}

function toggleAdd(item: Item) {
  if (!item.content_id) return
  if (isAlreadyAdded(item)) {
    // if it's a pending addition, remove it; if already in collection, mark for removal
    const pendIdx = pendingAdditions.value.findIndex(p => p.content_id === item.content_id)
    if (pendIdx !== -1) {
      pendingAdditions.value.splice(pendIdx, 1)
    } else {
      pendingRemovals.value.add(item.content_id)
    }
  } else {
    pendingAdditions.value.push(item)
  }
}

// ── save ──
async function save() {
  if (!selected.value || saving.value || !isDirty.value) return
  saving.value = true
  saveSuccess.value = false
  try {
    const id = selected.value.id
    const patches: Promise<unknown>[] = []

    if (editTitle.value !== selected.value.title || editVisibility.value !== selected.value.visibility) {
      patches.push(apiFetch(`/collections/${id}`, {
        method: 'PATCH',
        body: { title: editTitle.value, visibility: editVisibility.value },
      }))
    }

    for (const contentId of pendingRemovals.value) {
      patches.push(apiFetch(`/collections/${id}/items/${contentId}`, { method: 'DELETE' }))
    }

    for (const item of pendingAdditions.value) {
      if (item.content_id) {
        patches.push(apiFetch(`/collections/${id}/items`, {
          method: 'POST',
          query: { content_id: item.content_id },
        }))
      }
    }

    await Promise.all(patches)

    // update list item
    const li = collections.value.find(c => c.id === id)
    if (li) {
      li.title = editTitle.value
      li.visibility = editVisibility.value
    }

    // reload detail to get fresh state
    await loadDetail(id)

    saveSuccess.value = true
    clearTimeout(saveSuccessTimer)
    saveSuccessTimer = setTimeout(() => { saveSuccess.value = false }, 3000)
  } finally {
    saving.value = false
  }
}

function discardChanges() {
  if (!selected.value) return
  editTitle.value = selected.value.title
  editVisibility.value = selected.value.visibility as Visibility
  pendingAdditions.value = []
  pendingRemovals.value = new Set()
}

// ── delete ──
async function deleteCollection() {
  if (!selected.value || deleting.value) return
  deleting.value = true
  try {
    await apiFetch(`/collections/${selected.value.id}`, { method: 'DELETE' })
    collections.value = collections.value.filter(c => c.id !== selected.value!.id)
    selected.value = null
    selectedId.value = null
    confirmingDelete.value = false
  } finally {
    deleting.value = false
  }
}

onMounted(fetchList)
</script>

<style>
.colmgr {
  display: flex;
  height: calc(100vh - 56px);
  overflow: hidden;
}

/* ── list ── */
.colmgr-list {
  width: 260px;
  flex-shrink: 0;
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}
.colmgr-list__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 16px 14px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  position: sticky;
  top: 0;
  background: var(--surface);
  z-index: 1;
}
.colmgr-list__title { font-family: var(--font-brand); font-size: 15px; font-weight: 600; margin: 0; }
.colmgr-list__new { height: 30px; padding: 0 10px; font-size: 12px; display: flex; align-items: center; gap: 5px; }
.colmgr-list__loading { padding: 12px; display: flex; flex-direction: column; gap: 8px; }
.colmgr-skel { display: block; height: 52px; background: var(--surface2); border-radius: 10px; animation: skel-pulse 1.4s ease infinite; }
.colmgr-list__empty { padding: 24px 16px; font-size: 12.5px; color: var(--text-dim); line-height: 1.6; }

/* create form */
.colmgr-create { padding: 12px; border-bottom: 1px solid var(--border); display: flex; flex-direction: column; gap: 8px; flex-shrink: 0; }
.colmgr-create__input { width: 100%; background: var(--bg); border: 1px solid var(--accent-bdr); border-radius: 8px; padding: 8px 10px; font-size: 13px; color: var(--text); outline: none; box-shadow: 0 0 0 3px var(--accent-dim); box-sizing: border-box; }
.colmgr-create__actions { display: flex; gap: 6px; justify-content: flex-end; }
.colmgr-create__actions .btn { height: 28px; padding: 0 10px; font-size: 12px; }

/* list items */
.colmgr-list > .colmgr-item { display: flex; flex-direction: column; gap: 4px; padding: 10px 16px; text-align: left; background: transparent; border: none; border-bottom: 1px solid var(--border); cursor: pointer; transition: background .12s; width: 100%; }
.colmgr-item:hover { background: var(--surface2); }
.colmgr-item--active { background: var(--accent-dim) !important; }
.colmgr-item__title { font-size: 13.5px; font-weight: 500; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
.colmgr-item__meta { display: flex; align-items: center; gap: 5px; }
.colmgr-item__vis { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); }

/* vis dots */
.vis-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
.vis-dot--public  { background: #34c759; }
.vis-dot--link    { background: #ff9f0a; }
.vis-dot--private { background: var(--text-dim); }

/* ── edit panel ── */
.colmgr-edit { flex: 1; overflow-y: auto; background: var(--bg); }
.colmgr-edit__inner { max-width: 680px; padding: 28px 32px 80px; display: flex; flex-direction: column; gap: 28px; }

.colmgr-section { display: flex; flex-direction: column; gap: 10px; }
.colmgr-label { font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); text-transform: uppercase; letter-spacing: .08em; display: flex; align-items: center; gap: 6px; }
.colmgr-label__count { background: var(--surface2); border-radius: 4px; padding: 1px 6px; font-size: 10.5px; color: var(--text-mid); }
.colmgr-label__dirty { background: rgba(255,159,10,.15); color: #ff9f0a; border-radius: 4px; padding: 1px 6px; font-size: 10px; }
.colmgr-input { background: var(--surface); border: 1px solid var(--border2); border-radius: 10px; padding: 10px 14px; font-size: 14px; font-family: var(--font-ui); color: var(--text); outline: none; transition: border-color .15s; max-width: 480px; width: 100%; box-sizing: border-box; }
.colmgr-input:focus { border-color: var(--accent-bdr); box-shadow: 0 0 0 3px var(--accent-dim); }
.colmgr-hint { margin: 0; font-size: 12px; color: var(--text-dim); }
.colmgr-link { color: var(--accent); text-decoration: none; }
.colmgr-link:hover { text-decoration: underline; }

/* vis group */
.vis-group { display: flex; gap: 6px; }
.vis-btn { display: flex; align-items: center; gap: 6px; padding: 7px 14px; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; font-size: 12.5px; font-family: var(--font-ui); color: var(--text-mid); cursor: pointer; transition: all .12s; }
.vis-btn:hover { color: var(--text); border-color: var(--border2); }
.vis-btn--active { background: var(--accent-dim); border-color: var(--accent-bdr); color: var(--accent); }

/* items list */
.colmgr-items-loading { display: flex; flex-direction: column; gap: 6px; }
.colmgr-item-skel { display: block; height: 44px; background: var(--surface2); border-radius: 8px; animation: skel-pulse 1.4s ease infinite; }
.colmgr-items { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; max-width: 560px; }
.colmgr-row { display: flex; align-items: center; gap: 10px; padding: 8px 12px; border-bottom: 1px solid var(--border); transition: background .1s; }
.colmgr-row:last-child { border-bottom: none; }
.colmgr-row--pending-add { background: rgba(52,199,89,.06); }
.colmgr-row--pending-remove { opacity: 0.45; }
.colmgr-row__thumb { width: 40px; height: 28px; border-radius: 5px; overflow: hidden; flex-shrink: 0; background: var(--surface2); }
.colmgr-row__thumb img { width: 100%; height: 100%; object-fit: cover; }
.colmgr-row__title { flex: 1; font-size: 12.5px; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.colmgr-row__remove, .colmgr-row__undo { width: 24px; height: 24px; border-radius: 6px; background: transparent; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: background .12s, color .12s; }
.colmgr-row__remove { color: var(--text-dim); }
.colmgr-row__remove:hover { background: var(--surface2); color: var(--text); }
.colmgr-row__undo { color: var(--accent); }
.colmgr-row__undo:hover { background: var(--accent-dim); }
.colmgr-items__empty { padding: 16px 14px; font-size: 12.5px; color: var(--text-dim); margin: 0; }

/* add from library */
.colmgr-add { margin-top: 10px; max-width: 560px; }
.colmgr-add__bar { display: flex; align-items: center; gap: 8px; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 0 12px; }
.colmgr-add__bar svg { width: 14px; height: 14px; color: var(--text-dim); flex-shrink: 0; }
.colmgr-add__input { flex: 1; height: 38px; background: transparent; border: none; outline: none; font-size: 13px; font-family: var(--font-ui); color: var(--text); min-width: 0; }
.colmgr-add__input::placeholder { color: var(--text-dim); }
.colmgr-add__clear { background: transparent; border: none; cursor: pointer; color: var(--text-dim); display: flex; align-items: center; padding: 0; flex-shrink: 0; }
.colmgr-add__clear:hover { color: var(--text); }
.colmgr-add__results { margin-top: 6px; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; max-height: 240px; overflow-y: auto; }
.colmgr-add__row { display: flex; align-items: center; gap: 8px; padding: 7px 12px; width: 100%; text-align: left; background: transparent; border: none; border-bottom: 1px solid var(--border); cursor: pointer; transition: background .1s; }
.colmgr-add__row:last-child { border-bottom: none; }
.colmgr-add__row:hover { background: var(--surface2); }
.colmgr-add__row--added { background: rgba(52,199,89,.06); }
.colmgr-add__thumb { width: 34px; height: 24px; border-radius: 4px; overflow: hidden; flex-shrink: 0; background: var(--surface2); }
.colmgr-add__thumb img { width: 100%; height: 100%; object-fit: cover; }
.colmgr-add__title { flex: 1; font-size: 12.5px; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.colmgr-add__check { width: 14px; height: 14px; color: #34c759; flex-shrink: 0; }
.colmgr-add__empty { font-size: 12px; color: var(--text-dim); padding: 6px 0; margin: 0; }

/* bottom actions */
.colmgr-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 0 0;
  border-top: 1px solid var(--border);
  flex-wrap: wrap;
}
.colmgr-actions__save { min-width: 80px; }
.colmgr-actions__save:disabled { opacity: 0.4; cursor: not-allowed; }
.colmgr-actions__ok { display: flex; align-items: center; gap: 5px; font-size: 12.5px; color: #34c759; font-family: var(--font-mono); }
.colmgr-actions__discard { font-size: 12.5px; color: var(--text-mid); }
.colmgr-actions__discard:disabled { opacity: 0.4; cursor: not-allowed; }
.colmgr-actions__sep { flex: 1; }
.colmgr-danger__trigger { font-size: 12.5px; color: var(--danger, #e85555); border-color: transparent; }
.colmgr-danger__warn { font-size: 12.5px; color: var(--text-mid); }
.btn--danger { background: #e85555; color: #fff; border-color: #e85555; }
.btn--danger:hover { background: #d44; border-color: #d44; }
.btn--danger:disabled { opacity: 0.5; cursor: not-allowed; }

/* placeholder */
.colmgr-placeholder { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; color: var(--text-dim); }
.colmgr-placeholder p { font-size: 13px; margin: 0; }

@media (max-width: 640px) {
  .colmgr { flex-direction: column; height: auto; overflow: visible; }
  .colmgr-list { width: 100%; border-right: none; border-bottom: 1px solid var(--border); max-height: 280px; }
  .colmgr-edit__inner { padding: 20px 16px 60px; }
}
</style>
