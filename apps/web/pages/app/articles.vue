<script setup lang="ts">
definePageMeta({ ssr: false })

const { listArticles } = useArticles()
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

function openArticle(id: string) {
  router.push(`/app/write/${id}?from=/app/articles`)
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
        @click="openArticle(article.id)"
      >
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

.articles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.article-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s, box-shadow 0.15s;
  padding: 0;
}

.article-card:hover {
  border-color: var(--accent);
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
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
</style>
