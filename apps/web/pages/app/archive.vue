<template>
  <main class="shell">
    <header class="arc-head">
      <span class="eyebrow">ARCHIVE</span>
      <h1 class="page-title">封存庫</h1>
      <p>封存的內容不會出現在首頁和搜尋結果，但隨時可以復原。</p>
    </header>

    <div class="banner">
      <span class="banner__icon">📁</span>
      <span>封存內容共 <b>{{ items.length }} 筆</b>，不佔用首頁與搜尋結果。</span>
      <a href="#" class="banner__action mono" style="color:var(--text-mid); font-size:11px;">了解封存機制 →</a>
    </div>
    <div v-if="dangerItems.length > 0" class="banner banner--warn">
      <span class="banner__icon">⏳</span>
      <span>有 <b>{{ dangerItems.length }} 筆</b>內容即將於 24 小時後永久刪除，趕快復原！</span>
      <a href="#danger" class="banner__action mono" style="font-size:11px;">前往查看 →</a>
    </div>

    <div class="toolbar">
      <span class="eyebrow" style="margin-right:4px;">SORT</span>
      <div class="toolbar__group">
        <button class="sort-btn" :class="{ 'sort-btn--active': sortBy === 'date' }" @click="sortBy = 'date'">封存日期</button>
        <button class="sort-btn" :class="{ 'sort-btn--active': sortBy === 'oldest' }" @click="sortBy = 'oldest'">最舊優先</button>
        <button class="sort-btn" :class="{ 'sort-btn--active': sortBy === 'type' }" @click="sortBy = 'type'">來源類型</button>
      </div>
      <div class="toolbar__right">
        <button class="sort-btn" @click="toggleAll">全選</button>
        <span>{{ items.length }} 項封存<template v-if="dangerItems.length"> · {{ dangerItems.length }} 待刪除</template></span>
      </div>
    </div>

    <!-- Selection bar -->
    <div v-if="selectedIds.size > 0" class="selbar">
      <span class="selbar__count">已選 {{ selectedIds.size }} 項</span>
      <button class="btn" style="background:var(--accent-dim); color:var(--accent); border-color:var(--accent-bdr);" :disabled="restoring" @click="restoreSelected">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/></svg>
        {{ restoring ? '復原中…' : '復原' }}
      </button>
      <button class="btn btn--danger" :disabled="deleting" @click="showConfirm = true">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>
        永久刪除
      </button>
      <div class="spacer"></div>
      <button class="btn btn--ghost" @click="selectedIds.clear()">取消</button>
    </div>

    <!-- Archive items -->
    <div v-if="loading" class="alist" style="color:var(--text-dim);font-size:13px;padding:24px 0;">載入中…</div>
    <div v-else-if="sortedItems.length === 0" class="alist" style="color:var(--text-dim);font-size:13px;padding:24px 0;">沒有封存的內容。</div>
    <div v-else class="alist">
      <div
        v-for="item in sortedItems"
        :key="item.id"
        class="aitem"
        :class="{ selected: selectedIds.has(item.id) }"
        @click="toggleItem(item.id, $event)"
      >
        <span class="checkbox">
          <svg v-if="selectedIds.has(item.id)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
        </span>
        <div class="aitem__thumb">
          <img v-if="item.thumbnail_url" :src="item.thumbnail_url" style="width:100%;height:100%;object-fit:cover;" />
          <div v-else :class="`placeholder placeholder--${placeholderColor(item.source_type)}`"><div class="placeholder__stripes"></div></div>
        </div>
        <div class="aitem__main">
          <h3 class="aitem__title">{{ item.title }}</h3>
          <div class="aitem__meta">
            <span>{{ sourceLabel(item.source_type) }}</span>
            <span class="aitem__dot"></span>
            <span>{{ domainFromUrl(item.url) }}</span>
          </div>
        </div>
        <span class="aitem__when">封存於 {{ timeAgo(item.saved_at) }}</span>
        <div class="aitem__actions">
          <button class="btn" style="height:30px;padding:0 12px;font-size:12px;" @click.stop="restoreItem(item.id)">復原</button>
          <button class="btn btn--danger" style="height:30px;padding:0 12px;font-size:12px;" @click.stop="permanentDeleteItem(item.id)">刪除</button>
        </div>
      </div>
    </div>

    <!-- Danger zone -->
    <template v-if="dangerItems.length > 0">
      <header class="danger-head" id="danger">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" style="color:var(--warn)"><path d="M12 9v4M12 17h.01M10.3 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/></svg>
        <span class="mono">即將永久刪除</span>
        <span class="danger-head__count">{{ dangerItems.length }} 筆 · 24 小時後從系統清除</span>
      </header>

      <div class="alist">
        <div v-for="item in dangerItems" :key="item.id" class="aitem aitem--danger">
          <span class="checkbox"></span>
          <div class="aitem__thumb">
            <img v-if="item.thumbnail_url" :src="item.thumbnail_url" style="width:100%;height:100%;object-fit:cover;" />
            <div v-else :class="`placeholder placeholder--${placeholderColor(item.source_type)}`"><div class="placeholder__stripes"></div></div>
          </div>
          <div class="aitem__main">
            <h3 class="aitem__title">{{ item.title }}</h3>
            <div class="aitem__meta">
              <span>{{ sourceLabel(item.source_type) }} · {{ timeAgo(item.saved_at) }}</span>
            </div>
          </div>
          <span class="aitem__when"></span>
          <div class="aitem__actions"><button class="btn btn--warn" @click.stop="restoreItem(item.id)">復原</button></div>
        </div>
      </div>
    </template>
  </main>

  <!-- Confirm modal -->
  <div v-if="showConfirm" class="modal-mask" @click.self="showConfirm = false">
    <div class="modal">
      <h2>確認永久刪除</h2>
      <p>這個動作<b style="color:var(--danger)">無法復原</b>。以下內容將從你的知識庫中完全移除，包含摘要與關聯資料。</p>
      <div class="modal__list">
        <div v-for="item in selectedItems" :key="item.id" class="modal__list-item">{{ item.title }}</div>
      </div>
      <div class="modal__actions">
        <button class="btn btn--danger" style="flex:1;" :disabled="deleting" @click="permanentDeleteSelected">
          {{ deleting ? '刪除中…' : `永久刪除（${selectedIds.size} 筆）` }}
        </button>
        <button class="btn" :disabled="deleting" @click="showConfirm = false">取消</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Item } from '~/types/api'

const { listArchivedItems, updateItem, deleteItem } = useItems()

const sortBy = ref('date')
const showConfirm = ref(false)
const selectedIds = reactive(new Set<string>())
const loading = ref(true)
const items = ref<Item[]>([])
const dangerItems = ref<Item[]>([])
const restoring = ref(false)
const deleting = ref(false)

onMounted(async () => {
  try {
    items.value = await listArchivedItems()
  } finally {
    loading.value = false
  }
})

const sortedItems = computed(() => {
  const list = [...items.value]
  if (sortBy.value === 'oldest')
    return list.sort((a, b) => new Date(a.saved_at).getTime() - new Date(b.saved_at).getTime())
  if (sortBy.value === 'type')
    return list.sort((a, b) => (a.source_type ?? '').localeCompare(b.source_type ?? ''))
  return list.sort((a, b) => new Date(b.saved_at).getTime() - new Date(a.saved_at).getTime())
})

const selectedItems = computed(() => items.value.filter(i => selectedIds.has(i.id)))

function sourceLabel(sourceType: string | null): string {
  if (sourceType === 'youtube') return '▶ YouTube'
  if (sourceType === 'ig') return 'Instagram'
  return 'Article'
}

function domainFromUrl(url: string): string {
  try { return new URL(url).hostname.replace('www.', '') }
  catch { return url }
}

function timeAgo(dateStr: string): string {
  const diff = Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000)
  if (diff === 0) return '今天'
  if (diff === 1) return '昨天'
  if (diff < 30) return `${diff} 天前`
  if (diff < 365) return `${Math.floor(diff / 30)} 個月前`
  return `${Math.floor(diff / 365)} 年前`
}

function placeholderColor(sourceType: string | null): string {
  if (sourceType === 'youtube') return 'b'
  if (sourceType === 'ig') return 'e'
  return 'a'
}

function toggleItem(id: string, e: MouseEvent) {
  if ((e.target as HTMLElement).closest('.btn')) return
  if (selectedIds.has(id)) selectedIds.delete(id)
  else selectedIds.add(id)
}

function toggleAll() {
  if (selectedIds.size === sortedItems.value.length) selectedIds.clear()
  else sortedItems.value.forEach(i => selectedIds.add(i.id))
}

async function restoreItem(id: string) {
  await updateItem(id, { status: 'active' })
  items.value = items.value.filter(i => i.id !== id)
  selectedIds.delete(id)
}

async function restoreSelected() {
  restoring.value = true
  try {
    for (const id of [...selectedIds]) await restoreItem(id)
  } finally {
    restoring.value = false
  }
}

async function permanentDeleteItem(id: string) {
  await deleteItem(id)
  items.value = items.value.filter(i => i.id !== id)
  selectedIds.delete(id)
}

async function permanentDeleteSelected() {
  deleting.value = true
  try {
    for (const id of [...selectedIds]) await permanentDeleteItem(id)
    showConfirm.value = false
  } finally {
    deleting.value = false
  }
}
</script>
