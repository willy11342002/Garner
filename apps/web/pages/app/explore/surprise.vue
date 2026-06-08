<template>
  <main class="ex-pane">

    <!-- ══ 知識合成 ══════════════════════════════════ -->
    <section class="synth-section">
      <header class="synth-section__head">
        <div class="synth-section__title-row">
          <span class="eyebrow">知識合成</span>
          <span v-if="quota?.synthesis" class="synth-quota-badge" :class="{ 'synth-quota-badge--warn': synthQuotaFull }">
            剩餘 {{ synthQuotaRemaining }} / {{ quota.synthesis.limit }} 次
          </span>
        </div>
        <span class="synth-section__desc">選擇知識節點，輸入指令，讓 AI 幫你提煉洞察或撰寫文章</span>
      </header>

      <!-- Tag filter + 好手氣 -->
      <div class="filter-row synth-filter-row">
        <div
          ref="filterChipsRef"
          class="filter-chips"
          :class="{ 'filter-chips--dragging': isDragging }"
          @mousedown="onDragStart"
          @mousemove="onDragMove"
          @mouseup="onDragEnd"
          @mouseleave="onDragEnd"
        >
          <button
            class="tag-filter-chip"
            :class="{ 'tag-filter-chip--active': !synthTagIds.length }"
            @click="clearSynthTags"
          >全部</button>
          <button
            v-for="tag in tags"
            :key="tag.id"
            class="tag-filter-chip"
            :class="{ 'tag-filter-chip--active': synthTagIds.includes(tag.id) }"
            @click="toggleSynthTag(tag.id)"
          >{{ tag.name }} <span class="tag-filter-chip__count">{{ tag.item_count }}</span></button>
        </div>
        <button class="btn synth-lucky-btn" :disabled="synthCandLoading" @click="loadRandomItems">
          <span v-if="synthCandLoading" class="synth-pulse">
            <span></span><span></span><span></span>
          </span>
          <template v-else>◎ 好手氣</template>
        </button>
      </div>

      <!-- Candidate grid -->
      <div v-if="synthCandLoading" class="chain-cand-grid synth-cand-grid">
        <div v-for="n in 5" :key="n" class="card chain-cand-card chain-cand-card--skel">
          <div class="card__thumb"></div>
          <div class="card__body">
            <div class="skel-line" style="width:85%; height:12px;"></div>
            <div class="skel-line" style="width:50%; height:10px; margin-top:6px;"></div>
          </div>
        </div>
      </div>
      <div v-else-if="synthCandidates.length" class="chain-cand-grid synth-cand-grid">
        <button
          v-for="item in synthCandidates"
          :key="item.id"
          class="card chain-cand-card"
          :class="{
            'synth-cand--selected': isSelected(item.id),
            'synth-cand--full': synthSelectedItems.length >= 10 && !isSelected(item.id),
          }"
          :disabled="synthSelectedItems.length >= 10 && !isSelected(item.id)"
          @click="toggleChain(item)"
        >
          <div class="card__thumb">
            <img v-if="item.thumbnail_url" :src="item.thumbnail_url" :alt="item.title || ''" class="card__img">
            <div v-else class="placeholder placeholder--b"><div class="placeholder__stripes"></div></div>
            <span class="source-badge">{{ sourceLabel(item.source_type) }}</span>
            <span v-if="isSelected(item.id)" class="synth-selected-badge">✓</span>
          </div>
          <div class="card__body">
            <h3 class="card__title">{{ item.title || item.url }}</h3>
            <div class="card__footer">
              <span class="mono">{{ timeAgo(item.saved_at) }}</span>
            </div>
          </div>
        </button>
      </div>
      <div v-else-if="synthMode !== 'idle'" class="synth-cand-empty">找不到符合條件的內容</div>
      <div v-else class="synth-cand-empty">
        點選標籤篩選知識節點，或按 <strong>好手氣</strong> 隨機探索
      </div>

      <!-- Selected chain -->
      <div v-if="synthSelectedItems.length" class="synth-chain fadeup">
        <div class="synth-chain__head">
          <span class="synth-chain__label">已選節點</span>
          <span class="synth-chain__count" :class="{ 'synth-chain__count--full': synthSelectedItems.length >= 10 }">
            {{ synthSelectedItems.length }} / 10
          </span>
          <button class="btn synth-chain__clear" @click="synthSelectedItems = []">清除全部</button>
        </div>
        <div class="synth-chain__nodes">
          <div v-for="item in synthSelectedItems" :key="item.id" class="synth-node">
            <img v-if="item.thumbnail_url" :src="item.thumbnail_url" :alt="item.title || ''" class="synth-node__thumb">
            <div v-else class="synth-node__thumb synth-node__thumb--empty"></div>
            <span class="synth-node__label">{{ truncate(item.title || item.url || '', 18) }}</span>
            <button class="synth-node__remove" @click="removeFromChain(item.id)">×</button>
          </div>
        </div>
      </div>

      <!-- Prompt + Generate -->
      <div v-if="synthSelectedItems.length" class="synth-prompt-area fadeup">
        <textarea
          v-model="synthPrompt"
          class="synth-prompt"
          placeholder="你想用這些知識做什麼？例如：寫一篇比較這些概念的文章、整理出我對這個主題的理解..."
          rows="3"
          :disabled="synthLoading"
        />
        <div class="synth-prompt-actions">
          <span v-if="synthQuotaFull" class="synth-quota-warn">本月合成次數已用完</span>
          <button
            class="btn btn--accent synth-submit-btn"
            :disabled="!synthPrompt.trim() || synthLoading || synthQuotaFull"
            @click="doSynthesize"
          >
            <span v-if="synthLoading" class="synth-pulse">
              <span></span><span></span><span></span>
            </span>
            <span>{{ synthLoading ? '生成中...' : '生成內容' }}</span>
          </button>
        </div>
      </div>
    </section>

    <!-- ══ 合成結果 Modal ══════════════════════════════════ -->
    <Teleport to="body">
      <div v-if="synthModalOpen" class="id-overlay" @click.self="synthModalOpen = false">
        <div class="synth-modal">
          <button class="synth-modal__close" @click="synthModalOpen = false">×</button>
          <div class="synth-modal__body">
            <div class="synth-modal__content">
              <TiptapEditor v-if="synthTiptapDoc" :model-value="synthTiptapDoc" :readonly="true" />
            </div>
            <div v-if="synthResult?.sources.length" class="synth-modal__sources">
              <span class="synth-modal__sources-label">知識來源</span>
              <div class="synth-modal__sources-list">
                <a
                  v-for="s in synthResult.sources"
                  :key="s.id"
                  :href="s.url"
                  target="_blank"
                  rel="noopener"
                  class="synth-source-chip"
                >
                  <img v-if="s.thumbnail_url" :src="s.thumbnail_url" class="synth-source-chip__thumb" :alt="s.title || ''">
                  <div v-else class="synth-source-chip__thumb synth-source-chip__thumb--empty"></div>
                  <span class="synth-source-chip__title">{{ s.title || s.url }}</span>
                </a>
              </div>
            </div>
          </div>
          <div class="synth-modal__foot">
            <button class="btn btn--accent" :disabled="savingArticle" @click="saveAsArticle">
              {{ savingArticle ? '建立中...' : '轉換成文章 →' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

  </main>
</template>

<script setup lang="ts">
import type { Item, SynthesizeResult, Tag, UsageSummary } from '~/types/api'

definePageMeta({ ssr: false })
useHead({ title: 'Garner — 探索' })

const apiFetch = useApiFetch()
const { listItemsPage } = useItems()
const { createArticle, updateArticle } = useArticles()
const router = useRouter()
const { t } = useI18n()

const SOURCE_LABELS: Record<string, string> = { youtube: '▶ YouTube', article: 'Article', ig: 'IG' }

// ── Quota ─────────────────────────────────────────────────
const quota = ref<UsageSummary | null>(null)

const synthQuotaRemaining = computed(() => {
  const q = quota.value?.synthesis
  if (!q || q.limit === null) return '∞'
  return Math.max(0, q.limit - q.used)
})
const synthQuotaFull = computed(() => {
  const q = quota.value?.synthesis
  return !!q && q.limit !== null && q.used >= q.limit
})

async function loadQuota() {
  try { quota.value = await apiFetch<UsageSummary>('/quota/me') } catch {}
}

// ── Tags ──────────────────────────────────────────────────
const tags = ref<Tag[]>([])

async function loadTags() {
  try { tags.value = await apiFetch<Tag[]>('/tags') } catch {}
}

// ── Tag strip drag-to-scroll ──────────────────────────────
const filterChipsRef = ref<HTMLElement | null>(null)
const isDragging = ref(false)
let dragStartX = 0
let dragScrollLeft = 0

function onDragStart(e: MouseEvent) {
  if (!filterChipsRef.value) return
  isDragging.value = true
  dragStartX = e.pageX - filterChipsRef.value.offsetLeft
  dragScrollLeft = filterChipsRef.value.scrollLeft
}

function onDragMove(e: MouseEvent) {
  if (!isDragging.value || !filterChipsRef.value) return
  e.preventDefault()
  const x = e.pageX - filterChipsRef.value.offsetLeft
  filterChipsRef.value.scrollLeft = dragScrollLeft - (x - dragStartX)
}

function onDragEnd() {
  isDragging.value = false
}

// ── 知識合成 ──────────────────────────────────────────────
type SynthMode = 'idle' | 'tag' | 'lucky'

const synthMode = ref<SynthMode>('idle')
const synthTagIds = ref<string[]>([])
const synthCandidates = ref<Item[]>([])
const synthCandLoading = ref(false)
const synthSelectedItems = ref<Item[]>([])
const synthPrompt = ref('')
const synthLoading = ref(false)
const synthResult = ref<SynthesizeResult | null>(null)
const synthModalOpen = ref(false)
const savingArticle = ref(false)

const synthTiptapDoc = computed<Record<string, unknown> | null>(() => {
  if (!synthResult.value?.content_tiptap) return null
  try { return JSON.parse(synthResult.value.content_tiptap) } catch { return null }
})

function isSelected(id: string) {
  return synthSelectedItems.value.some(i => i.id === id)
}

function toggleChain(item: Item) {
  if (isSelected(item.id)) {
    removeFromChain(item.id)
  } else {
    if (synthSelectedItems.value.length >= 10) return
    synthSelectedItems.value.push(item)
  }
}

function removeFromChain(id: string) {
  synthSelectedItems.value = synthSelectedItems.value.filter(i => i.id !== id)
}

function truncate(str: string, len: number) {
  return str.length > len ? str.slice(0, len) + '...' : str
}

function toggleSynthTag(id: string) {
  synthTagIds.value = synthTagIds.value.includes(id)
    ? synthTagIds.value.filter(t => t !== id)
    : [...synthTagIds.value, id]
  synthMode.value = synthTagIds.value.length ? 'tag' : 'idle'
}

function clearSynthTags() {
  synthTagIds.value = []
  synthMode.value = 'idle'
  synthCandidates.value = []
}

async function loadRandomItems() {
  synthCandLoading.value = true
  synthMode.value = 'lucky'
  try {
    synthCandidates.value = await apiFetch<Item[]>('/explore/random-items?count=5')
  } catch {
    synthCandidates.value = []
  } finally {
    synthCandLoading.value = false
  }
}

async function loadTaggedItems() {
  if (!synthTagIds.value.length) { synthCandidates.value = []; return }
  synthCandLoading.value = true
  try {
    const res = await listItemsPage({ tag_ids: synthTagIds.value, page_size: 20 })
    synthCandidates.value = res.items
  } catch {
    synthCandidates.value = []
  } finally {
    synthCandLoading.value = false
  }
}

watch(synthTagIds, () => { if (synthMode.value === 'tag') loadTaggedItems() }, { deep: true })
watch(synthMode, (val) => { if (val === 'tag') loadTaggedItems() })

async function doSynthesize() {
  if (!synthPrompt.value.trim() || !synthSelectedItems.value.length) return
  synthLoading.value = true
  try {
    const result = await apiFetch<SynthesizeResult>('/explore/synthesize', {
      method: 'POST',
      body: {
        item_ids: synthSelectedItems.value.map(i => i.id),
        prompt: synthPrompt.value.trim(),
      },
    })
    synthResult.value = result
    synthModalOpen.value = true
    await loadQuota()
  } catch (err: any) {
    if (err?.response?.status === 429) await loadQuota()
  } finally {
    synthLoading.value = false
  }
}

async function saveAsArticle() {
  if (!synthResult.value) return
  savingArticle.value = true
  try {
    const article = await createArticle()
    await updateArticle(article.id, {
      content_md: synthResult.value.content_tiptap,
      is_draft: true,
    })
    synthModalOpen.value = false
    await router.push(`/app/write/${article.id}`)
  } finally {
    savingArticle.value = false
  }
}

onMounted(() => Promise.all([loadQuota(), loadTags()]))

function timeAgo(isoDate: string) {
  const days = Math.floor((Date.now() - new Date(isoDate).getTime()) / 86400000)
  if (days === 0) return t('explore.chain.time_today')
  if (days < 30) return t('explore.chain.time_days', { n: days })
  return t('explore.chain.time_months', { n: Math.floor(days / 30) })
}

function sourceLabel(type: string | null) {
  return type ? (SOURCE_LABELS[type] ?? type) : 'Article'
}
</script>

<style>
/* ── 知識合成 ── */
.synth-section { max-width: 70vw; margin-bottom: 40px; }
.synth-section__head { margin-bottom: 18px; }
.synth-section__title-row { display: flex; align-items: center; gap: 12px; margin-bottom: 4px; }
.synth-section__desc { font-size: 12.5px; color: var(--text-dim); }

.synth-quota-badge { font-family: var(--font-mono); font-size: 11px; padding: 3px 10px; border-radius: 6px; background: var(--surface2); color: var(--text-mid); border: 1px solid var(--border); }
.synth-quota-badge--warn { color: var(--tag-e); border-color: color-mix(in oklab, var(--tag-e) 30%, transparent); background: color-mix(in oklab, var(--tag-e) 8%, transparent); }

.synth-filter-row { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.synth-filter-row .filter-chips { flex: 1; min-width: 0; cursor: grab; }
.filter-chips--dragging { cursor: grabbing !important; user-select: none; }
.synth-lucky-btn { flex-shrink: 0; display: inline-flex; align-items: center; gap: 8px; white-space: nowrap; }

.synth-cand-grid { margin-bottom: 16px; }
.synth-cand--selected { outline: 2px solid var(--accent); outline-offset: -2px; }
.synth-cand--selected .card__thumb::after { content: ''; position: absolute; inset: 0; background: color-mix(in oklab, var(--accent) 12%, transparent); }
.synth-cand--full { opacity: 0.4; cursor: not-allowed; }
.synth-selected-badge { position: absolute; top: 6px; right: 6px; width: 20px; height: 20px; border-radius: 50%; background: var(--accent); color: #000; font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center; }

.synth-cand-empty { padding: 36px 0; font-size: 13px; color: var(--text-dim); text-align: center; }
.synth-cand-empty strong { color: var(--text-mid); }

.synth-chain { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px; margin-bottom: 14px; }
.synth-chain__head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.synth-chain__label { font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); }
.synth-chain__count { font-family: var(--font-mono); font-size: 11px; font-weight: 600; color: var(--text-mid); }
.synth-chain__count--full { color: var(--tag-e); }
.synth-chain__clear { margin-left: auto; font-size: 11px; height: 26px; padding: 0 10px; color: var(--text-dim); }
.synth-chain__nodes { display: flex; flex-wrap: wrap; gap: 8px; }

.synth-node { display: flex; align-items: center; gap: 7px; padding: 5px 8px 5px 6px; background: var(--surface2); border: 1px solid var(--border2); border-radius: 8px; max-width: 200px; }
.synth-node__thumb { width: 28px; height: 20px; border-radius: 4px; object-fit: cover; flex-shrink: 0; }
.synth-node__thumb--empty { background: var(--surface3); }
.synth-node__label { font-size: 11.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1; min-width: 0; }
.synth-node__remove { flex-shrink: 0; width: 18px; height: 18px; border-radius: 4px; background: transparent; border: none; color: var(--text-dim); cursor: pointer; font-size: 14px; line-height: 1; display: flex; align-items: center; justify-content: center; transition: all .12s; }
.synth-node__remove:hover { background: color-mix(in oklab, var(--tag-e) 14%, transparent); color: var(--tag-e); }

.synth-prompt-area { display: flex; flex-direction: column; gap: 10px; }
.synth-prompt { width: 100%; padding: 12px 14px; background: var(--surface); border: 1px solid var(--border2); border-radius: 10px; color: var(--text); font-size: 13.5px; font-family: var(--font-ui); line-height: 1.6; resize: vertical; transition: border-color .15s; box-sizing: border-box; }
.synth-prompt:focus { outline: none; border-color: var(--accent-bdr); }
.synth-prompt:disabled { opacity: 0.5; }
.synth-prompt-actions { display: flex; align-items: center; justify-content: flex-end; gap: 12px; }
.synth-quota-warn { font-family: var(--font-mono); font-size: 11.5px; color: var(--tag-e); }
.synth-submit-btn { display: inline-flex; align-items: center; gap: 8px; min-width: 110px; justify-content: center; }

.synth-pulse { display: flex; gap: 5px; }
.synth-pulse span { width: 6px; height: 6px; background: var(--accent); border-radius: 50%; animation: pulse 1.2s infinite; }
.synth-pulse span:nth-child(2) { animation-delay: .18s; }
.synth-pulse span:nth-child(3) { animation-delay: .36s; }

/* ── Synthesis Modal ── */
.synth-modal { position: relative; background: var(--surface); border: 1px solid var(--border2); border-radius: 16px; width: 680px; max-width: calc(100vw - 32px); max-height: 80vh; display: flex; flex-direction: column; overflow: hidden; }
.synth-modal__close { position: absolute; top: 14px; right: 14px; width: 30px; height: 30px; border-radius: 8px; background: var(--surface2); border: 1px solid var(--border); color: var(--text-mid); cursor: pointer; font-size: 18px; display: flex; align-items: center; justify-content: center; transition: all .15s; z-index: 1; }
.synth-modal__close:hover { background: var(--surface3); color: var(--text); }
.synth-modal__body { flex: 1; overflow-y: auto; padding: 28px 28px 20px; }
.synth-modal__content { background: var(--surface2); border-radius: 10px; padding: 16px 18px; border: 1px solid var(--border); }
.synth-modal__sources { margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--border); }
.synth-modal__sources-label { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); display: block; margin-bottom: 10px; }
.synth-modal__sources-list { display: flex; flex-direction: column; gap: 6px; }
.synth-modal__foot { padding: 16px 28px; border-top: 1px solid var(--border); display: flex; justify-content: flex-end; background: var(--surface); }

.synth-source-chip { display: flex; align-items: center; gap: 10px; padding: 7px 10px; background: var(--surface2); border: 1px solid var(--border); border-radius: 8px; text-decoration: none; color: var(--text-mid); font-size: 12px; transition: all .15s; }
.synth-source-chip:hover { background: var(--surface3); color: var(--text); }
.synth-source-chip__thumb { width: 36px; height: 24px; border-radius: 4px; object-fit: cover; flex-shrink: 0; }
.synth-source-chip__thumb--empty { background: var(--surface3); }
.synth-source-chip__title { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* ── Shared ── */
.chain-cand-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }
.chain-cand-card { width: auto; }
.chain-cand-card--skel { pointer-events: none; }
.chain-cand-card--skel .card__thumb { animation: skel-pulse 1.4s ease infinite; }
.skel-line { background: var(--surface2); border-radius: 6px; animation: skel-pulse 1.4s ease infinite; }
@keyframes skel-pulse { 0%,100%{opacity:.6} 50%{opacity:1} }
.fadeup { animation: fadeup .3s ease; }
@keyframes fadeup { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
@keyframes pulse { 0%, 100% { transform: scale(1); opacity: 0.5; } 50% { transform: scale(1.5); opacity: 1; } }

@media (max-width: 980px) { .chain-cand-grid { grid-template-columns: repeat(3, 1fr); } .synth-section { max-width: 100%; } }
@media (max-width: 640px) { .chain-cand-grid { grid-template-columns: repeat(2, 1fr); } .synth-filter-row { flex-direction: column; align-items: flex-start; } .synth-lucky-btn { align-self: flex-end; } }
</style>
