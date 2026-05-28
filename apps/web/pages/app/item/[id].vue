<script setup lang="ts">
import type { Item, Tag } from '~/types/api'

const route = useRoute()
const router = useRouter()
const id = route.params.id as string

const { getItem, getItemTags, attachTag, detachTag, updateItem } = useItems()
const { localize } = useI18nContent()

const item = ref<Item | null>(null)
const tags = ref<Tag[]>([])
const loading = ref(true)
const error = ref(false)

const addingTag = ref(false)
const newTagInput = ref('')
const tagRemoving = ref<Record<string, boolean>>({})
const tagAdding = ref(false)
const tagInputRef = ref<HTMLInputElement | null>(null)

async function startAddingTag() {
  addingTag.value = true
  await nextTick()
  tagInputRef.value?.focus()
}

const TAG_COLORS = ['a', 'b', 'c', 'd', 'e'] as const

function tagColor(i: number) {
  return TAG_COLORS[i % TAG_COLORS.length]
}

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

const archiving = ref(false)
const showArchiveConfirm = ref(false)

function close() {
  router.back()
}

function requestArchive() {
  if (item.value?.status === 'archived') {
    confirmArchive()
  } else {
    showArchiveConfirm.value = true
  }
}

async function confirmArchive() {
  if (!item.value) return
  showArchiveConfirm.value = false
  archiving.value = true
  try {
    const isArchived = item.value.status === 'archived'
    await updateItem(item.value.id, { status: isArchived ? 'active' : 'archived' })
    router.back()
  } finally {
    archiving.value = false
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

onMounted(async () => {
  document.body.style.overflow = 'hidden'
  try {
    const [fetchedItem, fetchedTags] = await Promise.all([
      getItem(id),
      getItemTags(id),
    ])
    item.value = fetchedItem
    tags.value = fetchedTags
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  document.body.style.overflow = ''
})
</script>

<template>
  <div
    class="id-overlay"
    @click.self="close"
    @keydown.esc="close"
    tabindex="-1"
  >
    <div v-if="loading" class="id-spinner">載入中...</div>
    <div v-else-if="error" class="id-spinner">載入失敗，請重新整理</div>

    <div v-else-if="item" class="id-panel fadeup">
      <button class="id-close" @click="close">×</button>

      <div class="id-media">
        <img v-if="item.thumbnail_url" :src="item.thumbnail_url" class="id-media__img" alt="" />
        <div v-else class="placeholder placeholder--b id-media__ph">
          <div class="placeholder__stripes"></div>
        </div>
        <span class="source-badge id-media__badge">{{ sourceLabel(item.url) }}</span>
      </div>

      <div class="id-body">
        <div class="id-body__meta mono">{{ relativeTime(item.saved_at) }}</div>
        <h1 class="id-body__title">{{ cardTitle(item.url, item.title) }}</h1>

        <div class="id-body__tags">
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
          <button
            v-else
            class="id-tag__add"
            :disabled="tagAdding"
            @click="startAddingTag"
          >+ 新增標籤</button>
        </div>

        <div v-if="item.summary || item.summary_i18n" class="id-body__summary">
          <div class="id-body__summary-label mono">SUMMARY</div>
          <p class="id-body__summary-text">{{ localize(item.summary_i18n, item.summary) }}</p>
        </div>
        <div v-else-if="!item.parsed_at">
          <span class="processing-badge">AI 處理中...</span>
        </div>

        <div class="id-body__actions">
          <a :href="item.url" target="_blank" rel="noopener" class="btn btn--accent">開啟原文 →</a>
          <button class="btn" :disabled="archiving" @click="requestArchive">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0">
              <template v-if="item.status === 'archived'">
                <path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>
              </template>
              <template v-else>
                <rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/><line x1="12" y1="12" x2="12" y2="16"/><line x1="10" y1="14" x2="14" y2="14"/>
              </template>
            </svg>
            {{ archiving ? '處理中…' : item.status === 'archived' ? '復原' : '封存' }}
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Archive confirm modal -->
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
</template>
