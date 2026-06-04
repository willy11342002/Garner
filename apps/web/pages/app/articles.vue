<script setup lang="ts">
definePageMeta({ ssr: false })
useHead({ title: 'Vela — 我的文章' })

const { listArticles, publishArticle } = useArticles()
const apiFetch = useApiFetch()
const router = useRouter()

const articles = ref<Awaited<ReturnType<typeof listArticles>>>([])
const loading = ref(true)

onMounted(async () => {
  try {
    articles.value = await listArticles()
  } finally {
    loading.value = false
  }
})

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('zh-TW', { year: 'numeric', month: 'short', day: 'numeric' })
}

// ── 選擇模式 ──────────────────────────────────────────────────────────────────
const selecting = ref(false)
const selected = ref<Set<string>>(new Set())

function toggleSelect(id: string) {
  const s = new Set(selected.value)
  if (s.has(id)) { s.delete(id) } else { s.add(id) }
  selected.value = s
}

function enterSelectMode() {
  selecting.value = true
}

function exitSelectMode() {
  selecting.value = false
  selected.value = new Set()
}

function handleCardClick(id: string) {
  if (selecting.value) {
    toggleSelect(id)
  } else {
    router.push(`/app/write/${id}?from=/app/articles`)
  }
}

// ── 批次 AI 分析 ──────────────────────────────────────────────────────────────
const analyzing = ref(false)

async function batchAnalyze() {
  if (analyzing.value) return
  analyzing.value = true
  try {
    await Promise.allSettled([...selected.value].map(id => publishArticle(id)))
    articles.value = await listArticles()
    exitSelectMode()
  } finally {
    analyzing.value = false
  }
}

// ── 批次封存 ──────────────────────────────────────────────────────────────────
const archiving = ref(false)

async function batchArchive() {
  if (archiving.value) return
  archiving.value = true
  try {
    await Promise.allSettled(
      [...selected.value].map(id => apiFetch(`/items/${id}`, { method: 'PATCH', body: { status: 'archived' } }))
    )
    articles.value = articles.value.filter(a => !selected.value.has(a.id))
    exitSelectMode()
  } finally {
    archiving.value = false
  }
}
</script>

<template>
  <main class="shell articles-page">
    <header class="articles-head">
      <span class="eyebrow">ARTICLES</span>
      <h1 class="page-title">我的文章</h1>
      <p class="articles-head__desc">你在 Vela 建立的所有文章</p>
    </header>

    <div class="articles-toolbar">
      <button class="btn btn--accent" @click="router.push('/app/write')">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
        新增文章
      </button>
      <button class="btn btn--ghost" :class="{ 'btn--ghost-active': selecting }" @click="selecting ? exitSelectMode() : enterSelectMode()">
        {{ selecting ? '取消選擇' : '選擇' }}
      </button>
    </div>

    <div v-if="loading" class="articles-grid">
      <div v-for="n in 6" :key="n" class="article-card article-card--skel">
        <div class="article-card__cover placeholder"><div class="placeholder__stripes"></div></div>
        <div class="article-card__body">
          <div class="article-card__skel-title"></div>
          <div class="article-card__skel-meta"></div>
        </div>
      </div>
    </div>

    <div v-else-if="articles.length === 0" class="articles-empty">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
      <p>還沒有文章，點「新增文章」開始寫作</p>
    </div>

    <div v-else class="articles-grid">
      <button
        v-for="article in articles"
        :key="article.id"
        class="article-card"
        :class="{ 'article-card--selected': selected.has(article.id), 'article-card--selecting': selecting }"
        @click="handleCardClick(article.id)"
      >
        <!-- 選取勾勾（只在選擇模式顯示） -->
        <div v-if="selecting" class="article-card__check" @click.stop="toggleSelect(article.id)">
          <svg v-if="selected.has(article.id)" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><polyline points="20 6 9 17 4 12"/></svg>
        </div>

        <div class="article-card__cover">
          <img v-if="article.thumbnail_url" :src="article.thumbnail_url" alt="">
          <div v-else class="placeholder placeholder--b"><div class="placeholder__stripes"></div></div>
        </div>
        <div class="article-card__body">
          <span class="article-card__status" :class="article.is_draft ? 'article-card__status--draft' : 'article-card__status--pub'">
            {{ article.is_draft ? '草稿' : '已發布' }}
          </span>
          <h3 class="article-card__title">{{ article.title || '未命名文章' }}</h3>
          <span class="article-card__date mono">{{ formatDate(article.saved_at) }}</span>
        </div>
      </button>
    </div>

    <!-- 批次操作 floating bar -->
    <Transition name="batch-bar">
      <div v-if="selecting" class="batch-bar">
        <span class="batch-bar__count">已選 {{ selected.size }} 篇</span>
        <div class="batch-bar__actions">
          <button class="batch-bar__btn batch-bar__btn--ghost" @click="exitSelectMode">取消</button>
          <button class="batch-bar__btn batch-bar__btn--analyze" :disabled="analyzing" @click="batchAnalyze">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/></svg>
            {{ analyzing ? '分析中…' : '保存' }}
          </button>
          <button class="batch-bar__btn batch-bar__btn--archive" :disabled="archiving" @click="batchArchive">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="21 8 21 21 3 21 3 8"/><rect x="1" y="3" width="22" height="5"/><line x1="10" y1="12" x2="14" y2="12"/></svg>
            {{ archiving ? '封存中…' : '封存' }}
          </button>
        </div>
      </div>
    </Transition>
  </main>
</template>

<style scoped>
.articles-page {
  padding: 32px 24px 64px;
  max-width: 1100px;
  margin: 0 auto;
}

.articles-head {
  margin-bottom: 28px;
}

.articles-head__desc {
  color: var(--text-mid);
  font-size: 14px;
  margin-top: 4px;
}

.articles-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
}

.btn--ghost-active {
  background: var(--surface2);
  color: var(--text);
}

.articles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

/* ── Card ── */
.article-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s, box-shadow 0.15s;
  padding: 0;
  position: relative;
}

.article-card:hover {
  border-color: var(--accent);
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}

.article-card--selected {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--accent-bdr);
}

.article-card--selecting {
  cursor: default;
}

/* ── 選取勾勾 ── */
.article-card__check {
  position: absolute;
  top: 8px;
  left: 8px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 1.5px solid rgba(255, 255, 255, 0.7);
  background: rgba(0, 0, 0, 0.25);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
  transition: background 0.12s, border-color 0.12s;
  color: #fff;
}

.article-card--selected .article-card__check {
  background: var(--accent);
  border-color: var(--accent);
}

.article-card__cover {
  width: 100%;
  aspect-ratio: 16/9;
  overflow: hidden;
  background: var(--surface-2, var(--bg-2));
}

.article-card__cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.article-card__body {
  padding: 12px 14px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.article-card__status {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 2px 6px;
  border-radius: 4px;
  align-self: flex-start;
}

.article-card__status--draft {
  background: var(--surface-2, rgba(128,128,128,0.12));
  color: var(--text-mid);
}

.article-card__status--pub {
  background: rgba(34,197,94,0.12);
  color: #16a34a;
}

.article-card__title {
  font-size: 14px;
  font-weight: 600;
  line-height: 1.35;
  color: var(--text);
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.article-card__date {
  font-size: 11px;
  color: var(--text-mid);
}

.article-card--skel .article-card__skel-title {
  height: 14px;
  background: var(--surface-2, rgba(128,128,128,0.1));
  border-radius: 4px;
  width: 75%;
  animation: pulse 1.4s ease-in-out infinite;
}

.article-card--skel .article-card__skel-meta {
  height: 11px;
  background: var(--surface-2, rgba(128,128,128,0.1));
  border-radius: 4px;
  width: 45%;
  margin-top: 4px;
  animation: pulse 1.4s ease-in-out infinite;
}

.articles-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 64px 0;
  color: var(--text-mid);
}

.articles-empty p {
  font-size: 14px;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* ── 批次操作 floating bar ── */
.batch-bar {
  position: fixed;
  bottom: 28px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 50;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--bg);
  border: 1px solid var(--border2);
  border-radius: 14px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
  white-space: nowrap;
}

.batch-bar__count {
  font-size: 12.5px;
  color: var(--text-mid);
  font-family: var(--font-mono);
  padding-right: 6px;
  border-right: 1px solid var(--border2);
}

.batch-bar__actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.batch-bar__btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: opacity 0.15s, background 0.15s;
}
.batch-bar__btn:disabled { opacity: 0.5; cursor: not-allowed; }

.batch-bar__btn--ghost {
  background: transparent;
  border-color: var(--border2);
  color: var(--text-mid);
}
.batch-bar__btn--ghost:hover { background: var(--surface2); }

.batch-bar__btn--analyze {
  background: var(--accent-dim);
  border-color: var(--accent-bdr);
  color: var(--accent);
}
.batch-bar__btn--analyze:not(:disabled):hover { opacity: 0.85; }

.batch-bar__btn--archive {
  background: rgba(234, 179, 8, 0.1);
  border-color: rgba(234, 179, 8, 0.25);
  color: #b45309;
}
.batch-bar__btn--archive:not(:disabled):hover { opacity: 0.85; }

/* floating bar 動畫 */
.batch-bar-enter-active,
.batch-bar-leave-active {
  transition: transform 0.22s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.18s ease;
}
.batch-bar-enter-from,
.batch-bar-leave-to {
  transform: translateX(-50%) translateY(16px);
  opacity: 0;
}
.batch-bar-enter-to,
.batch-bar-leave-from {
  transform: translateX(-50%) translateY(0);
  opacity: 1;
}
</style>
