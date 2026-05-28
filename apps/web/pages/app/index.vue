<script setup lang="ts">
import type { Item, Tag } from '~/types/api'

const itemStore = useItemStore()
const { getItemTags } = useItems()

const loading = ref(true)
const itemTagsMap = ref<Record<string, Tag[]>>({})

// URL quick-save (empty state CTA)
const newUrl = ref('')
const saving = ref(false)
const saveError = ref('')

const heroItem = computed(() => itemStore.items[0] ?? null)

const heroTags = computed(() =>
  heroItem.value ? (itemTagsMap.value[heroItem.value.id] ?? []) : []
)

const tagGroups = computed(() => {
  const groups = new Map<string, { tag: Tag; items: Item[] }>()
  for (const item of itemStore.items) {
    for (const tag of itemTagsMap.value[item.id] ?? []) {
      if (!groups.has(tag.id)) groups.set(tag.id, { tag, items: [] })
      groups.get(tag.id)!.items.push(item)
    }
  }
  return [...groups.values()]
})

const untaggedItems = computed(() =>
  itemStore.items.filter(item => (itemTagsMap.value[item.id] ?? []).length === 0)
)

const TAG_COLORS = ['a', 'b', 'c', 'd', 'e'] as const

function tagColor(i: number) {
  return TAG_COLORS[i % TAG_COLORS.length]
}

function sourceLabel(url: string) {
  if (/youtu/.test(url)) return '▶ YouTube'
  if (/instagram\.com/.test(url)) return 'IG'
  return 'Article'
}

function daysSince(dateStr: string) {
  return Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000)
}

function relativeTime(dateStr: string) {
  const d = daysSince(dateStr)
  if (d === 0) return 'today'
  if (d === 1) return '1d ago'
  return `${d}d ago`
}

async function quickSave() {
  const url = newUrl.value.trim()
  if (!url) return
  saving.value = true
  saveError.value = ''
  try {
    const item = await itemStore.add({ url })
    newUrl.value = ''
    itemTagsMap.value[item.id] = await getItemTags(item.id)
  } catch {
    saveError.value = '儲存失敗，請確認 URL 格式是否正確'
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await itemStore.load()
  await Promise.all(
    itemStore.items.map(async item => {
      itemTagsMap.value[item.id] = await getItemTags(item.id)
    })
  )
  loading.value = false
})
</script>

<template>
  <main class="shell">
    <!-- Loading -->
    <div v-if="loading" class="loading-state">載入中...</div>

    <!-- Empty: Ghost Preview + CTA -->
    <template v-else-if="itemStore.items.length === 0">
      <!-- Ghost Hero -->
      <section class="hero hero--empty fadeup">
        <div class="hero__media">
          <div class="placeholder placeholder--b">
            <div class="placeholder__stripes"></div>
          </div>
        </div>
        <div class="hero__body hero__cta">
          <span class="hero__eyebrow">WELCOME TO VELA</span>
          <h1 class="hero__title">你的知識庫還是空的</h1>
          <p class="hero__summary">存入第一筆內容，知識庫就會開始自動成長。</p>
          <div class="cta-input-row">
            <input
              v-model="newUrl"
              class="cta-input"
              placeholder="貼入任何 YouTube 或網頁 URL..."
              :disabled="saving"
              @keydown.enter="quickSave"
            />
            <button class="btn btn--accent" :disabled="saving" @click="quickSave">
              {{ saving ? '存入中...' : '存入' }}
            </button>
          </div>
          <p v-if="saveError" class="cta-error">{{ saveError }}</p>
          <div class="cta-divider"><span>或</span></div>
          <a href="#" class="btn cta-ext-btn">安裝 Chrome Extension →</a>
        </div>
      </section>

    </template>

    <!-- Populated -->
    <template v-else>
      <!-- Hero -->
      <section v-if="heroItem" class="hero fadeup">
        <div class="hero__media">
          <img v-if="heroItem.thumbnail_url" :src="heroItem.thumbnail_url" class="hero__img" alt="" />
          <div v-else class="placeholder placeholder--b">
            <div class="placeholder__stripes"></div>
            <div class="placeholder__label">[ 縮圖處理中 ]</div>
          </div>
          <div class="hero__mediaTag mono" style="color:var(--text-dim); font-size:10px; letter-spacing:.08em;">
            TODAY'S REVISIT · {{ daysSince(heroItem.saved_at) }} DAYS AGO
          </div>
          <span class="source-badge hero__source">{{ sourceLabel(heroItem.url) }}</span>
        </div>
        <div class="hero__body">
          <span class="hero__eyebrow">TODAY'S REVISIT</span>
          <h1 class="hero__title">{{ heroItem.title ?? heroItem.url }}</h1>
          <p v-if="heroItem.summary" class="hero__summary">{{ heroItem.summary }}</p>
          <div v-if="heroTags.length > 0" class="hero__chips">
            <span
              v-for="(tag, i) in heroTags"
              :key="tag.id"
              :class="`tag-chip tag-chip--${tagColor(i)}`"
            >{{ tag.name }}</span>
          </div>
          <div class="hero__actions">
            <a :href="heroItem.url" target="_blank" rel="noopener" class="btn btn--accent">開啟閱讀 →</a>
          </div>
        </div>
      </section>

      <!-- Tag rows -->
      <section v-for="(group, i) in tagGroups" :key="group.tag.id" class="tagrow">
        <header class="tagrow__head">
          <span class="tagrow__dot" :style="`background:var(--tag-${tagColor(i)})`"></span>
          <span class="tagrow__name">{{ group.tag.name }}</span>
          <span class="tagrow__count">{{ group.items.length }}</span>
          <NuxtLink to="/app/share" class="tagrow__share">↗ 分享這個標籤</NuxtLink>
          <a href="#" class="tagrow__all">查看全部 →</a>
        </header>
        <div class="tagrow__scroll">
          <a
            v-for="item in group.items.slice(0, 6)"
            :key="item.id"
            class="card"
            :href="item.url"
            target="_blank"
            rel="noopener"
          >
            <div class="card__thumb">
              <img v-if="item.thumbnail_url" :src="item.thumbnail_url" class="card__img" alt="" />
              <div v-else :class="`placeholder placeholder--${tagColor(i)}`">
                <div class="placeholder__stripes"></div>
              </div>
              <span class="source-badge">{{ sourceLabel(item.url) }}</span>
            </div>
            <div class="card__body">
              <h3 class="card__title">{{ item.title ?? item.url }}</h3>
              <div class="card__footer">
                <span v-if="!item.parsed_at" class="processing-badge">AI 處理中</span>
                <span v-else :class="`tag-chip tag-chip--${tagColor(i)}`">{{ group.tag.name }}</span>
                <span class="mono">{{ relativeTime(item.saved_at) }}</span>
              </div>
            </div>
          </a>
          <a v-if="group.items.length > 6" class="card--more" href="#">查看更多 +{{ group.items.length - 6 }}</a>
        </div>
      </section>

      <!-- Untagged -->
      <section v-if="untaggedItems.length > 0" class="tagrow">
        <header class="tagrow__head">
          <span class="tagrow__dot" style="background:var(--border2)"></span>
          <span class="tagrow__name">未分類</span>
          <span class="tagrow__count">{{ untaggedItems.length }}</span>
        </header>
        <div class="tagrow__scroll">
          <a
            v-for="item in untaggedItems.slice(0, 6)"
            :key="item.id"
            class="card"
            :href="item.url"
            target="_blank"
            rel="noopener"
          >
            <div class="card__thumb">
              <img v-if="item.thumbnail_url" :src="item.thumbnail_url" class="card__img" alt="" />
              <div v-else class="placeholder placeholder--a">
                <div class="placeholder__stripes"></div>
              </div>
              <span class="source-badge">{{ sourceLabel(item.url) }}</span>
            </div>
            <div class="card__body">
              <h3 class="card__title">{{ item.title ?? item.url }}</h3>
              <div class="card__footer">
                <span v-if="!item.parsed_at" class="processing-badge">AI 處理中</span>
                <span class="mono">{{ relativeTime(item.saved_at) }}</span>
              </div>
            </div>
          </a>
        </div>
      </section>
    </template>
  </main>
</template>

<style>
/* Loading */
.loading-state {
  padding: 80px 0;
  text-align: center;
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 13px;
}

/* Empty state: tall hero fills viewport */
.hero.hero--empty {
  min-height: calc(100vh - 52px - 24px - 64px - 28px - 40px);
}
.hero.hero--empty .hero__media {
  min-height: 0;
}

/* Empty state CTA in hero body */
.hero__cta { gap: 16px; }

.cta-input-row {
  display: flex;
  gap: 8px;
}
.cta-input {
  flex: 1;
  background: var(--surface2);
  border: 1px solid var(--border2);
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 13px;
  color: var(--text);
  font-family: var(--font-ui);
  outline: none;
  transition: border-color .15s ease;
  min-width: 0;
}
.cta-input:focus { border-color: var(--accent-bdr); }
.cta-input::placeholder { color: var(--text-dim); }
.cta-input:disabled { opacity: 0.5; }

.cta-error {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 11.5px;
  color: var(--danger);
}

.cta-divider {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-dim);
}
.cta-divider::before,
.cta-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}

.cta-ext-btn {
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Thumbnail images */
.hero__img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.card__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

/* Hero */
.hero {
  position: relative;
  margin: 28px 0 40px;
  border-radius: 20px;
  overflow: hidden;
  border: 1px solid var(--border);
  background: var(--surface);
  min-height: 300px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 0.85fr);
}
.hero__media { position: relative; min-height: 300px; overflow: hidden; }
.hero__media .placeholder__label { font-size: 11px; color: rgba(255,255,255,0.55); }
body.light .hero__media .placeholder__label { color: rgba(0,0,0,0.5); }
.hero__media::after {
  content: ''; position: absolute; inset: 0;
  background: linear-gradient(90deg, transparent 0%, transparent 45%, var(--surface) 95%);
  pointer-events: none;
}
.hero__mediaTag { position: absolute; left: 18px; top: 18px; z-index: 2; }
.hero__source { position: absolute; right: 18px; bottom: 18px; z-index: 2; }
.hero__body {
  padding: 28px 32px 28px 8px;
  display: flex; flex-direction: column; justify-content: center; gap: 14px;
  position: relative; z-index: 3;
}
.hero__eyebrow { display: inline-flex; align-items: center; gap: 10px; font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.1em; }
.hero__eyebrow::before { content: ''; width: 3px; height: 12px; background: var(--accent); border-radius: 2px; }
.hero__title { font-family: var(--font-brand); font-weight: 600; font-size: 26px; line-height: 1.25; letter-spacing: -0.015em; margin: 0; max-width: 520px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.hero__summary { font-size: 13px; color: var(--text-mid); line-height: 1.75; max-width: 520px; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.hero__chips { display: flex; gap: 6px; flex-wrap: wrap; }
.hero__actions { display: flex; gap: 10px; margin-top: 4px; }

/* Tag rows */
.tagrow { margin-bottom: 36px; }
.tagrow__head { display: flex; align-items: center; padding: 0 4px 10px; border-bottom: 1px solid var(--border); margin-bottom: 14px; }
.tagrow__dot { width: 7px; height: 7px; border-radius: 50%; margin-right: 10px; flex-shrink: 0; }
.tagrow__name { font-family: var(--font-ui); font-weight: 500; font-size: 14px; color: var(--text); }
.tagrow__count { margin-left: 10px; font-family: var(--font-mono); font-size: 11.5px; color: var(--text-dim); }
.tagrow__share { margin-left: 12px; font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); padding: 2px 8px; border: 1px solid var(--border); border-radius: 12px; transition: all .15s ease; }
.tagrow__share:hover { color: var(--accent); border-color: var(--accent-bdr); }
.tagrow__all { margin-left: auto; font-family: var(--font-mono); font-size: 11.5px; color: var(--text-dim); transition: color .15s ease; }
.tagrow__all:hover { color: var(--text); }
.tagrow__scroll { display: flex; gap: 12px; overflow-x: auto; padding: 4px 4px 8px; scrollbar-width: none; }
.tagrow__scroll::-webkit-scrollbar { display: none; }
.processing-badge {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--accent);
  border: 1px solid var(--accent-bdr);
  border-radius: 8px;
  padding: 1px 7px;
  animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.card--more { width: 200px; flex: 0 0 auto; border: 1px dashed var(--border2); background: transparent; display: flex; align-items: center; justify-content: center; color: var(--text-mid); font-family: var(--font-mono); font-size: 12px; border-radius: 12px; }
.card--more:hover { color: var(--accent); border-color: var(--accent-bdr); }

@media (max-width: 880px) {
  .hero { grid-template-columns: 1fr; min-height: 0; }
  .hero__media { height: 200px; min-height: 0; }
  .hero__media::after { background: linear-gradient(180deg, transparent 0%, var(--surface) 90%); }
  .hero__body { padding: 20px 22px 24px; }
  .hero__title { font-size: 22px; }
  .card { width: 168px; }
  .card__thumb { height: 96px; }
}
</style>
