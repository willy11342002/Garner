<script setup lang="ts">
import type { Item, Tag } from '~/types/api'

definePageMeta({ ssr: false, layout: 'write' })

const route = useRoute()
const router = useRouter()
const id = route.params.id as string

const FROM_LABELS: Record<string, string> = {
  '/app/articles': '我的文章',
  '/app/chat': '對話',
  '/app/collections': '我的集合',
  '/app/archive': '封存庫',
}
const backPath = computed(() => (route.query.from as string) || '/app')
const backLabel = computed(() => FROM_LABELS[backPath.value] ?? '首頁')


const { updateArticle, publishArticle, uploadCover, deleteCover } = useArticles()
const { attachTag, detachTag, confirmItemTag, getPendingItemTags, getItemTags, deleteItem } = useItems()
const apiFetch = useApiFetch()

const article = ref<Item | null>(null)
const loading = ref(true)
const loadError = ref(false)

const title = ref('')
const editorContent = ref<Record<string, unknown>>({ type: 'doc', content: [] })
const isPublic = ref(false)
const isDraft = ref(true)

const saveStatus = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
const analyzing = ref(false)
const analysisStage = ref<string>('')

const STAGE_LABELS: Record<string, string> = {
  analyzing: 'AI 分析中',
  embedding: '建立索引中',
  failed:    '處理失敗',
  timeout:   '處理逾時',
}
const analysisLabel = computed(() =>
  STAGE_LABELS[analysisStage.value] ?? 'AI 處理中'
)
const isDirty = ref(false)
const archiving = ref(false)

const originalTitle = ref('')
const originalContent = ref('')

// ── Outline ──────────────────────────────────────────────────────────────────
interface OutlineItem { level: number; text: string; index: number }

const outlineOpen = ref(window.innerWidth > 768)
const editorBodyRef = ref<HTMLElement | null>(null)

const outline = computed<OutlineItem[]>(() => {
  const content = (editorContent.value?.content as any[]) ?? []
  const items: OutlineItem[] = []
  let idx = 0
  for (const node of content) {
    if (node.type === 'heading') {
      const level: number = node.attrs?.level ?? 1
      if (level >= 1 && level <= 4) {
        const text = ((node.content ?? []) as any[])
          .filter((c: any) => c.type === 'text')
          .map((c: any) => c.text as string)
          .join('')
        items.push({ level, text, index: idx })
      }
      idx++
    }
  }
  return items
})

function scrollToHeading(headingIndex: number) {
  const container = editorBodyRef.value
  if (!container) return
  const headings = container.querySelectorAll<HTMLElement>('.ProseMirror h1, .ProseMirror h2, .ProseMirror h3, .ProseMirror h4')
  const dom = headings[headingIndex]
  if (!dom) return
  // write-page uses min-height (not height), so window is the real scroll container
  const top = window.scrollY + dom.getBoundingClientRect().top - 68 // 44px topbar + 24px padding
  window.scrollTo({ top, behavior: 'smooth' })
}

// AI 分析抽屜
const drawerOpen = ref(window.innerWidth > 768)
const drawerHasResult = ref(false)
const confirmedTags = ref<Tag[]>([])
const pendingTags = ref<Tag[]>([])

const { locale } = useI18nContent()
const localizedTiptap = computed(() => {
  const i18n = article.value?.summary_i18n
  if (i18n && typeof i18n === 'object') {
    const doc = (i18n as Record<string, unknown>)[locale.value]
      ?? (i18n as Record<string, unknown>)['zh-TW']
    if (doc && typeof doc === 'object') return doc as Record<string, unknown>
  }
  return null
})

// ── 標籤操作 ──────────────────────────────────────────────────────────────────
const tagRemoving = ref<Record<string, boolean>>({})
const tagConfirming = ref<Record<string, boolean>>({})
const addingTag = ref(false)
const newTagInput = ref('')
const tagAdding = ref(false)
const tagInputRef = ref<HTMLInputElement | null>(null)

async function startAddingTag() {
  addingTag.value = true
  await nextTick()
  tagInputRef.value?.focus()
}

async function handleAddTag() {
  const name = newTagInput.value.trim()
  addingTag.value = false
  newTagInput.value = ''
  if (!name) return
  tagAdding.value = true
  try {
    const tag = await attachTag(id, name, false)
    if (tag) confirmedTags.value.push(tag)
  } finally {
    tagAdding.value = false
  }
}

async function handleRemoveConfirmedTag(tag: Tag) {
  tagRemoving.value[tag.id] = true
  try {
    await detachTag(id, tag.id)
    confirmedTags.value = confirmedTags.value.filter(t => t.id !== tag.id)
  } finally {
    delete tagRemoving.value[tag.id]
  }
}

async function handleConfirmTag(tag: Tag) {
  tagConfirming.value[tag.id] = true
  try {
    await confirmItemTag(id, tag.id)
    pendingTags.value = pendingTags.value.filter(t => t.id !== tag.id)
    confirmedTags.value.push(tag)
  } finally {
    delete tagConfirming.value[tag.id]
  }
}

async function handleRemovePendingTag(tag: Tag) {
  tagRemoving.value[tag.id] = true
  try {
    await detachTag(id, tag.id)
    pendingTags.value = pendingTags.value.filter(t => t.id !== tag.id)
  } finally {
    delete tagRemoving.value[tag.id]
  }
}

async function fetchTags() {
  try {
    const [confirmed, pending] = await Promise.all([
      getItemTags(id),
      getPendingItemTags(id),
    ])
    confirmedTags.value = confirmed
    pendingTags.value = pending
  } catch { /* ignore */ }
}

onMounted(async () => {
  try {
    const data: Item = await apiFetch(`/articles/${id}`)
    article.value = data
    title.value = data.title ?? ''
    originalTitle.value = data.title ?? ''
    isPublic.value = data.is_public
    isDraft.value = data.is_draft
    if (data.content_md) {
      try { editorContent.value = JSON.parse(data.content_md) } catch { /* ignore */ }
    }
    originalContent.value = data.content_md ?? ''
    if (data.parsed_at) {
      drawerHasResult.value = true
      await fetchTags()
    }
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
})

watch(title, (val) => { isDirty.value = val !== originalTitle.value || JSON.stringify(editorContent.value) !== originalContent.value })
watch(editorContent, (val) => { isDirty.value = title.value !== originalTitle.value || JSON.stringify(val) !== originalContent.value }, { deep: true })

function handleBeforeUnload(e: BeforeUnloadEvent) {
  if (!isDirty.value) return
  e.preventDefault()
}
onMounted(() => window.addEventListener('beforeunload', handleBeforeUnload))
onBeforeUnmount(() => window.removeEventListener('beforeunload', handleBeforeUnload))

onBeforeRouteLeave(() => {
  if (!isDirty.value) return true
  return window.confirm('有未保存的變更，確定要離開嗎？')
})

async function handleArchive() {
  if (!window.confirm('確定要封存這篇文章嗎？封存後可在封存庫找回。')) return
  archiving.value = true
  isDirty.value = false
  try {
    await deleteItem(id)
    router.push(backPath.value)
  } catch {
    isDirty.value = true
    archiving.value = false
  }
}

async function togglePublic() {
  isPublic.value = !isPublic.value
  await updateArticle(id, { is_public: isPublic.value })
}

async function handleAnalyze() {
  if (analyzing.value) return
  analyzing.value = true
  try {
    await updateArticle(id, {
      title: title.value || '未命名文章',
      content_md: JSON.stringify(editorContent.value),
      is_public: isPublic.value,
    })
    originalTitle.value = title.value || '未命名文章'
    originalContent.value = JSON.stringify(editorContent.value)
    isDirty.value = false
    const updated = await publishArticle(id)
    isDraft.value = updated.is_draft
    article.value = updated
    drawerHasResult.value = true
    drawerOpen.value = true
    // 等待背景 AI 分析完成
    await waitForAnalysis(id)
  } catch {
    saveStatus.value = 'error'
  } finally {
    analyzing.value = false
    if (saveStatus.value !== 'error') {
      saveStatus.value = 'saved'
      setTimeout(() => { if (saveStatus.value === 'saved') saveStatus.value = 'idle' }, 2500)
    }
  }
}

async function waitForAnalysis(itemId: string) {
  const config = useRuntimeConfig()
  const session = useSupabaseSession()
  const token = session.value?.access_token
  if (!token) return

  let response: Response
  try {
    response = await fetch(
      `${config.public.apiBase}/items/${itemId}/stream`,
      { headers: { Authorization: `Bearer ${token}` } },
    )
  } catch { return }

  if (!response.ok || !response.body) return

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const msg = JSON.parse(line.slice(6))
          if (msg.status === 'progress' && msg.stage) {
            analysisStage.value = msg.stage
          } else if (msg.status === 'done' && msg.item) {
            article.value = msg.item
            isDraft.value = msg.item.is_draft
            await fetchTags()
            return
          } else if (msg.status === 'failed' || msg.status === 'timeout') {
            analysisStage.value = msg.status
            return
          }
        } catch { /* ignore malformed line */ }
      }
    }
  } finally {
    reader.cancel()
  }
}

// cover
const coverInput = ref<HTMLInputElement | null>(null)
const coverUploading = ref(false)

async function handleCoverChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  coverUploading.value = true
  try {
    const updated = await uploadCover(id, file)
    if (article.value) article.value.thumbnail_url = updated.thumbnail_url
  } finally {
    coverUploading.value = false
    if (coverInput.value) coverInput.value.value = ''
  }
}

async function handleDeleteCover(e: Event) {
  e.stopPropagation()
  coverUploading.value = true
  try {
    const updated = await deleteCover(id)
    if (article.value) article.value.thumbnail_url = updated.thumbnail_url
  } finally {
    coverUploading.value = false
  }
}

</script>

<template>
  <div class="write-page" :class="{ 'write-page--drawer-open': drawerOpen }">

    <!-- Top bar -->
    <header class="write-bar">
      <button class="write-bar__back" @click="router.push(backPath)">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg>
        {{ backLabel }}
      </button>

      <div class="write-bar__meta">
        <span class="write-bar__dot" :class="isDraft ? 'write-bar__dot--draft' : 'write-bar__dot--pub'"></span>
        <span class="write-bar__label">{{ isDraft ? '草稿' : '已發布' }}</span>
        <span v-if="saveStatus === 'saving'" class="write-bar__save">儲存中…</span>
        <span v-else-if="saveStatus === 'saved'" class="write-bar__save write-bar__save--ok">已儲存</span>
        <span v-else-if="saveStatus === 'error'" class="write-bar__save write-bar__save--err">儲存失敗</span>
      </div>

      <div class="write-bar__actions">
        <!-- Public toggle pill -->
        <button
          class="write-bar__pill"
          :class="{ 'write-bar__pill--on': isPublic }"
          @click="togglePublic"
        >
          <span class="write-bar__pill-knob"></span>
          <span class="write-bar__pill-label">{{ isPublic ? '公開' : '私有' }}</span>
        </button>

        <!-- Archive button -->
        <button
          class="write-bar__archive"
          :disabled="archiving || analyzing"
          @click="handleArchive"
        >封存</button>

        <!-- AI 分析按鈕 -->
        <button
          class="write-bar__publish"
          :disabled="analyzing"
          @click="handleAnalyze"
        >{{ analyzing ? analysisLabel : '保存' }}</button>
      </div>
    </header>

    <!-- Loading -->
    <div v-if="loading" class="write-center">
      <span class="write-spinner"></span>
    </div>

    <!-- Error -->
    <div v-else-if="loadError" class="write-center">
      <p class="write-center__msg">無法載入文章</p>
      <NuxtLink to="/app" class="btn btn--ghost">← 返回首頁</NuxtLink>
    </div>

    <!-- Editor + Drawer wrapper -->
    <main v-else class="write-main">

      <!-- 左側大綱 -->
      <aside class="write-outline" :class="{ 'write-outline--open': outlineOpen }">
        <button class="write-outline-toggle" @click="outlineOpen = !outlineOpen">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="14" height="14">
            <path v-if="outlineOpen" d="M15 18l-6-6 6-6"/>
            <path v-else d="M9 18l6-6-6-6"/>
          </svg>
        </button>
        <div class="write-outline__head">
          <span class="write-outline__title">大綱</span>
        </div>
        <div class="write-outline__body">
          <p v-if="!outline.length" class="write-outline__empty">尚無標題</p>
          <nav v-else class="write-outline__nav">
            <button
              v-for="item in outline"
              :key="item.index"
              class="write-outline__item"
              :class="`write-outline__item--h${item.level}`"
              @click="scrollToHeading(item.index)"
            >{{ item.text || '（無標題）' }}</button>
          </nav>
        </div>
      </aside>

      <!-- Editor body -->
      <div ref="editorBodyRef" class="write-editor-body">

      <!-- Cover -->
      <div
        class="write-cover"
        :class="{ 'write-cover--has-img': !!article?.thumbnail_url }"
        @click="coverInput?.click()"
      >
        <img
          v-if="article?.thumbnail_url"
          :src="article.thumbnail_url"
          class="write-cover__img"
          alt=""
        />
        <div v-else class="write-cover__empty">
          <span v-if="coverUploading" class="write-spinner"></span>
          <template v-else>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
            新增封面圖
          </template>
        </div>
        <div v-if="article?.thumbnail_url" class="write-cover__overlay">
          <span class="write-cover__change">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            更換封面
          </span>
          <span class="write-cover__delete" @click="handleDeleteCover">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
            刪除封面
          </span>
        </div>
        <input
          ref="coverInput"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          class="write-cover__input"
          @change="handleCoverChange"
        />
      </div>

      <!-- Content area -->
      <div class="write-content">
        <!-- Title -->
        <textarea
          v-model="title"
          class="write-title"
          placeholder="未命名"
          rows="1"
          maxlength="200"
          @input="(e) => { const el = e.target as HTMLTextAreaElement; el.style.height = 'auto'; el.style.height = el.scrollHeight + 'px' }"
        />

        <!-- Body -->
        <div class="write-body">
          <TiptapEditor v-model="editorContent" />
        </div>
      </div>
      </div><!-- end write-editor-body -->

      <!-- AI 分析抽屜（always rendered，用 class 控制開關） -->
      <aside class="write-drawer" :class="{ 'write-drawer--open': drawerOpen }">
        <!-- handle 黏在抽屜左緣，跟著滑動 -->
        <button
          class="write-panel-toggle"
          @click="drawerOpen = !drawerOpen"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="14" height="14">
            <path v-if="drawerOpen" d="M9 18l6-6-6-6"/>
            <path v-else d="M15 18l-6-6 6-6"/>
          </svg>
        </button>

        <div class="write-drawer__head">
          <span class="write-drawer__title">元資料</span>
        </div>

        <div class="write-drawer__body">
          <template v-if="!drawerHasResult">
            <p class="write-drawer__empty">點擊「保存」產生摘要與標籤。</p>
          </template>
          <template v-else>
            <!-- 標籤 -->
            <section class="write-drawer__section">
              <div class="write-drawer__section-label">標籤</div>
              <div class="write-drawer__tags">
                <!-- AI 待確認 -->
                <template v-if="pendingTags.length">
                  <div class="write-drawer__tags-pending-label">AI 建議</div>
                  <span
                    v-for="tag in pendingTags"
                    :key="tag.id"
                    class="write-drawer__tag write-drawer__tag--pending"
                    :style="(tagRemoving[tag.id] || tagConfirming[tag.id]) ? 'opacity:0.4;pointer-events:none' : ''"
                  >
                    {{ tag.name }}
                    <button class="write-drawer__tag-confirm" title="確認" @click="handleConfirmTag(tag)">✓</button>
                    <button class="write-drawer__tag-remove" @click="handleRemovePendingTag(tag)">×</button>
                  </span>
                </template>

                <!-- 已確認 -->
                <span
                  v-for="tag in confirmedTags"
                  :key="tag.id"
                  class="write-drawer__tag"
                  :style="tagRemoving[tag.id] ? 'opacity:0.4;pointer-events:none' : ''"
                >
                  {{ tag.name }}
                  <button class="write-drawer__tag-remove" @click="handleRemoveConfirmedTag(tag)">×</button>
                </span>

                <!-- 新增輸入 -->
                <input
                  v-if="addingTag"
                  ref="tagInputRef"
                  v-model="newTagInput"
                  class="write-drawer__tag-input"
                  placeholder="標籤名稱"
                  @keydown.enter="handleAddTag"
                  @keydown.esc.stop="addingTag = false; newTagInput = ''"
                  @blur="handleAddTag"
                />
                <button v-else class="write-drawer__tag-add" :disabled="tagAdding" @click="startAddingTag">
                  + 新增
                </button>
              </div>
              <p v-if="!pendingTags.length && !confirmedTags.length && !addingTag" class="write-drawer__empty-sm">分析中，請稍候…</p>
            </section>

            <!-- 摘要 -->
            <section class="write-drawer__section">
              <div class="write-drawer__section-label">摘要</div>
              <template v-if="localizedTiptap">
                <TiptapEditor :model-value="localizedTiptap" :readonly="true" class="write-drawer__tiptap" />
              </template>
              <p v-else-if="article?.summary" class="write-drawer__summary">{{ article.summary }}</p>
              <p v-else class="write-drawer__empty-sm">分析中，請稍候…</p>
            </section>
          </template>
        </div>
      </aside>
    </main>

  </div>
</template>

<style scoped>
/* ─── Page shell ─── */
.write-page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--bg);
}

/* ─── Main area ─── */
.write-main {
  display: flex;
  flex: 1;
}

.write-editor-body {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* ─── 左側大綱 ─── */
.write-outline {
  position: fixed;
  top: 96px;
  left: 0;
  bottom: 0;
  width: 260px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border);
  background: var(--bg);
  overflow: visible;
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.08);
  transform: translateX(-100%);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  animation: adjust-top linear both;
  animation-timeline: scroll(root);
  animation-range: 0px 52px;
  z-index: 10;
}
.write-outline--open {
  transform: translateX(0);
}

.write-outline-toggle {
  position: absolute;
  top: 50%;
  right: -22px;
  transform: translateY(-50%);
  z-index: 1;
  width: 22px;
  height: 48px;
  background: var(--surface);
  color: var(--text-mid);
  cursor: pointer;
  border: 1px solid var(--border);
  border-left: none;
  border-radius: 0 10px 10px 0;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, color 0.15s;
}
.write-outline-toggle:hover { background: var(--surface2); color: var(--text); }
.write-outline-toggle:active {
  background: var(--accent);
  color: var(--accent-fg);
  border-color: var(--accent);
}

.write-outline__head {
  display: flex;
  align-items: center;
  padding: 16px 18px 14px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.write-outline__title {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 500;
  color: var(--text-dim);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.write-outline__body {
  padding: 12px 0;
  overflow-y: auto;
  flex: 1;
}

.write-outline__empty {
  margin: 0;
  padding: 0 18px;
  font-size: 13px;
  color: var(--text-dim);
  font-style: italic;
}

.write-outline__nav {
  display: flex;
  flex-direction: column;
}

.write-outline__item {
  display: block;
  width: 100%;
  background: none;
  border: none;
  text-align: left;
  font-size: 12.5px;
  color: var(--text-mid);
  padding: 5px 18px;
  cursor: pointer;
  line-height: 1.5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  border-radius: 0;
  transition: background 0.1s, color 0.1s;
}
.write-outline__item:hover { background: var(--surface2); color: var(--text); }
.write-outline__item--h1 { padding-left: 14px; font-weight: 600; font-size: 13px; color: var(--text); }
.write-outline__item--h2 { padding-left: 22px; font-weight: 500; }
.write-outline__item--h3 { padding-left: 30px; font-size: 12px; }
.write-outline__item--h4 { padding-left: 38px; font-size: 11.5px; color: var(--text-dim); }

/* ─── AI 分析抽屜（桌面：flow item；手機：fixed overlay） ─── */
@keyframes adjust-top {
  from {
    /* 捲動最上方時：44px + 52px = 96px */
    top: 96px; 
  }
  to {
    /* 捲動超過 52px 後，頂部固定在 44px */
    top: 44px; 
  }
}
.write-drawer {
  position: fixed;
  top: 96px; /* fallback：scroll animation 會覆蓋此值 */
  right: 0;
  bottom: 0;
  width: 360px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-left: 1px solid var(--border);
  background: var(--bg);
  overflow: visible; /* handle 需要往左突出 */
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.08);
  transform: translateX(100%);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  animation: adjust-top linear both;
  animation-timeline: scroll(root); /* 監聽整個網頁的滾動 */
  animation-range: 0px 52px;       /* 動畫只在滾動 0 到 52px 之間發生 */
}
.write-drawer--open {
  transform: translateX(0);
}
/* 讓抽屜內容本身可以 scroll */
.write-drawer__body,
.write-drawer__head {
  overflow-y: auto;
}

.write-drawer__head {
  display: flex;
  align-items: center;
  padding: 16px 18px 14px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.write-drawer__title {
  flex: 1;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 500;
  color: var(--text-dim);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.write-drawer__close {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: var(--text-dim);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 5px;
  transition: background 0.12s, color 0.12s;
}
.write-drawer__close:hover { background: var(--surface2); color: var(--text); }

.write-drawer__body {
  padding: 20px 18px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.write-drawer__section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.write-drawer__section-label {
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--text-dim);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.write-drawer__summary {
  margin: 0;
  font-size: 13.5px;
  color: var(--text-mid);
  line-height: 1.75;
}

.write-drawer__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.write-drawer__tags-pending-label {
  width: 100%;
  font-size: 10px;
  color: var(--text-dim);
  font-family: var(--font-mono);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 2px;
}

.write-drawer__tag {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  padding: 3px 6px 3px 10px;
  border-radius: 20px;
  background: var(--accent-dim);
  color: var(--accent);
  border: 1px solid var(--accent-bdr);
  font-family: var(--font-mono);
}

.write-drawer__tag--pending {
  background: var(--surface2);
  color: var(--text-mid);
  border-color: var(--border2);
  border-style: dashed;
}

.write-drawer__tag-confirm,
.write-drawer__tag-remove {
  background: none;
  border: none;
  padding: 0 2px;
  cursor: pointer;
  font-size: 11px;
  line-height: 1;
  border-radius: 3px;
  transition: color 0.1s, background 0.1s;
}
.write-drawer__tag-confirm { color: var(--accent); }
.write-drawer__tag-confirm:hover { background: var(--accent-dim); }
.write-drawer__tag-remove { color: var(--text-dim); }
.write-drawer__tag-remove:hover { color: var(--danger); background: var(--danger-dim, color-mix(in srgb, var(--danger) 10%, transparent)); }

.write-drawer__tag-add {
  font-size: 12px;
  padding: 3px 8px;
  border-radius: 20px;
  background: transparent;
  color: var(--text-dim);
  border: 1px dashed var(--border2);
  font-family: var(--font-mono);
  cursor: pointer;
  transition: color 0.12s, border-color 0.12s;
}
.write-drawer__tag-add:hover { color: var(--accent); border-color: var(--accent-bdr); }
.write-drawer__tag-add:disabled { opacity: 0.5; cursor: not-allowed; }

.write-drawer__tag-input {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 20px;
  background: var(--surface2);
  color: var(--text);
  border: 1px solid var(--accent-bdr);
  font-family: var(--font-mono);
  outline: none;
  width: 100px;
}

.write-drawer__empty {
  margin: 0;
  font-size: 13px;
  color: var(--text-dim);
  line-height: 1.7;
}

.write-drawer__empty-sm {
  margin: 0;
  font-size: 12.5px;
  color: var(--text-dim);
  font-style: italic;
}

/* TiptapEditor 在抽屜內的樣式收斂 */
.write-drawer__tiptap :deep(.tiptap-wrap) {
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-mid);
}
.write-drawer__tiptap :deep(.tiptap-wrap--edit .ProseMirror),
.write-drawer__tiptap :deep(.ProseMirror) {
  border: none;
  border-radius: 0;
  padding: 0;
  outline: none;
}
.write-drawer__tiptap :deep(p) { margin: 0 0 0.4em; }
.write-drawer__tiptap :deep(h1),
.write-drawer__tiptap :deep(h2),
.write-drawer__tiptap :deep(h3) {
  font-size: 13px;
  font-weight: 600;
  margin: 0.6em 0 0.2em;
}
.write-drawer__tiptap :deep(ul),
.write-drawer__tiptap :deep(ol) {
  padding-left: 1.2em;
  margin: 0.2em 0;
}
.write-drawer__tiptap :deep(.ProseMirror > *:hover) { background: transparent; }


/* ─── 右邊緣 drawer handle（黏在抽屜左緣，跟著滑動） ─── */
.write-panel-toggle {
  position: absolute;
  top: 50%;
  left: -22px;
  transform: translateY(-50%);
  z-index: 1;
  width: 22px;
  height: 48px;
  background: var(--surface);
  color: var(--text-mid);
  cursor: pointer;
  border: 1px solid var(--border);
  border-right: none;
  border-radius: 10px 0 0 10px;
  box-shadow: -2px 0 8px rgba(0, 0, 0, 0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, color 0.15s;
}
.write-panel-toggle:hover { background: var(--surface2); color: var(--text); }
.write-panel-toggle:active {
  background: var(--accent);
  color: var(--accent-fg);
  border-color: var(--accent);
}
/* 小綠點提示有結果 */
.write-panel-toggle--dot::after {
  content: '';
  position: absolute;
  top: 8px;
  right: 5px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
  border: 1.5px solid var(--surface);
}

/* ─── Top bar ─── */
.write-bar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
  height: 44px;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
}

.write-bar__back {
  display: flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: none;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-mid);
  cursor: pointer;
  transition: background 0.12s, color 0.12s;
  white-space: nowrap;
}
.write-bar__back:hover { background: var(--surface2); color: var(--text); }

.write-bar__meta {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.write-bar__dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.write-bar__dot--draft { background: var(--text-dim); }
.write-bar__dot--pub   { background: var(--accent); }

.write-bar__label {
  font-size: 12px;
  color: var(--text-mid);
  font-family: var(--font-mono);
}

.write-bar__save {
  font-size: 11.5px;
  color: var(--text-dim);
  font-family: var(--font-mono);
}
.write-bar__save--ok  { color: var(--accent); }
.write-bar__save--err { color: var(--danger); }

.write-bar__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

/* Public toggle pill */
.write-bar__pill {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--surface2);
  border: 1px solid var(--border2);
  border-radius: 20px;
  padding: 3px 10px 3px 4px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.write-bar__pill--on {
  background: var(--accent-dim);
  border-color: var(--accent-bdr);
}
.write-bar__pill-knob {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--text-dim);
  transition: background 0.15s;
  flex-shrink: 0;
}
.write-bar__pill--on .write-bar__pill-knob { background: var(--accent); }
.write-bar__pill-label {
  font-size: 12px;
  color: var(--text-mid);
  font-family: var(--font-mono);
  white-space: nowrap;
}
.write-bar__pill--on .write-bar__pill-label { color: var(--accent); }

/* Archive button */
.write-bar__archive {
  background: var(--danger);
  color: #fff;
  border: none;
  border-radius: 7px;
  padding: 5px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
  white-space: nowrap;
}
.write-bar__archive:disabled { opacity: 0.5; cursor: not-allowed; }
.write-bar__archive:not(:disabled):hover { opacity: 0.88; }

/* Publish button */
.write-bar__publish {
  background: var(--accent);
  color: var(--accent-fg);
  border: none;
  border-radius: 7px;
  padding: 5px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
  white-space: nowrap;
}
.write-bar__publish:disabled { opacity: 0.5; cursor: not-allowed; }
.write-bar__publish:not(:disabled):hover { opacity: 0.88; }

/* ─── Loading / Error centers ─── */
.write-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  flex: 1;
  min-height: calc(100vh - 100px);
  color: var(--text-dim);
}
.write-center__msg { margin: 0; font-size: 14px; }


/* ─── Cover ─── */
.write-cover {
  position: relative;
  width: 100%;
  height: 49px;
  background: transparent;
  cursor: pointer;
  overflow: hidden;
  flex-shrink: 0;
  transition: height 0.2s ease;
}
.write-cover--has-img {
  height: 260px;
  background: var(--surface2);
}

.write-cover__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.3s;
}
.write-cover:hover .write-cover__img { transform: scale(1.01); }

/* Empty state */
.write-cover__empty {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0;
  font-size: 12.5px;
  color: var(--text-dim);
  border-bottom: 1px dashed var(--border2);
  transition: color 0.15s, background 0.15s;
}
.write-cover:hover .write-cover__empty {
  color: var(--text-mid);
  background: var(--surface2);
}

/* Hover overlay when has image */
.write-cover__overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,0.35);
  display: flex;
  align-items: flex-end;
  justify-content: flex-end;
  gap: 8px;
  padding: 14px 18px;
  opacity: 0;
  transition: opacity 0.2s;
}
.write-cover:hover .write-cover__overlay { opacity: 1; }

.write-cover__change,
.write-cover__delete {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(255,255,255,0.15);
  backdrop-filter: blur(6px);
  border: 1px solid rgba(255,255,255,0.25);
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 12px;
  color: #fff;
  font-weight: 500;
  cursor: pointer;
}
.write-cover__delete {
  background: rgba(220, 38, 38, 0.45);
  border-color: rgba(220, 38, 38, 0.5);
}
.write-cover__delete:hover {
  background: rgba(220, 38, 38, 0.65);
}

.write-cover__input { display: none; }

/* ─── Content ─── */
.write-content {
  margin: 0px 360px 0px 300px;
  padding: 48px;
}

/* ─── Title textarea ─── */
.write-title {
  display: block;
  width: 100%;
  background: transparent;
  border: none;
  outline: none;
  resize: none;
  overflow: hidden;
  font-family: var(--font-brand);
  font-size: 2.6rem;
  font-weight: 700;
  color: var(--text);
  line-height: 1.2;
  letter-spacing: -0.01em;
  padding: 0;
  margin-bottom: 32px;
}
.write-title::placeholder { color: var(--text-dim); opacity: 0.45; }

/* ─── Body editor – override TiptapEditor styles ─── */
.write-body :deep(.tiptap-wrap) {
  font-size: 16px;
  line-height: 1.75;
  color: var(--text);
}

/* Remove the border that TiptapEditor adds in edit mode */
.write-body :deep(.tiptap-wrap--edit .ProseMirror) {
  border: none;
  border-radius: 0;
  padding: 0;
  min-height: 40vh;
}

.write-body :deep(.ProseMirror) { outline: none; }

/* Paragraphs */
.write-body :deep(p) {
  margin: 0 0 0.25em;
  color: var(--text);
  opacity: 1;
}

/* Headings – Notion style */
.write-body :deep(h1) {
  font-family: var(--font-brand);
  font-size: 1.875em;
  font-weight: 700;
  color: var(--text);
  margin: 1.4em 0 0.1em;
  letter-spacing: -0.01em;
  line-height: 1.25;
}
.write-body :deep(h2) {
  font-family: var(--font-brand);
  font-size: 1.375em;
  font-weight: 600;
  color: var(--text);
  margin: 1.4em 0 0.1em;
  letter-spacing: -0.005em;
  line-height: 1.3;
}
.write-body :deep(h3) {
  font-family: var(--font-brand);
  font-size: 1.125em;
  font-weight: 600;
  color: var(--text);
  margin: 1.2em 0 0.1em;
  line-height: 1.35;
}

/* Bold / italic */
.write-body :deep(strong) { font-weight: 700; color: var(--text); }
.write-body :deep(em) { font-style: italic; }

/* Lists — marker 往內，不超出 block 邊界 */
.write-body :deep(ul),
.write-body :deep(ol) {
  padding-left: 1.5em;
  margin: 0.2em 0 0.4em;
  /* 取消 block hover 的 negative margin，避免 marker 跑出去 */
  margin-left: 0 !important;
  list-style-position: inside;
}
.write-body :deep(li) {
  margin: 0.15em 0;
  color: var(--text);
  opacity: 1;
}
.write-body :deep(li::marker) { color: var(--text-mid); }
.write-body :deep(li p) { margin: 0; display: inline; }

/* Inline code */
.write-body :deep(code) {
  font-family: var(--font-mono);
  font-size: 0.85em;
  background: var(--surface2);
  border: 1px solid var(--border2);
  border-radius: 4px;
  padding: 0.1em 0.4em;
  color: var(--accent);
}

/* Code block */
.write-body :deep(pre) {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px 18px;
  margin: 0.75em 0;
  overflow-x: auto;
}
.write-body :deep(pre code) {
  background: none;
  border: none;
  padding: 0;
  color: var(--text);
  font-size: 0.875em;
  line-height: 1.6;
}

/* Blockquote */
.write-body :deep(blockquote) {
  border-left: 3px solid var(--accent-bdr);
  margin: 0.75em 0;
  padding: 0.25em 0 0.25em 1.1em;
  color: var(--text-mid);
}
.write-body :deep(blockquote p) { color: var(--text-mid); }

/* Horizontal rule */
.write-body :deep(hr) {
  border: none;
  border-top: 1px solid var(--border2);
  margin: 1.5em 0;
}

/* Block hover highlight – Notion 風格 */
.write-body :deep(.ProseMirror > *) {
  border-radius: 4px;
  padding-left: 4px;
  padding-right: 4px;
  margin-left: -4px;
  margin-right: -4px;
  transition: background 0.08s;
}
.write-body :deep(.ProseMirror > *:hover) {
  background: var(--surface2);
}

/* Placeholder */
.write-body :deep(.ProseMirror p.is-editor-empty:first-child::before) {
  content: attr(data-placeholder);
  color: var(--text-dim);
  opacity: 0.5;
  pointer-events: none;
  float: left;
  height: 0;
}

/* ─── Spinner ─── */
.write-spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2px solid var(--border2);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.65s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ─── Responsive ─── */
@media (max-width: 768px) {
  .write-content { padding: 32px 20px 80px 20px; }
  .write-title { font-size: 1.9rem; }
  .write-cover--has-img { height: 180px; }
  .write-cover__empty { padding: 0 20px; }
  .write-bar__back span { display: none; }

  .write-drawer {
    position: fixed;
    top: 44px;
    right: 0;
    bottom: 0;
    z-index: 30;
    width: 280px;
  }
}
</style>
