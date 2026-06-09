<template>
  <main class="ex-pane">

    <!-- ══ 知識合成 ══════════════════════════════════ -->
    <section class="synth-section">
      <header class="synth-section__head">
        <div class="synth-section__title-row">
          <span class="eyebrow">知識合成</span>
          <span v-if="quota?.chat" class="synth-quota-badge" :class="{ 'synth-quota-badge--warn': synthQuotaFull }">
            剩餘 {{ synthQuotaRemaining }} / {{ quota.chat.limit }} 次
          </span>
        </div>
        <span class="synth-section__desc">選擇知識節點，輸入指令，讓 AI 幫你提煉洞察或撰寫文章</span>
      </header>

      <!-- Tag filter + 好手氣 -->
      <div class="filter-row synth-filter-row" style="margin-bottom:0; border-bottom:none; padding-bottom:8px;">
        <!-- 桌機：橫向捲動 chip 條 -->
        <div
          ref="filterChipsRef"
          class="filter-chips synth-filter-chips--desktop"
          :class="{ 'filter-chips--dragging': isDragging }"
          @mousedown="onDragStart"
          @mousemove="onDragMove"
          @mouseup="onDragEnd"
          @mouseleave="onDragEnd"
        >
          <button
            v-for="tag in tags"
            :key="tag.id"
            class="tag-filter-chip"
            :class="{ 'tag-filter-chip--active': synthTagIds.includes(tag.id) }"
            @click="toggleSynthTag(tag.id)"
          >{{ tag.name }} <span class="tag-filter-chip__count">{{ tag.item_count }}</span></button>
        </div>
        <button
          v-if="synthTagIds.length"
          class="tag-filter-chip tag-filter-chip--clear synth-filter-chips--desktop"
          @click="clearSynthTags"
        >{{ t('home.filter_clear') }}</button>

        <!-- 手機：下拉選單 -->
        <div ref="tagDropdownRef" class="tag-dropdown-wrap synth-filter-chips--mobile">
          <button class="tag-dropdown-trigger" @click="tagDropdownOpen = !tagDropdownOpen">
            <span>{{ synthTagIds.length ? `已選 ${synthTagIds.length} 個標籤` : '選擇標籤篩選' }}</span>
            <span class="tag-dropdown-caret" :class="{ 'tag-dropdown-caret--open': tagDropdownOpen }">▾</span>
          </button>
          <div v-if="tagDropdownOpen" class="tag-dropdown-list">
            <button
              v-for="tag in tags"
              :key="tag.id"
              class="tag-dropdown-item"
              :class="{ 'tag-dropdown-item--selected': synthTagIds.includes(tag.id) }"
              @click="toggleSynthTag(tag.id)"
            >
              <span class="tag-dropdown-item__check">{{ synthTagIds.includes(tag.id) ? '✓' : '' }}</span>
              <span>{{ tag.name }}</span>
              <span class="tag-filter-chip__count">{{ tag.item_count }}</span>
            </button>
          </div>
        </div>

        <button class="btn synth-lucky-btn" :disabled="synthCandLoading" @click="loadRandomItems">
          <span v-if="synthCandLoading" class="synth-pulse">
            <span></span><span></span><span></span>
          </span>
          <template v-else>◎ 好手氣</template>
        </button>
      </div>

      <!-- 手機：已選 tag chips -->
      <div v-if="synthTagIds.length" class="synth-selected-tags synth-filter-chips--mobile">
        <button
          v-for="id in synthTagIds"
          :key="id"
          class="synth-selected-tag-chip"
          @click="toggleSynthTag(id)"
        >
          {{ tags.find(t => t.id === id)?.name }}
          <span class="synth-selected-tag-chip__x">×</span>
        </button>
      </div>

      <!-- AND / OR toggle + 清除全部 -->
      <div v-if="synthTagIds.length" class="filter-andor synth-filter-actions">
        <template v-if="synthTagIds.length > 1">
          <span class="filter-andor__label">{{ t('home.filter_match') }}</span>
          <button
            class="filter-andor__opt"
            :class="{ 'filter-andor__opt--active': synthFilterLogic === 'and' }"
            @click="synthFilterLogic = 'and'"
          >{{ t('home.filter_all') }}</button>
          <button
            class="filter-andor__opt"
            :class="{ 'filter-andor__opt--active': synthFilterLogic === 'or' }"
            @click="synthFilterLogic = 'or'"
          >{{ t('home.filter_any') }}</button>
        </template>
        <button class="filter-clear-btn synth-clear-btn" @click="clearSynthTags">清除全部</button>
      </div>

      <!-- Results row -->
      <div class="results-row" style="margin-top:10px; margin-bottom:12px;">
        <p class="results-row__summary">
          {{ synthMode === 'lucky' ? `${synthCandidates.length} 筆隨機推薦` : `${candTotal} 筆結果` }}
        </p>
        <div class="results-row__controls">
          <div class="filter-dropdown">
            <span class="filter-dropdown__label">時間</span>
            <span class="filter-dropdown__val">{{ timeLabelMap[exploreTimeFilter] }}</span>
            <select v-model="exploreTimeFilter">
              <option value="all">全部時間</option>
              <option value="7d">近 7 天</option>
              <option value="30d">近 30 天</option>
              <option value="year">今年</option>
            </select>
          </div>
          <div class="filter-dropdown">
            <span class="filter-dropdown__label">排序</span>
            <span class="filter-dropdown__val">{{ sortLabelMap[exploreSortOrder] }}</span>
            <select v-model="exploreSortOrder">
              <option value="saved_desc">最新加入</option>
              <option value="saved_asc">最舊加入</option>
            </select>
          </div>
        </div>
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

      <!-- Pagination (only for tag/all mode, not lucky) -->
      <div v-if="synthMode !== 'lucky' && candTotalPages > 1" class="pagination" style="margin-top:16px;">
        <button class="pagination__btn" :disabled="candPage === 1" @click="goCandPage(candPage - 1)">←</button>
        <span class="pagination__info mono">{{ candPage }} / {{ candTotalPages }}</span>
        <button class="pagination__btn" :disabled="candPage === candTotalPages" @click="goCandPage(candPage + 1)">→</button>
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
          @keydown="(e) => { if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && synthPrompt.trim() && !synthLoading && !synthQuotaFull) { e.preventDefault(); doSynthesize() } }"
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

  </main>
</template>

<script setup lang="ts">
import type { ChatSession, Item, Tag, UsageSummary } from '~/types/api'

definePageMeta({ ssr: false })
useHead({ title: 'Garner — 探索' })

const apiFetch = useApiFetch()
const { listItemsPage } = useItems()
const router = useRouter()
const { t } = useI18n()

const SOURCE_LABELS: Record<string, string> = { youtube: '▶ YouTube', article: 'Article', ig: 'IG' }

// ── Quota ─────────────────────────────────────────────────
const quota = ref<UsageSummary | null>(null)

const synthQuotaRemaining = computed(() => {
  const q = quota.value?.chat
  if (!q || q.limit === null) return '∞'
  return Math.max(0, q.limit - q.used)
})
const synthQuotaFull = computed(() => {
  const q = quota.value?.chat
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

// ── Mobile tag dropdown ───────────────────────────────────
const tagDropdownOpen = ref(false)
const tagDropdownRef = ref<HTMLElement | null>(null)

function onDocClickForTagDropdown(e: MouseEvent) {
  if (tagDropdownRef.value && !tagDropdownRef.value.contains(e.target as Node)) {
    tagDropdownOpen.value = false
  }
}

onMounted(() => document.addEventListener('click', onDocClickForTagDropdown, true))
onUnmounted(() => document.removeEventListener('click', onDocClickForTagDropdown, true))

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
const synthFilterLogic = ref<'and' | 'or'>('and')
const synthCandidates = ref<Item[]>([])
const synthCandLoading = ref(false)
const candPage = ref(1)
const candTotal = ref(0)
const CAND_PAGE_SIZE = 20
const candTotalPages = computed(() => Math.max(1, Math.ceil(candTotal.value / CAND_PAGE_SIZE)))

const exploreTimeFilter = ref<'all' | '7d' | '30d' | 'year'>('all')
const exploreSortOrder = ref<'saved_desc' | 'saved_asc'>('saved_desc')

const timeLabelMap = { all: '全部時間', '7d': '近 7 天', '30d': '近 30 天', year: '今年' }
const sortLabelMap = { saved_desc: '最新加入', saved_asc: '最舊加入' }

function getExploreTimeParam(): string | undefined {
  const now = new Date()
  if (exploreTimeFilter.value === '7d') return new Date(now.getTime() - 7 * 86400000).toISOString()
  if (exploreTimeFilter.value === '30d') return new Date(now.getTime() - 30 * 86400000).toISOString()
  if (exploreTimeFilter.value === 'year') return new Date(now.getFullYear(), 0, 1).toISOString()
  return undefined
}

const activeFilterSummary = computed(() => {
  const parts: string[] = []
  if (synthTagIds.value.length) {
    const names = synthTagIds.value.map(id => tags.value.find(t => t.id === id)?.name).filter(Boolean)
    if (names.length) parts.push(names.join(' + '))
  }
  if (exploreTimeFilter.value !== 'all') parts.push(timeLabelMap[exploreTimeFilter.value])
  return parts.join(' · ')
})
const synthSelectedItems = ref<Item[]>([])
const synthPrompt = ref('')
const synthLoading = ref(false)

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

async function loadAllItems(page = 1) {
  synthCandLoading.value = true
  candPage.value = page
  try {
    const res = await listItemsPage({ page, page_size: CAND_PAGE_SIZE, saved_after: getExploreTimeParam(), sort: exploreSortOrder.value })
    synthCandidates.value = res.items
    candTotal.value = res.total
  } catch {
    synthCandidates.value = []
    candTotal.value = 0
  } finally {
    synthCandLoading.value = false
  }
}

function clearSynthTags() {
  synthTagIds.value = []
  synthMode.value = 'idle'
  loadAllItems(1)
}

function goCandPage(page: number) {
  if (synthTagIds.value.length) loadTaggedItems(page)
  else loadAllItems(page)
}

async function loadRandomItems() {
  synthCandLoading.value = true
  synthMode.value = 'lucky'
  try {
    const res = await apiFetch<{ items: Item[] }>('/items/?sort=random&page_size=5')
    synthCandidates.value = res.items
  } catch {
    synthCandidates.value = []
  } finally {
    synthCandLoading.value = false
  }
}

async function loadTaggedItems(page = 1) {
  if (!synthTagIds.value.length) { return loadAllItems(page) }
  synthCandLoading.value = true
  candPage.value = page
  try {
    const res = await listItemsPage({ tag_ids: synthTagIds.value, tag_logic: synthFilterLogic.value, page, page_size: CAND_PAGE_SIZE, saved_after: getExploreTimeParam(), sort: exploreSortOrder.value })
    synthCandidates.value = res.items
    candTotal.value = res.total
  } catch {
    synthCandidates.value = []
  } finally {
    synthCandLoading.value = false
  }
}

watch(synthTagIds, () => { if (synthMode.value === 'tag') loadTaggedItems(1) }, { deep: true })
watch(synthFilterLogic, () => { if (synthMode.value === 'tag') loadTaggedItems(1) })
watch(synthMode, (val) => { if (val === 'tag') loadTaggedItems(1) })
watch([exploreTimeFilter, exploreSortOrder], () => {
  if (synthMode.value === 'lucky') return
  if (synthTagIds.value.length) loadTaggedItems(1)
  else loadAllItems(1)
})

async function doSynthesize() {
  if (!synthPrompt.value.trim() || !synthSelectedItems.value.length) return
  synthLoading.value = true
  try {
    // 建立新 chat session
    const chatSession = await apiFetch<ChatSession>('/chat/sessions', { method: 'POST', body: {} })

    // 帶 prefill（乾淨 prompt）+ items IDs 跳轉，讓 chat 頁面走正常 send() 流程
    await router.push({
      path: '/app/chat',
      query: {
        session: chatSession.id,
        prefill: synthPrompt.value.trim(),
        items: synthSelectedItems.value.map(i => i.id).join(','),
      },
    })
  } finally {
    synthLoading.value = false
  }
}

onMounted(() => Promise.all([loadQuota(), loadTags(), loadAllItems()]))

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
.ex-pane { width: 70vw; margin: 0 auto; padding: 28px 32px; box-sizing: border-box; min-height: calc(100vh - 52px - 110.78px); }
@media (max-width: 980px) { .ex-pane { padding: 20px 16px; width: 95vw; } }

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
/* ── Mobile tag dropdown ── */
.synth-filter-chips--desktop { display: flex; }
.synth-filter-chips--mobile { display: none; }

.tag-dropdown-wrap { position: relative; flex: 1; min-width: 0; }
.tag-dropdown-trigger { display: flex; align-items: center; justify-content: space-between; width: 100%; padding: 0 12px; height: 32px; background: var(--surface2); border: 1px solid var(--border2); border-radius: 8px; cursor: pointer; font-size: 12.5px; color: var(--text-mid); gap: 8px; }
.tag-dropdown-caret { font-size: 14px; transition: transform .15s; line-height: 1; }
.tag-dropdown-caret--open { transform: rotate(180deg); }
.tag-dropdown-list { position: absolute; top: calc(100% + 4px); left: 0; right: 0; background: var(--surface); border: 1px solid var(--border2); border-radius: 10px; max-height: 220px; overflow-y: auto; z-index: 100; box-shadow: 0 8px 24px rgba(0,0,0,.18); }
.tag-dropdown-item { display: flex; align-items: center; gap: 8px; width: 100%; padding: 8px 12px; background: transparent; border: none; cursor: pointer; font-size: 13px; color: var(--text); text-align: left; transition: background .1s; }
.tag-dropdown-item:hover { background: var(--surface2); }
.tag-dropdown-item--selected { color: var(--accent); }
.tag-dropdown-item__check { width: 14px; font-size: 11px; flex-shrink: 0; }
.tag-dropdown-item .tag-filter-chip__count { margin-left: auto; }

.synth-selected-tags { display: flex; flex-wrap: wrap; gap: 6px; padding-bottom: 8px; }
.synth-filter-actions { padding: 4px 0 8px; }
.synth-clear-btn { margin-left: auto; }
.synth-selected-tag-chip { display: inline-flex; align-items: center; gap: 5px; padding: 3px 8px 3px 10px; background: color-mix(in oklab, var(--accent) 12%, var(--surface2)); border: 1px solid color-mix(in oklab, var(--accent) 30%, transparent); border-radius: 20px; font-size: 12px; color: var(--text); cursor: pointer; transition: background .12s; }
.synth-selected-tag-chip:hover { background: color-mix(in oklab, var(--tag-e) 12%, var(--surface2)); border-color: color-mix(in oklab, var(--tag-e) 30%, transparent); }
.synth-selected-tag-chip__x { font-size: 14px; line-height: 1; color: var(--text-dim); }

@media (max-width: 640px) {
  .chain-cand-grid { grid-template-columns: repeat(2, 1fr); }
  .synth-filter-row { flex-direction: row; align-items: center; gap: 8px; }
  .synth-lucky-btn { flex-shrink: 0; }
  .synth-filter-chips--desktop { display: none !important; }
  .synth-filter-chips--mobile { display: flex; }
  .tag-dropdown-wrap { display: block; }
  .synth-selected-tags { display: flex; }
}
</style>
