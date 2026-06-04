<script setup lang="ts">
import type { ItemPendingReview, Tag } from '~/types/api'

const emit = defineEmits<{
  'item-tags-updated': [itemId: string]
}>()

const { getPendingReview, confirmItemTagsBulk, detachTag, attachTag } = useItems()
const { open: openItemModal } = useItemModal()
const notifStore = useNotificationStore()
const itemStore = useItemStore()
const { localize } = useI18nContent()
const { pendingItems } = usePendingItems()

const expanded = ref(false)
const confirmingAll = ref(false)
const tagDismissing = ref<Record<string, boolean>>({})
const addingTagFor = ref<string | null>(null)
const newTagInput = ref('')
let newTagInputEl: HTMLInputElement | null = null

function pendingKey(itemId: string, tagId: string) {
  return `${itemId}:${tagId}`
}

function sourceEmoji(url: string) {
  if (/youtu/.test(url)) return '▶'
  if (/instagram\.com/.test(url)) return '◈'
  return '◎'
}

function sourceIconBg(url: string) {
  if (/youtu/.test(url)) return 'rgba(255,80,80,.18)'
  if (/instagram\.com/.test(url)) return 'rgba(200,60,180,.18)'
  return 'rgba(80,120,255,.18)'
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
  if (d === 0) return 'today'
  if (d === 1) return '1d ago'
  return `${d}d ago`
}

function markNotifReadForItem(itemId: string) {
  const ids = notifStore.items
    .filter(n => n.item_id === itemId && !n.is_read)
    .map(n => n.id)
  if (ids.length) notifStore.markRead(ids)
}

const confirmingItem = ref<string | null>(null)
const archivingItem = ref<string | null>(null)

async function handleConfirmItem(item: ItemPendingReview) {
  confirmingItem.value = item.id
  try {
    await confirmItemTagsBulk(item.id, item.pending_tags.map(t => t.id))
    emit('item-tags-updated', item.id)
    markNotifReadForItem(item.id)
    pendingItems.value = pendingItems.value.filter(i => i.id !== item.id)
  } finally {
    confirmingItem.value = null
  }
}

async function handleArchiveItem(item: ItemPendingReview) {
  archivingItem.value = item.id
  try {
    await itemStore.patch(item.id, { status: 'archived' })
    pendingItems.value = pendingItems.value.filter(i => i.id !== item.id)
  } finally {
    archivingItem.value = null
  }
}

async function handleConfirmAll() {
  confirmingAll.value = true
  try {
    for (const item of [...pendingItems.value]) {
      await confirmItemTagsBulk(item.id, item.pending_tags.map(t => t.id))
      emit('item-tags-updated', item.id)
      markNotifReadForItem(item.id)
    }
    pendingItems.value = []
  } finally {
    confirmingAll.value = false
  }
}

async function handleDismissTag(item: ItemPendingReview, tagId: string) {
  const key = pendingKey(item.id, tagId)
  tagDismissing.value[key] = true
  try {
    await detachTag(item.id, tagId)
    item.pending_tags = item.pending_tags.filter(t => t.id !== tagId)
    if (item.pending_tags.length === 0) {
      pendingItems.value = pendingItems.value.filter(i => i.id !== item.id)
    }
  } finally {
    tagDismissing.value[key] = false
  }
}

async function startAddingTag(itemId: string) {
  addingTagFor.value = itemId
  newTagInput.value = ''
  await nextTick()
  newTagInputEl?.focus()
}

async function handleAddTag(item: ItemPendingReview) {
  const name = newTagInput.value.trim()
  addingTagFor.value = null
  newTagInput.value = ''
  if (!name) return
  const tempId = `local-${name}-${Date.now()}`
  item.pending_tags.push({ id: tempId, name, name_i18n: null, item_count: 0 })
  const tag = await attachTag(item.id, name, true)
  if (tag?.id) {
    const idx = item.pending_tags.findIndex(t => t.id === tempId)
    if (idx !== -1) item.pending_tags[idx] = tag
  }
}

watch(() => itemStore.recentlyProcessed, async (itemId) => {
  if (!itemId) return
  pendingItems.value = await getPendingReview()
})

onMounted(async () => {
  pendingItems.value = await getPendingReview()
})
</script>

<template>
  <section v-if="pendingItems.length > 0" class="pending-section fadeup">
    <header class="pending-section__head">
      <span class="pending-section__dot"></span>
      <span class="pending-section__count">{{ pendingItems.length }} 筆新知識待確認</span>
      <button
        class="pending-section__confirm-all"
        :disabled="confirmingAll"
        @click="handleConfirmAll"
      >{{ confirmingAll ? '確認中...' : '全部確認' }}</button>
      <button class="pending-section__toggle" @click="expanded = !expanded">
        <svg
          width="12" height="12" viewBox="0 0 12 12" fill="none"
          stroke="currentColor" stroke-width="2" stroke-linecap="round"
          :style="{ transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform .2s ease' }"
        >
          <polyline points="1 4 6 9 11 4"/>
        </svg>
        <span>{{ expanded ? '收起' : '展開' }}</span>
      </button>
    </header>

    <div v-show="expanded" class="pending-list">
      <div
        v-for="item in pendingItems"
        :key="item.id"
        class="pending-row"
        @click="openItemModal(item.id)"
      >
        <div class="pending-row__icon" :style="`background:${sourceIconBg(item.url)}`">
          {{ sourceEmoji(item.url) }}
        </div>
        <div class="pending-row__main">
          <div class="pending-row__title">{{ cardTitle(item.url, item.title) }}</div>
          <div class="pending-row__meta">
            <span class="source-badge source-badge--sm">{{ sourceLabel(item.url) }}</span>
            <span class="mono">{{ relativeTime(item.saved_at) }}</span>
          </div>
        </div>
        <div class="pending-row__tags" @click.stop>
          <div
            v-for="tag in item.pending_tags"
            :key="tag.id"
            class="pending-tag-chip"
            :class="{ 'pending-tag-chip--acting': tagDismissing[pendingKey(item.id, tag.id)] }"
          >
            <span>#{{ localize(tag.name_i18n, tag.name) }}</span>
            <button
              :disabled="tagDismissing[pendingKey(item.id, tag.id)]"
              @click="handleDismissTag(item, tag.id)"
            >×</button>
          </div>
          <template v-if="addingTagFor === item.id">
            <input
              :ref="(el) => { newTagInputEl = el as HTMLInputElement | null }"
              v-model="newTagInput"
              class="pending-tag-input"
              placeholder="標籤名稱"
              @keydown.enter.stop="handleAddTag(item)"
              @keydown.esc.stop="addingTagFor = null; newTagInput = ''"
              @blur="handleAddTag(item)"
              @click.stop
            />
          </template>
          <button
            v-else
            class="pending-row__add"
            title="新增標籤"
            @click="startAddingTag(item.id)"
          >+</button>
        </div>
        <div class="pending-row__actions" @click.stop>
          <button
            class="pending-row__action pending-row__action--archive"
            :disabled="archivingItem === item.id || confirmingItem === item.id"
            title="封存"
            @click="handleArchiveItem(item)"
          >封存</button>
          <button
            class="pending-row__action pending-row__action--confirm"
            :disabled="confirmingItem === item.id || archivingItem === item.id"
            title="確認"
            @click="handleConfirmItem(item)"
          >{{ confirmingItem === item.id ? '...' : '確認' }}</button>
        </div>
      </div>
    </div>
  </section>
</template>
