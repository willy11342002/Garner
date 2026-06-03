<script setup lang="ts">
import type { Item } from '~/types/api'

definePageMeta({ ssr: false, layout: 'write' })

const route = useRoute()
const router = useRouter()
const id = route.params.id as string

const { updateArticle, publishArticle, uploadCover } = useArticles()
const apiFetch = useApiFetch()

const article = ref<Item | null>(null)
const loading = ref(true)
const loadError = ref(false)

const title = ref('')
const editorContent = ref<Record<string, unknown>>({ type: 'doc', content: [] })
const isPublic = ref(false)
const isDraft = ref(true)

const saveStatus = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
const publishing = ref(false)

let saveTimer: ReturnType<typeof setTimeout> | null = null

onMounted(async () => {
  try {
    const data: Item = await apiFetch(`/articles/${id}`)
    article.value = data
    title.value = data.title ?? ''
    isPublic.value = data.is_public
    isDraft.value = data.is_draft
    if (data.content_md) {
      try { editorContent.value = JSON.parse(data.content_md) } catch { /* ignore */ }
    }
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
})

function scheduleSave() {
  if (saveTimer) clearTimeout(saveTimer)
  saveStatus.value = 'saving'
  saveTimer = setTimeout(doSave, 1500)
}

async function doSave() {
  try {
    await updateArticle(id, {
      title: title.value || '未命名文章',
      content_md: JSON.stringify(editorContent.value),
      is_public: isPublic.value,
    })
    saveStatus.value = 'saved'
    setTimeout(() => { if (saveStatus.value === 'saved') saveStatus.value = 'idle' }, 2500)
  } catch {
    saveStatus.value = 'error'
  }
}

watch(title, scheduleSave)
watch(editorContent, scheduleSave, { deep: true })

async function togglePublic() {
  isPublic.value = !isPublic.value
  await updateArticle(id, { is_public: isPublic.value })
}

async function handlePublish() {
  if (publishing.value) return
  publishing.value = true
  if (saveTimer) { clearTimeout(saveTimer); await doSave() }
  try {
    const updated = await publishArticle(id)
    isDraft.value = updated.is_draft
    article.value = updated
  } finally {
    publishing.value = false
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

onBeforeUnmount(() => { if (saveTimer) clearTimeout(saveTimer) })
</script>

<template>
  <div class="write-page">

    <!-- Top bar -->
    <header class="write-bar">
      <button class="write-bar__back" @click="router.push('/app')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg>
        首頁
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

        <button
          class="write-bar__publish"
          :disabled="publishing"
          @click="handlePublish"
        >{{ publishing ? '發布中…' : isDraft ? '發布文章' : '重新發布' }}</button>
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

    <!-- Editor -->
    <main v-else class="write-main">

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

/* ─── Main layout ─── */
.write-main {
  display: flex;
  flex-direction: column;
  flex: 1;
}

/* ─── Cover ─── */
.write-cover {
  position: relative;
  width: 100%;
  height: 260px;
  background: var(--surface2);
  cursor: pointer;
  overflow: hidden;
  flex-shrink: 0;
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
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-dim);
  border-bottom: 1px dashed var(--border2);
  transition: color 0.15s, background 0.15s;
}
.write-cover:hover .write-cover__empty {
  color: var(--text-mid);
  background: var(--surface3);
}

/* Hover overlay when has image */
.write-cover__overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,0.35);
  display: flex;
  align-items: flex-end;
  justify-content: flex-end;
  padding: 14px 18px;
  opacity: 0;
  transition: opacity 0.2s;
}
.write-cover:hover .write-cover__overlay { opacity: 1; }

.write-cover__change {
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
}

.write-cover__input { display: none; }

/* ─── Content ─── */
.write-content {
  max-width: 760px;
  width: 100%;
  margin: 0 auto;
  /* 左側 96px：handle 28px + 間距，右側對稱 64px */
  padding: 48px 64px 120px 96px;
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
  .write-cover { height: 180px; }
  .write-bar__back span { display: none; }
}
</style>
