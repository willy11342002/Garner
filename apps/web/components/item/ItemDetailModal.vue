<script setup lang="ts">
import type { Item, CollectionShareItem, Tag } from '~/types/api'

type AnyItem = Item | CollectionShareItem

const props = defineProps<{
  itemId?: string | null     // 私人模式：傳 id，自動 fetch
  item?: AnyItem | null      // 公開唯讀模式：直接傳已載入的 item
}>()
const emit = defineEmits<{ close: []; archived: [] }>()

// 是否顯示
const isOpen = computed(() => !!(props.itemId || props.item))
// 是否為唯讀公開模式
const readonly = computed(() => !props.itemId)

const { getItem, getItemTags, getPendingItemTags, attachTag, detachTag, updateItem, confirmItemTag, updateItemSummary } = useItems()
const { localize, locale } = useI18nContent()

const localizedTiptap = computed(() => {
  const i = item.value
  if (!i) return null
  const i18n = (i as Item).summary_i18n
  if (i18n && typeof i18n === 'object') {
    const doc = (i18n as Record<string, unknown>)[locale.value] ?? (i18n as Record<string, unknown>)['zh-TW']
    if (doc && typeof doc === 'object') return doc as Record<string, unknown>
  }
  return null
})

// Edit mode (only available when is_owner)
const isEditing = ref(false)
const editDoc = ref<Record<string, unknown> | null>(null)
const saving = ref(false)

const canEdit = computed(() => !readonly.value && !!(item.value as Item)?.is_owner)

function startEdit() {
  editDoc.value = localizedTiptap.value ? JSON.parse(JSON.stringify(localizedTiptap.value)) : { type: 'doc', content: [] }
  isEditing.value = true
}

function cancelEdit() {
  isEditing.value = false
  editDoc.value = null
}

async function saveEdit() {
  if (!item.value || !editDoc.value) return
  saving.value = true
  try {
    const currentLocale = locale.value || 'zh-TW'
    const existing = (item.value as Item).summary_i18n ?? {}
    const updated = { ...existing, [currentLocale]: editDoc.value }
    const saved = await updateItemSummary(item.value.id, updated)
    fetchedItem.value = saved
    isEditing.value = false
    editDoc.value = null
  } finally {
    saving.value = false
  }
}

const fetchedItem = ref<Item | null>(null)
const tags = ref<Tag[]>([])
const pendingTags = ref<Tag[]>([])
const loading = ref(false)
const error = ref(false)

// 最終顯示的 item：私人模式用 fetchedItem，公開模式用 props.item
const item = computed(() => readonly.value ? props.item ?? null : fetchedItem.value)

// Tags
const addingTag = ref(false)
const newTagInput = ref('')
const tagRemoving = ref<Record<string, boolean>>({})
const tagAdding = ref(false)
const tagInputRef = ref<HTMLInputElement | null>(null)
const tagConfirming = ref<Record<string, boolean>>({})
const confirmingAll = ref(false)

// Archive
const archiving = ref(false)
const showArchiveConfirm = ref(false)

const TAG_COLORS = ['a', 'b', 'c', 'd', 'e'] as const
function tagColor(i: number) { return TAG_COLORS[i % TAG_COLORS.length] }

function sourceLabel(url: string) {
  if (/youtu/.test(url)) return '▶ YouTube'
  if (/instagram\.com/.test(url)) return 'IG'
  return 'Article'
}

function cardTitle(url: string, title: string | null) {
  if (title) return title
  try { return new URL(url).hostname.replace(/^www\./, '') }
  catch { return '' }
}

function relativeTime(dateStr: string) {
  const d = Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000)
  if (d === 0) return '今天'
  if (d === 1) return '1 天前'
  return `${d} 天前`
}

async function load(id: string) {
  loading.value = true
  error.value = false
  fetchedItem.value = null
  tags.value = []
  pendingTags.value = []
  try {
    const [fi, ft, fp] = await Promise.all([getItem(id), getItemTags(id), getPendingItemTags(id)])
    fetchedItem.value = fi
    tags.value = ft
    pendingTags.value = fp
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

watch(() => props.itemId, (id) => {
  if (id) {
    if (import.meta.client) document.body.style.overflow = 'hidden'
    load(id)
  } else if (!props.item) {
    if (import.meta.client) document.body.style.overflow = ''
    fetchedItem.value = null
    tags.value = []
    pendingTags.value = []
  }
}, { immediate: true })

watch(() => props.item, (v) => {
  if (!import.meta.client) return
  if (v) document.body.style.overflow = 'hidden'
  else if (!props.itemId) document.body.style.overflow = ''
}, { immediate: true })

onUnmounted(() => {
  if (import.meta.client) document.body.style.overflow = ''
})

function doClose() {
  showArchiveConfirm.value = false
  emit('close')
}

// Tag handlers
async function startAddingTag() {
  addingTag.value = true
  await nextTick()
  tagInputRef.value?.focus()
}

async function handleAddTag() {
  const name = newTagInput.value.trim()
  addingTag.value = false
  newTagInput.value = ''
  if (!name || !item.value) return
  tagAdding.value = true
  try {
    const tag = await attachTag(item.value.id, name, false)
    if (tag) tags.value.push(tag)
  } finally {
    tagAdding.value = false
  }
}

async function handleRemoveTag(tag: Tag) {
  if (!item.value) return
  tagRemoving.value[tag.id] = true
  try {
    await detachTag(item.value.id, tag.id)
    tags.value = tags.value.filter(t => t.id !== tag.id)
  } finally {
    delete tagRemoving.value[tag.id]
  }
}

async function handleConfirmTag(tag: Tag) {
  if (!item.value) return
  tagConfirming.value[tag.id] = true
  try {
    await confirmItemTag(item.value.id, tag.id)
    pendingTags.value = pendingTags.value.filter(t => t.id !== tag.id)
    tags.value.push(tag)
  } finally {
    delete tagConfirming.value[tag.id]
  }
}

async function handleConfirmAll() {
  if (!item.value || !pendingTags.value.length) return
  confirmingAll.value = true
  try {
    await Promise.all(pendingTags.value.map(t => confirmItemTag(item.value!.id, t.id)))
    tags.value.push(...pendingTags.value)
    pendingTags.value = []
  } finally {
    confirmingAll.value = false
  }
}

async function handleRemovePendingTag(tag: Tag) {
  if (!item.value) return
  tagRemoving.value[tag.id] = true
  try {
    await detachTag(item.value.id, tag.id)
    pendingTags.value = pendingTags.value.filter(t => t.id !== tag.id)
  } finally {
    delete tagRemoving.value[tag.id]
  }
}

// Archive handlers
function requestArchive() {
  if (item.value?.status === 'archived') confirmArchive()
  else showArchiveConfirm.value = true
}

async function confirmArchive() {
  if (!item.value) return
  showArchiveConfirm.value = false
  archiving.value = true
  try {
    const isArchived = item.value.status === 'archived'
    await updateItem(item.value.id, { status: isArchived ? 'active' : 'archived' })
    fetchedItem.value = { ...fetchedItem.value!, status: isArchived ? 'active' : 'archived' }
    emit('archived')
  } finally {
    archiving.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="id-overlay"
      @click.self="doClose"
      @keydown.esc="doClose"
      tabindex="-1"
    >
      <div v-if="loading" class="id-spinner">載入中...</div>
      <div v-else-if="error" class="id-spinner">載入失敗，請重新整理</div>

      <div v-else-if="item" class="id-panel fadeup">
        <button class="id-close" @click="doClose">×</button>

        <div class="id-media">
          <img v-if="item.thumbnail_url" :src="item.thumbnail_url" class="id-media__img" alt="">
          <div v-else class="placeholder placeholder--b id-media__ph">
            <div class="placeholder__stripes"></div>
          </div>
          <span class="source-badge id-media__badge">{{ sourceLabel(item.url) }}</span>
        </div>

        <div class="id-body">
          <div v-if="(item as Item).saved_at" class="id-body__meta mono">{{ relativeTime((item as Item).saved_at) }}</div>
          <h1 class="id-body__title">{{ cardTitle(item.url, item.title) }}</h1>

          <!-- Tags（私人模式才顯示） -->
          <div v-if="!readonly" class="id-body__tags">
            <!-- Pending tags：AI 推薦、待確認 -->
            <template v-if="pendingTags.length">
              <div class="id-body__tags-pending-label">AI 建議標籤</div>
              <span
                v-for="tag in pendingTags"
                :key="tag.id"
                class="tag-chip tag-chip--pending id-tag"
                :style="(tagRemoving[tag.id] || tagConfirming[tag.id]) ? 'opacity:0.4;pointer-events:none' : ''"
              >
                {{ localize(tag.name_i18n, tag.name) }}
                <button class="id-tag__confirm" @click="handleConfirmTag(tag)" title="確認此標籤">✓</button>
                <button class="id-tag__remove" @click="handleRemovePendingTag(tag)">×</button>
              </span>
            </template>

            <!-- Confirmed tags -->
            <span
              v-for="(tag, i) in tags"
              :key="tag.id"
              :class="`tag-chip tag-chip--${tagColor(i)} id-tag`"
              :style="tagRemoving[tag.id] ? 'opacity:0.4;pointer-events:none' : ''"
            >
              {{ localize(tag.name_i18n, tag.name) }}
              <button class="id-tag__remove" @click="handleRemoveTag(tag)">×</button>
            </span>

            <template v-if="addingTag">
              <input
                ref="tagInputRef"
                v-model="newTagInput"
                class="id-tag__input"
                placeholder="標籤名稱"
                @keydown.enter="handleAddTag"
                @keydown.esc.stop="addingTag = false; newTagInput = ''"
                @blur="handleAddTag"
              />
            </template>
            <button v-else class="id-tag__add" :disabled="tagAdding" @click="startAddingTag">
              + 新增標籤
            </button>
          </div>

          <!-- Summary -->
          <div v-if="item.summary || (item as Item).summary_i18n || canEdit" class="id-body__summary">
            <div class="id-body__summary-label mono">
              SUMMARY
              <button v-if="canEdit && !isEditing" class="id-summary__edit-btn" @click="startEdit">編輯</button>
            </div>
            <template v-if="isEditing">
              <TiptapEditor v-model="editDoc" :readonly="false" />
              <div class="id-summary__edit-actions">
                <button class="btn btn--accent" :disabled="saving" @click="saveEdit">{{ saving ? '儲存中…' : '儲存' }}</button>
                <button class="btn" :disabled="saving" @click="cancelEdit">取消</button>
              </div>
            </template>
            <template v-else>
              <TiptapEditor v-if="localizedTiptap" :model-value="localizedTiptap" :readonly="true" />
              <p v-else-if="canEdit" class="id-body__summary-empty">點擊「編輯」開始記錄想法…</p>
            </template>
          </div>
          <div v-else-if="!readonly && !(item as Item).parsed_at">
            <span class="processing-badge">AI 處理中...</span>
          </div>

          <!-- Actions -->
          <div class="id-body__actions">
            <button
              v-if="!readonly && pendingTags.length"
              class="btn btn--confirm-tags"
              :disabled="confirmingAll"
              @click="handleConfirmAll"
            >
              {{ confirmingAll ? '確認中…' : `確認標籤 (${pendingTags.length})` }}
            </button>
            <a :href="item.url" target="_blank" rel="noopener" class="btn btn--accent">開啟原文 →</a>
            <button v-if="!readonly" class="btn" :disabled="archiving" @click="requestArchive">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0">
                <template v-if="(item as Item).status === 'archived'">
                  <path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>
                </template>
                <template v-else>
                  <rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/><line x1="12" y1="12" x2="12" y2="16"/><line x1="10" y1="14" x2="14" y2="14"/>
                </template>
              </svg>
              {{ archiving ? '處理中…' : (item as Item).status === 'archived' ? '復原' : '封存' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Archive confirm -->
    <div v-if="showArchiveConfirm" class="modal-mask" @click.self="showArchiveConfirm = false">
      <div class="modal">
        <h2>確認封存</h2>
        <p>封存後此內容將從首頁與搜尋結果中隱藏，可前往<b>封存庫</b>隨時復原。</p>
        <div class="modal__actions">
          <button class="btn btn--warn" style="flex:1;" :disabled="archiving" @click="confirmArchive">
            {{ archiving ? '處理中…' : '封存' }}
          </button>
          <button class="btn" :disabled="archiving" @click="showArchiveConfirm = false">取消</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
