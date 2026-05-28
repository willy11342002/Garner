<template>
  <main class="share-shell">
    <span class="eyebrow">SHARE COLLECTION</span>
    <h1 class="page-title" style="margin:6px 0 24px;">分享一個集合</h1>

    <!-- Stepper -->
    <div class="stepper" :data-step="currentStep">
      <div class="step" :class="{ 'step--done': currentStep > 1, 'step--current': currentStep === 1, 'step--clickable': true }" @click="goToStep(1)">
        <span class="step__circle">
          <template v-if="currentStep > 1">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
          </template>
          <template v-else>1</template>
        </span>
        <span class="step__label">1. 選擇來源</span>
      </div>
      <div class="step" :class="{ 'step--done': currentStep > 2, 'step--current': currentStep === 2, 'step--clickable': maxReachedStep >= 2, 'step--locked': maxReachedStep < 2 }" @click="goToStep(2)">
        <span class="step__circle">
          <template v-if="currentStep > 2">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
          </template>
          <template v-else>2</template>
        </span>
        <span class="step__label">2. 微調內容</span>
      </div>
      <div class="step" :class="{ 'step--current': currentStep === 3, 'step--clickable': maxReachedStep >= 3, 'step--locked': maxReachedStep < 3 }" @click="goToStep(3)">
        <span class="step__circle">3</span>
        <span class="step__label">3. 設定公開</span>
      </div>
    </div>

    <!-- Step 1 — Tag picker -->
    <section v-if="currentStep === 1" class="step-section">
      <span class="step-section__num">STEP 1 · 進行中</span>
      <h2>從哪個標籤建立集合？</h2>
      <p class="desc">系統會把這個標籤底下的所有內容帶入集合，下一步可以微調。</p>

      <div v-if="tagsLoading" class="loading-row">載入標籤中...</div>
      <div v-else-if="tags.length === 0" class="empty-hint">你還沒有任何標籤，先去存幾篇內容吧。</div>
      <div v-else class="tag-grid">
        <button
          v-for="(tag, i) in tags"
          :key="tag.id"
          class="tag-pick"
          :class="{ sel: selectedTagId === tag.id }"
          @click="selectTag(tag)"
        >
          <span class="dot" :style="{ background: `var(--tag-${tagColor(i)})` }"></span>
          <span class="name">{{ tag.name }}</span>
          <span class="count">{{ tag.item_count }} 筆</span>
          <span class="thumbs">
            <span v-for="c in thumbColors(i)" :key="c" class="t">
              <span :class="`placeholder placeholder--${c}`"><span class="placeholder__stripes"></span></span>
            </span>
          </span>
          <span v-if="selectedTagId === tag.id" class="check">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
          </span>
        </button>
      </div>
      <div class="step-foot">
        <span class="spacer"></span>
        <button class="btn btn--accent" :disabled="!selectedTagId" @click="goToStep2">下一步 →</button>
      </div>
    </section>

    <!-- Step 2 — Content picker -->
    <section v-if="currentStep === 2" class="step-section">
      <span class="step-section__num">STEP 2 · 進行中</span>
      <h2>選擇要包含哪些內容</h2>
      <p class="desc">預設全選，點擊取消勾選你不想公開的項目。</p>

      <div v-if="itemsLoading" class="loading-row">載入內容中...</div>
      <template v-else>
        <div class="select-all">
          <button class="pill" @click="toggleAllItems">{{ selectedItemIds.size === tagItems.length ? '取消全選' : '全選' }}</button>
          <span class="spacer" style="flex:1;"></span>
          <span>共 {{ tagItems.length }} 筆 · 已選 {{ selectedItemIds.size }}</span>
        </div>

        <div class="clist">
          <div
            v-for="(item, i) in tagItems"
            :key="item.id"
            class="citem"
            :class="{ unsel: !selectedItemIds.has(item.id) }"
            @click="toggleItem(item.id)"
          >
            <span class="checkbox">
              <svg v-if="selectedItemIds.has(item.id)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
            </span>
            <div class="citem__thumb">
              <img v-if="item.thumbnail_url" :src="item.thumbnail_url" style="width:100%;height:100%;object-fit:cover;" />
              <div v-else :class="`placeholder placeholder--${tagColor(i)}`"><div class="placeholder__stripes"></div></div>
            </div>
            <div class="citem__main">
              <h4 class="citem__title">{{ item.title || item.url }}</h4>
              <div class="citem__meta">
                <span class="tag-chip tag-chip--a">{{ sourceLabel(item.source_type) }}</span>
                <span>{{ timeAgo(item.saved_at) }}</span>
              </div>
            </div>
            <span class="citem__src">{{ sourceBadge(item.source_type) }}</span>
          </div>
        </div>
      </template>

      <div class="step-foot">
        <span class="mono" style="color:var(--accent);">已選 {{ selectedItemIds.size }} / {{ tagItems.length }} 筆</span>
        <span class="spacer"></span>
        <button class="btn" @click="goToStep(1)">← 上一步</button>
        <button class="btn btn--accent" :disabled="selectedItemIds.size === 0" @click="advanceTo3">下一步 →</button>
      </div>
    </section>

    <!-- Step 3 — Visibility -->
    <section v-if="currentStep === 3" class="step-section">
      <span class="step-section__num">STEP 3 · 預覽</span>
      <h2>設定這個集合的公開程度</h2>
      <p class="desc">你可以隨時改變公開設定，原本 Fork 過的人不會被回收。</p>

      <div class="vis-row">
        <div>
          <div class="vis-options">
            <label v-for="opt in visOptions" :key="opt.value" class="vis-opt" :class="{ sel: visibility === opt.value }" @click="visibility = opt.value">
              <div class="vis-opt__head">
                <span>{{ opt.icon }}</span>
                <span class="vis-opt__title">{{ opt.label }}</span>
                <span class="radio"></span>
              </div>
              <p class="vis-opt__desc">{{ opt.desc }}</p>
            </label>
          </div>

          <div class="form-row">
            <label>集合標題</label>
            <input class="input" v-model="collectionTitle" />
          </div>
        </div>

        <div>
          <div class="preview-card">
            <header class="preview-card__head">即時預覽</header>
            <div class="preview-card__cover">
              <div v-for="i in 3" :key="i" class="t">
                <img v-if="tagItems[i - 1]?.thumbnail_url" :src="tagItems[i - 1].thumbnail_url!" style="width:100%;height:100%;object-fit:cover;" />
                <div v-else :class="`placeholder placeholder--${tagColor(i - 1)}`"><div class="placeholder__stripes"></div></div>
              </div>
            </div>
            <div class="preview-card__body">
              <h3 class="preview-card__title">{{ collectionTitle || '（無標題）' }}</h3>
              <div class="preview-card__user">
                <span class="preview-card__avatar">{{ authorInitials }}</span>
                <span>@{{ authStore.user?.username || '...' }} · 剛剛建立</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="step-foot">
        <button class="btn" @click="goToStep(2)">← 上一步</button>
        <span class="spacer"></span>
        <button class="btn btn--accent btn--lg" :disabled="publishing || !collectionTitle" @click="publish">
          {{ publishing ? '建立中...' : '建立並分享 →' }}
        </button>
      </div>
    </section>

    <!-- Success Toast -->
    <aside v-if="showToast && newCollectionId" class="toast">
      <div class="toast__head">
        <span class="ico">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
        </span>
        <span class="toast__title">集合已建立</span>
        <span style="flex:1;"></span>
        <button style="color:var(--text-dim); font-size:14px;" @click="showToast = false">×</button>
      </div>
      <div class="toast__actions">
        <NuxtLink :to="`/app/collection/${newCollectionId}`" class="btn btn--accent">前往查看 →</NuxtLink>
      </div>
    </aside>
  </main>
</template>

<script setup lang="ts">
import type { Collection, Item, Tag } from '~/types/api'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const apiFetch = useApiFetch()

// ── Tags (step 1) ─────────────────────────────────────────────────
const tags = ref<Tag[]>([])
const tagsLoading = ref(true)
const selectedTagId = ref<string | null>(null)
const selectedTagName = ref('')

onMounted(async () => {
  try {
    const all = await apiFetch<Tag[]>('/tags/')
    tags.value = all.filter(t => t.item_count > 0)
  } finally {
    tagsLoading.value = false
  }

  const presetTagId = route.query.tag as string | undefined
  if (presetTagId) {
    const tag = tags.value.find(t => t.id === presetTagId)
    if (tag) await goToStep2WithTag(tag)
  }
})

const COLORS = ['a', 'b', 'c', 'd', 'e'] as const
function tagColor(i: number) { return COLORS[i % COLORS.length] }
function thumbColors(i: number) {
  const base = i % COLORS.length
  return [COLORS[base], COLORS[(base + 1) % 5], COLORS[(base + 2) % 5]]
}

// ── Items (step 2) ────────────────────────────────────────────────
const tagItems = ref<Item[]>([])
const itemsLoading = ref(false)
const selectedItemIds = reactive(new Set<string>())

function selectTag(tag: Tag) {
  selectedTagId.value = tag.id
  selectedTagName.value = tag.name
  collectionTitle.value = tag.name
}

async function goToStep2WithTag(tag: Tag) {
  selectTag(tag)
  await loadTagItems(tag.id)
}

async function goToStep2() {
  if (!selectedTagId.value) return
  await loadTagItems(selectedTagId.value)
}

async function loadTagItems(tagId: string) {
  maxReachedStep.value = Math.max(maxReachedStep.value, 2)
  currentStep.value = 2
  itemsLoading.value = true
  selectedItemIds.clear()
  try {
    tagItems.value = await apiFetch<Item[]>(`/tags/${tagId}/items`)
    tagItems.value.forEach(item => selectedItemIds.add(item.id))
  } finally {
    itemsLoading.value = false
  }
}

function toggleItem(id: string) {
  if (selectedItemIds.has(id)) selectedItemIds.delete(id)
  else selectedItemIds.add(id)
}

function toggleAllItems() {
  if (selectedItemIds.size === tagItems.value.length) {
    selectedItemIds.clear()
  } else {
    tagItems.value.forEach(i => selectedItemIds.add(i.id))
  }
}

function sourceLabel(t: string | null) {
  if (t === 'youtube') return 'YouTube'
  if (t === 'ig') return 'Instagram'
  return '文章'
}
function sourceBadge(t: string | null) {
  if (t === 'youtube') return '▶'
  if (t === 'ig') return 'IG'
  return '⎘'
}
function timeAgo(iso: string) {
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000)
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 30) return `${days}d ago`
  return `${Math.floor(days / 30)}mo ago`
}

// ── Stepper navigation ───────────────────────────────────────────
const currentStep = ref(1)
const maxReachedStep = ref(1)

function goToStep(n: 1 | 2 | 3) {
  if (maxReachedStep.value < n) return
  currentStep.value = n
}

function advanceTo3() {
  maxReachedStep.value = Math.max(maxReachedStep.value, 3)
  currentStep.value = 3
}

// ── Visibility & publish (step 3) ────────────────────────────────
const visibility = ref<'private' | 'link' | 'public'>('public')
const collectionTitle = ref('')
const publishing = ref(false)
const showToast = ref(false)
const newCollectionId = ref<string | null>(null)

const authorInitials = computed(() => {
  const name = authStore.user?.username ?? ''
  return name.slice(0, 2).toUpperCase() || 'ME'
})

const visOptions: { value: 'private' | 'link' | 'public'; icon: string; label: string; desc: string }[] = [
  { value: 'private', icon: '🔒', label: '私人',    desc: '只有你自己看得到，連結分享也無效。' },
  { value: 'link',    icon: '🔗', label: '連結分享', desc: '知道連結的人可以查看與 Fork，但不會被搜尋到。' },
  { value: 'public',  icon: '🌐', label: '公開',    desc: '任何人都能搜尋與 Fork。會出現在 Browse、Google 結果中。' },
]

async function publish() {
  if (!collectionTitle.value || publishing.value) return
  publishing.value = true
  try {
    const slug = collectionTitle.value
      .toLowerCase()
      .replace(/[^a-z0-9一-鿿]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 40) + '-' + Math.random().toString(36).slice(2, 8)

    const col = await apiFetch<Collection>('/collections/', {
      method: 'POST',
      body: { title: collectionTitle.value, visibility: visibility.value, slug },
    })

    // Add selected items sequentially
    const ids = Array.from(selectedItemIds)
    for (const itemId of ids) {
      await apiFetch(`/collections/${col.id}/items?item_id=${itemId}`, { method: 'POST' })
    }

    newCollectionId.value = col.id
    showToast.value = true
  } finally {
    publishing.value = false
  }
}
</script>

<style>
.share-shell { max-width: 980px; margin: 0 auto; padding: 28px 32px 80px; }

.stepper {
  display: grid; grid-template-columns: 1fr 1fr 1fr;
  align-items: center; margin: 14px 0 36px; position: relative;
}
.step { display: flex; flex-direction: column; align-items: center; gap: 10px; position: relative; }
.step__circle {
  width: 32px; height: 32px; border-radius: 50%;
  background: var(--surface3); border: 1.5px solid var(--border2);
  display: inline-flex; align-items: center; justify-content: center;
  font-family: var(--font-mono); font-size: 12.5px; font-weight: 500;
  color: var(--text-mid); position: relative; z-index: 2;
}
.step--done .step__circle { background: var(--accent); color: var(--accent-fg); border-color: var(--accent); }
.step--current .step__circle { border-color: var(--accent); color: var(--accent); background: var(--bg); box-shadow: 0 0 0 4px var(--accent-dim); }
.step__label { font-family: var(--font-mono); font-size: 11.5px; color: var(--text-mid); letter-spacing: 0.03em; }
.step--current .step__label { color: var(--text); }
.step--clickable { cursor: pointer; }
.step--clickable:hover .step__circle { border-color: var(--accent-bdr); }
.step--locked { cursor: default; opacity: 0.45; }
.stepper::before {
  content: ''; position: absolute;
  left: 16.67%; right: 16.67%; top: 16px;
  height: 1.5px; background: var(--border2); z-index: 1;
}
.stepper[data-step="1"]::after { display: none; }
.stepper[data-step="2"]::after {
  content: ''; position: absolute;
  left: 16.67%; top: 16px; width: 33.33%;
  height: 1.5px; background: var(--accent); z-index: 1;
}
.stepper[data-step="3"]::after {
  content: ''; position: absolute;
  left: 16.67%; top: 16px; width: 66.66%;
  height: 1.5px; background: var(--accent); z-index: 1;
}

.step-section {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 16px; padding: 28px 32px 24px; margin-bottom: 18px;
}
.step-section.is-disabled { opacity: 0.45; pointer-events: none; }
.step-section h2 { font-family: var(--font-brand); font-weight: 600; font-size: 21px; letter-spacing: -0.01em; margin: 0 0 6px; }
.step-section .desc { color: var(--text-mid); font-size: 13.5px; margin: 0 0 22px; }
.step-section__num { display: inline-block; font-family: var(--font-mono); font-size: 11px; color: var(--accent); margin-bottom: 6px; letter-spacing: 0.08em; }

.loading-row { font-family: var(--font-mono); font-size: 12px; color: var(--text-dim); padding: 20px 0; }
.empty-hint { font-size: 13.5px; color: var(--text-mid); padding: 16px 0; }

.tag-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.tag-pick {
  display: flex; align-items: center; gap: 10px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; padding: 14px 16px; cursor: pointer;
  transition: all .15s ease; position: relative;
}
.tag-pick:hover { border-color: var(--border2); transform: translateY(-2px); }
.tag-pick.sel { background: var(--accent-dim); border-color: var(--accent-bdr); }
.tag-pick .dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.tag-pick .name { font-size: 13.5px; font-weight: 500; }
.tag-pick .count { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); margin-left: auto; }
.tag-pick .thumbs { display: flex; gap: 2px; margin-left: 8px; flex-shrink: 0; }
.tag-pick .thumbs .t { width: 22px; height: 16px; border-radius: 3px; overflow: hidden; border: 1px solid var(--border); }
.tag-pick .check {
  position: absolute; right: 12px; top: 12px;
  width: 18px; height: 18px; border-radius: 50%;
  background: var(--accent); color: var(--accent-fg);
  display: inline-flex; align-items: center; justify-content: center;
}
.step-foot {
  display: flex; align-items: center;
  margin-top: 22px; padding-top: 18px; border-top: 1px solid var(--border); gap: 10px;
}
.step-foot .spacer { flex: 1; }
.step-foot .mono { font-family: var(--font-mono); font-size: 12px; }

.clist { display: flex; flex-direction: column; gap: 6px; }
.citem {
  display: grid; grid-template-columns: 22px 70px 1fr auto;
  gap: 12px; align-items: center;
  padding: 10px 12px; background: var(--surface);
  border: 1px solid var(--border); border-radius: 10px;
  cursor: pointer; transition: all .15s ease;
}
.citem:hover { background: var(--surface2); }
.citem.unsel { opacity: 0.45; }
.citem .checkbox {
  width: 18px; height: 18px; border-radius: 5px;
  border: 1.5px solid var(--border2); background: var(--surface);
  display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.citem:not(.unsel) .checkbox { background: var(--accent); border-color: var(--accent); color: var(--accent-fg); }
.citem .checkbox svg { width: 12px; height: 12px; }
.citem__thumb { width: 70px; height: 44px; border-radius: 5px; overflow: hidden; }
.citem__main { min-width: 0; }
.citem__title { font-size: 13px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin: 0 0 3px; }
.citem__meta { display: flex; gap: 8px; align-items: center; font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); }
.citem__src { font-family: var(--font-mono); font-size: 10px; color: var(--text-dim); }

.select-all {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 12px; margin-bottom: 10px; border-radius: 8px;
  font-family: var(--font-mono); font-size: 12px; color: var(--text-mid);
}
.select-all .pill {
  cursor: pointer; padding: 5px 12px;
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 6px; transition: all .15s ease;
}
.select-all .pill:hover { color: var(--text); }

.vis-row { display: grid; grid-template-columns: 1fr 360px; gap: 24px; align-items: flex-start; }
.vis-options { display: flex; flex-direction: column; gap: 10px; margin-bottom: 22px; }
.vis-opt {
  position: relative; background: var(--surface2);
  border: 1px solid var(--border); border-radius: 12px;
  padding: 14px 18px 14px 22px; cursor: pointer; transition: all .15s ease;
}
.vis-opt:hover { background: var(--surface3); }
.vis-opt.sel { background: var(--accent-dim); border-color: var(--accent-bdr); }
.vis-opt.sel::before {
  content: ''; position: absolute; left: 0; top: 12px; bottom: 12px;
  width: 3px; background: var(--accent); border-radius: 2px;
}
.vis-opt__head { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
.vis-opt__title { font-size: 14px; font-weight: 500; }
.vis-opt__desc { color: var(--text-mid); font-size: 12.5px; line-height: 1.55; margin: 0; }
.vis-opt .radio {
  margin-left: auto; width: 16px; height: 16px;
  border-radius: 50%; border: 1.5px solid var(--border2); flex-shrink: 0; position: relative;
}
.vis-opt.sel .radio { border-color: var(--accent); }
.vis-opt.sel .radio::after { content: ''; position: absolute; inset: 3px; background: var(--accent); border-radius: 50%; }

.form-row { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
.form-row label { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.06em; }
.input {
  background: var(--surface2); border: 1px solid var(--border2);
  border-radius: 10px; padding: 11px 14px; font-size: 13.5px; color: var(--text);
  outline: none; transition: all .15s ease; font-family: var(--font-ui); width: 100%; box-sizing: border-box;
}
.input:focus { border-color: var(--accent-bdr); box-shadow: 0 0 0 3px var(--accent-dim); }

.preview-card { background: var(--surface2); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; }
.preview-card__head {
  padding: 8px 12px; border-bottom: 1px solid var(--border);
  font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); letter-spacing: 0.06em;
  display: flex; align-items: center; gap: 6px;
}
.preview-card__head::before { content: ''; width: 8px; height: 8px; border-radius: 50%; background: var(--accent); }
.preview-card__cover { height: 120px; display: grid; grid-template-columns: 2fr 1fr; grid-template-rows: 1fr 1fr; gap: 2px; overflow: hidden; }
.preview-card__cover .t { overflow: hidden; }
.preview-card__cover .t:first-child { grid-row: 1 / span 2; }
.preview-card__body { padding: 12px 14px 16px; }
.preview-card__title { font-family: var(--font-brand); font-weight: 600; font-size: 14.5px; margin: 0 0 10px; }
.preview-card__user { display: flex; align-items: center; gap: 6px; font-family: var(--font-mono); font-size: 10.5px; color: var(--text-mid); }
.preview-card__avatar {
  width: 18px; height: 18px; border-radius: 50%;
  background: linear-gradient(135deg, var(--tag-d), var(--tag-b));
  color: #fff; display: inline-flex; align-items: center; justify-content: center; font-size: 8px;
}

.toast {
  position: fixed; right: 24px; bottom: 24px; z-index: 50;
  width: 300px; background: var(--surface); border: 1px solid var(--accent-bdr);
  border-radius: 14px; padding: 14px 16px;
  box-shadow: 0 20px 48px -16px var(--shadow);
  animation: slideIn .35s cubic-bezier(.34,1.4,.64,1) both;
}
@keyframes slideIn { from { transform: translateX(20px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
.toast__head { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.toast__head .ico {
  width: 22px; height: 22px; border-radius: 50%;
  background: var(--accent); color: var(--accent-fg);
  display: inline-flex; align-items: center; justify-content: center;
}
.toast__title { font-size: 13px; font-weight: 500; }
.toast__actions { display: flex; gap: 6px; }
.toast__actions .btn { height: 30px; padding: 0 12px; font-size: 12px; flex: 1; justify-content: center; }

@media (max-width: 880px) {
  .tag-grid { grid-template-columns: 1fr 1fr; }
  .vis-row { grid-template-columns: 1fr; }
  .step-section { padding: 22px 18px 18px; }
}
@media (max-width: 580px) {
  .share-shell { padding: 20px 16px 60px; }
  .tag-grid { grid-template-columns: 1fr; }
  .stepper { gap: 8px; }
  .step__label { display: none; }
  .toast { left: 16px; right: 16px; bottom: 16px; width: auto; }
}
</style>
