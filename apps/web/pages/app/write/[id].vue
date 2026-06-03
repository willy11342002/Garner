<script setup lang="ts">
import type { Item } from '~/types/api'

definePageMeta({ ssr: false })

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
      try { editorContent.value = JSON.parse(data.content_md) } catch { /* raw text, ignore */ }
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
    setTimeout(() => { if (saveStatus.value === 'saved') saveStatus.value = 'idle' }, 2000)
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

// cover image
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
    <header class="write-topbar">
      <button class="write-topbar__back btn btn--ghost" @click="router.push('/app')">← 返回</button>
      <div class="write-topbar__center">
        <span class="write-topbar__status" :class="`write-topbar__status--${isDraft ? 'draft' : 'published'}`">
          {{ isDraft ? '草稿' : '已發布' }}
        </span>
        <span class="write-topbar__save">
          <template v-if="saveStatus === 'saving'">儲存中...</template>
          <template v-else-if="saveStatus === 'saved'">已儲存</template>
          <template v-else-if="saveStatus === 'error'">儲存失敗</template>
        </span>
      </div>
      <div class="write-topbar__right">
        <label class="write-topbar__public-toggle" :class="{ 'write-topbar__public-toggle--on': isPublic }">
          <input type="checkbox" :checked="isPublic" @change="togglePublic" />
          {{ isPublic ? '公開' : '私有' }}
        </label>
        <button
          class="btn btn--accent"
          :disabled="publishing"
          @click="handlePublish"
        >{{ publishing ? '發布中...' : isDraft ? '發布' : '重新發布' }}</button>
      </div>
    </header>

    <div v-if="loading" class="write-loading">
      <span class="write-spinner"></span>
    </div>

    <div v-else-if="loadError" class="write-loading">
      <p>載入失敗</p>
      <NuxtLink to="/app" class="btn btn--ghost">← 返回</NuxtLink>
    </div>

    <main v-else class="write-body">
      <!-- Cover image -->
      <div class="write-cover" @click="coverInput?.click()">
        <img v-if="article?.thumbnail_url" :src="article.thumbnail_url" class="write-cover__img" alt="封面" />
        <div v-else class="write-cover__placeholder">
          <span v-if="coverUploading" class="write-spinner"></span>
          <span v-else>＋ 新增封面圖</span>
        </div>
        <input
          ref="coverInput"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          class="write-cover__input"
          @change="handleCoverChange"
        />
      </div>

      <!-- Title -->
      <input
        v-model="title"
        class="write-title"
        placeholder="文章標題"
        maxlength="200"
      />

      <div class="write-divider"></div>

      <!-- Body editor -->
      <div class="write-editor">
        <TiptapEditor v-model="editorContent" />
      </div>
    </main>
  </div>
</template>

<style scoped>
.write-page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--bg);
}

/* Top bar */
.write-topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px;
  height: 52px;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
}

.write-topbar__center {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
}

.write-topbar__status {
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
  letter-spacing: 0.04em;
}
.write-topbar__status--draft {
  background: var(--surface2);
  color: var(--text-dim);
}
.write-topbar__status--published {
  background: color-mix(in srgb, var(--accent) 15%, transparent);
  color: var(--accent);
}

.write-topbar__save {
  font-size: 12px;
  color: var(--text-dim);
  font-family: var(--font-mono);
}

.write-topbar__right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.write-topbar__public-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-dim);
  cursor: pointer;
  user-select: none;
}
.write-topbar__public-toggle input { display: none; }
.write-topbar__public-toggle--on { color: var(--accent); }

/* Body */
.write-body {
  max-width: 720px;
  width: 100%;
  margin: 0 auto;
  padding: 32px 24px 80px;
  display: flex;
  flex-direction: column;
  gap: 0;
}

/* Cover */
.write-cover {
  width: 100%;
  height: 220px;
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  margin-bottom: 28px;
  background: var(--surface2);
  border: 1px dashed var(--border2);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.15s;
}
.write-cover:hover { border-color: var(--accent-bdr); }
.write-cover__img { width: 100%; height: 100%; object-fit: cover; }
.write-cover__placeholder {
  font-size: 14px;
  color: var(--text-dim);
}
.write-cover__input { display: none; }

/* Title */
.write-title {
  width: 100%;
  background: transparent;
  border: none;
  outline: none;
  font-family: var(--font-brand);
  font-size: 2rem;
  font-weight: 700;
  color: var(--text);
  line-height: 1.3;
  padding: 0;
  margin-bottom: 16px;
  resize: none;
}
.write-title::placeholder { color: var(--text-dim); opacity: 0.5; }

.write-divider {
  height: 1px;
  background: var(--border);
  margin-bottom: 24px;
}

.write-editor { flex: 1; }

/* Loading */
.write-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  flex: 1;
  min-height: calc(100vh - 52px);
  color: var(--text-dim);
}

.write-spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2px solid var(--border2);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
