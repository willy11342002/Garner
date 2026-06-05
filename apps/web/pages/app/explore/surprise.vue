<template>
  <main class="ex-pane">
    <!-- ── 連鎖探索 ─────────────────────────────── -->
    <section class="chain-section">
      <header class="chain-section__head">
        <span class="eyebrow">{{ $t('explore.chain.eyebrow') }}</span>
        <span class="chain-section__desc">{{ $t('explore.chain.desc') }}</span>
      </header>

      <!-- 起點選擇 -->
      <div v-if="!chain.length" class="chain-start">
        <button class="chain-start__lucky" :disabled="chainLoading" @click="startChain">
          <span class="chain-start__lucky-icon">{{ chainLoading ? '' : '◎' }}</span>
          <span v-if="chainLoading" class="chain-start__lucky-pulse">
            <span></span><span></span><span></span>
          </span>
          <span>{{ $t('explore.chain.start_lucky') }}</span>
        </button>
      </div>
      <!-- 起點候選選擇 -->
      <div v-if="startCandidates.length && !chain.length" class="chain-candidates">
        <p class="chain-candidates__label">{{ $t('explore.chain.pick_label') }}</p>
        <div class="chain-cand-grid">
          <button
            v-for="item in startCandidates"
            :key="item.id"
            class="card chain-cand-card"
            @click="pickStart(item)"
          >
            <div class="card__thumb">
              <img v-if="item.thumbnail_url" :src="item.thumbnail_url" :alt="item.title || ''" class="card__img">
              <div v-else class="placeholder placeholder--b"><div class="placeholder__stripes"></div></div>
              <span class="source-badge">{{ sourceLabel(item.source_type) }}</span>
              <span v-if="item.is_public" class="chain-public-badge chain-public-badge--thumb">公開</span>
            </div>
            <div class="card__body">
              <h3 class="card__title">{{ item.title || item.url }}</h3>
              <div class="card__footer">
                <span class="mono">{{ timeAgo(item.saved_at) }}</span>
              </div>
            </div>
          </button>
        </div>
      </div>

      <!-- 鏈條 -->
      <template v-if="chain.length">
        <!-- 麵包屑路徑 -->
        <div class="chain-path">
          <template v-for="(hop, i) in chain" :key="hop.item.id">
            <button
              class="chain-node"
              :class="{ 'chain-node--active': i === activeHopIdx }"
              @click="i === activeHopIdx ? openDetail(hop.item) : activeHopIdx = i"
            >
              <img v-if="hop.item.thumbnail_url" :src="hop.item.thumbnail_url" :alt="hop.item.title || ''" class="chain-node__thumb">
              <div v-else class="chain-node__thumb chain-node__thumb--empty"></div>
              <span class="chain-node__label">{{ hop.item.title ? hop.item.title.slice(0, 20) + (hop.item.title.length > 20 ? '...' : '') : $t('explore.chain.no_title') }}</span>
            </button>
            <span v-if="i < chain.length - 1" class="chain-arrow">→</span>
          </template>
          <button class="btn btn--ghost chain-reset" @click="resetChain">{{ $t('explore.chain.start_over') }}</button>
        </div>

        <!-- 從任意節點重寫提示（點了非末端節點） -->
        <div v-if="activeHopIdx < chain.length - 1" class="chain-rewrite-bar">
          <span class="chain-rewrite-bar__hint">{{ $t('explore.chain.rewrite_hint') }}</span>
          <button class="btn chain-rewrite-bar__btn" @click="rewriteFrom(activeHopIdx)">
            {{ $t('explore.chain.rewrite_btn') }}
          </button>
        </div>

        <!-- 當前節點詳情 -->
        <div class="chain-detail">
          <!-- AI 分析（這一跳） -->
          <template v-if="activeHop.analysis">
            <div class="hop-analysis fadeup">
              <div class="hop-block hop-block--connect">
                <span class="hop-block__label">{{ $t('explore.chain.connection_label') }}</span>
                <!-- eslint-disable-next-line vue/no-v-html -->
                <p v-html="activeHop.analysis.connection"></p>
              </div>
              <div class="hop-block hop-block--idea">
                <span class="hop-block__label">{{ $t('explore.chain.ideation_label') }}</span>
                <p>{{ activeHop.analysis.ideation }}</p>
              </div>
              <div class="hop-block hop-block--question">
                <span class="hop-block__label">{{ $t('explore.chain.question_label') }}</span>
                <p class="hop-question">{{ activeHop.analysis.question }}</p>
              </div>
            </div>
          </template>
          <div v-else-if="activeHopIdx === 0 && chain.length === 1" class="hop-start-hint">{{ $t('explore.chain.start_hint') }}</div>

          <!-- 分析 loading -->
          <div v-if="chainLoading && activeHopIdx === chain.length - 1 && !activeHop.analysis" class="hop-loading">
            <div class="pulse-row"><span></span><span></span><span></span></div>
            <span>{{ $t('explore.chain.loading_hop') }}</span>
          </div>
        </div>

        <!-- 整條路徑分析 -->
        <div v-if="chain.length >= 3" class="full-chain">
          <button v-if="!fullAnalysis && !fullLoading" class="btn full-chain__btn" @click="doFullAnalysis">
            {{ $t('explore.chain.full_btn', { n: chain.length }) }}
          </button>
          <div v-if="fullLoading" class="hop-loading">
            <div class="pulse-row"><span></span><span></span><span></span></div>
            <span>{{ $t('explore.chain.loading_full') }}</span>
          </div>
          <div v-if="fullAnalysis" class="full-chain__result fadeup">
            <span class="synth__badge">{{ $t('explore.chain.synth_badge') }}</span>
            <!-- eslint-disable-next-line vue/no-v-html -->
            <p v-html="fullAnalysis"></p>
          </div>
        </div>

        <!-- 候選下一跳 -->
        <div v-if="activeHopIdx === chain.length - 1" class="chain-next">
          <p class="chain-next__label">{{ $t('explore.chain.next_label') }}</p>
          <div v-if="nextLoading" class="chain-cand-grid">
            <div v-for="n in 4" :key="n" class="card chain-cand-card chain-cand-card--skel">
              <div class="card__thumb"></div>
              <div class="card__body">
                <div class="skel-line" style="width:85%; height:12px;"></div>
                <div class="skel-line" style="width:50%; height:10px; margin-top:6px;"></div>
              </div>
            </div>
          </div>
          <div v-else-if="activeHop.candidates.length" class="chain-cand-grid">
            <button
              v-for="item in activeHop.candidates"
              :key="item.id"
              class="card chain-cand-card"
              @click="jumpTo(item)"
            >
              <div class="card__thumb">
                <img v-if="item.thumbnail_url" :src="item.thumbnail_url" :alt="item.title || ''" class="card__img">
                <div v-else class="placeholder placeholder--d"><div class="placeholder__stripes"></div></div>
                <span class="source-badge">{{ sourceLabel(item.source_type) }}</span>
                <span v-if="item.is_public" class="chain-public-badge chain-public-badge--thumb">公開</span>
              </div>
              <div class="card__body">
                <h3 class="card__title">{{ item.title || item.url }}</h3>
                <div class="card__footer">
                  <span class="mono">{{ timeAgo(item.saved_at) }}</span>
                </div>
              </div>
            </button>
          </div>
          <p v-else class="chain-empty">{{ $t('explore.chain.empty') }}</p>
        </div>
      </template>
    </section>
  <ItemDetailModal :itemId="detailItemId" @close="detailItemId = null" />
  </main>
</template>

<script setup lang="ts">
import type { ChainHop, ChainItem } from '~/types/api'
useHead({ title: 'Garner — 探索' })

// ── Detail Modal ──────────────────────────────
const detailItemId = ref<string | null>(null)
function openDetail(item: ChainItem) {
  if (item.is_public) return
  detailItemId.value = item.id
}

const SOURCE_LABELS: Record<string, string> = { youtube: '▶ YouTube', article: 'Article', ig: 'IG' }

const { t } = useI18n()

const apiFetch = useApiFetch()

// ── Chain ──────────────────────────────────────
const chain = ref<ChainHop[]>([])
const activeHopIdx = ref(0)
const startCandidates = ref<ChainItem[]>([])
const chainLoading = ref(false)
const nextLoading = ref(false)
const fullLoading = ref(false)
const fullAnalysis = ref<string | null>(null)

const activeHop = computed(() => chain.value[activeHopIdx.value])

const STORAGE_KEY = 'garner_chain_state'

function saveChainState() {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
      chain: chain.value,
      activeHopIdx: activeHopIdx.value,
      fullAnalysis: fullAnalysis.value,
    }))
  } catch {}
}

function restoreChainState() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return
    const state = JSON.parse(raw)
    if (state.chain?.length) {
      chain.value = state.chain
      activeHopIdx.value = state.activeHopIdx ?? 0
      fullAnalysis.value = state.fullAnalysis ?? null
    }
  } catch {}
}

onMounted(restoreChainState)
watch([chain, activeHopIdx, fullAnalysis], saveChainState, { deep: true })

async function startChain() {
  chainLoading.value = true
  startCandidates.value = []
  chain.value = []
  fullAnalysis.value = null
  try {
    startCandidates.value = await apiFetch<ChainItem[]>('/explore/chain/start?type=random')
  } finally {
    chainLoading.value = false
  }
}

async function pickStart(item: ChainItem) {
  startCandidates.value = []
  chain.value = [{ item, analysis: null, candidates: [] }]
  activeHopIdx.value = 0
  await loadCandidates(0)
}

async function loadCandidates(hopIdx: number) {
  nextLoading.value = true
  const currentId = chain.value[hopIdx].item.id
  const excludeIds = chain.value.map(h => h.item.id).join(',')
  try {
    const candidates = await apiFetch<ChainItem[]>(
      `/explore/chain/next?item_id=${currentId}&exclude=${excludeIds}`
    )
    const chainIdSet = new Set(chain.value.map(h => h.item.id))
    chain.value[hopIdx].candidates = candidates.filter(c => !chainIdSet.has(c.id))
  } finally {
    nextLoading.value = false
  }
}

async function jumpTo(item: ChainItem) {
  const fromItem = chain.value[chain.value.length - 1].item
  chain.value.push({ item, analysis: null, candidates: [] })
  const hopIdx = chain.value.length - 1
  activeHopIdx.value = hopIdx
  fullAnalysis.value = null

  chainLoading.value = true
  try {
    const analysis = await apiFetch('/explore/chain/hop', {
      method: 'POST',
      body: { from_item_id: fromItem.id, to_item_id: item.id },
    })
    chain.value[hopIdx].analysis = analysis
  } catch {
    chain.value[hopIdx].analysis = null
  } finally {
    chainLoading.value = false
  }

  await loadCandidates(hopIdx)
}

async function doFullAnalysis() {
  fullLoading.value = true
  try {
    const res = await apiFetch('/explore/chain/full', {
      method: 'POST',
      body: { item_ids: chain.value.map(h => h.item.id) },
    })
    fullAnalysis.value = res.analysis
  } finally {
    fullLoading.value = false
  }
}

function resetChain() {
  chain.value = []
  startCandidates.value = []
  activeHopIdx.value = 0
  fullAnalysis.value = null
  try { sessionStorage.removeItem(STORAGE_KEY) } catch {}
}

async function rewriteFrom(hopIdx: number) {
  chain.value = chain.value.slice(0, hopIdx + 1)
  chain.value[hopIdx].candidates = []
  activeHopIdx.value = hopIdx
  fullAnalysis.value = null
  await loadCandidates(hopIdx)
}

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
/* ── Insights (原有) ── */
.surprise-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 14px; padding: 80px 0; color: var(--text-dim); text-align: center; max-width: 400px; margin: 0 auto; }
.surprise-empty p { font-size: 13px; line-height: 1.6; }
.surprise-refresh { margin-top: 20px; font-size: 12px; }
.insights { display: flex; flex-direction: column; gap: 12px; max-width: 920px; }
.insight { position: relative; background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 20px 22px 18px 26px; transition: all .15s ease; }
.insight:hover { transform: translateX(4px); }
.insight::before { content: ''; position: absolute; left: 0; top: 16px; bottom: 16px; width: 3px; border-radius: 2px; }
.insight--connection::before { background: var(--tag-b); }
.insight--connection:hover { border-color: var(--tag-b); }
.insight--forgotten::before { background: var(--tag-e); }
.insight--forgotten:hover { border-color: var(--tag-e); }
.insight--trend::before { background: var(--tag-a); }
.insight--trend:hover { border-color: var(--tag-a); }
.insight--skel { pointer-events: none; min-height: 140px; }
.insight__head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.ins-badge { font-family: var(--font-mono); font-size: 10.5px; font-weight: 500; padding: 3px 10px; border-radius: 5px; }
.ins-badge--b { color: var(--tag-b); background: color-mix(in oklab, var(--tag-b) 14%, transparent); }
.ins-badge--e { color: var(--tag-e); background: color-mix(in oklab, var(--tag-e) 14%, transparent); }
.ins-badge--a { color: var(--tag-a); background: color-mix(in oklab, var(--tag-a) 14%, transparent); }
.insight__when { margin-left: auto; font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); }
.insight__title { font-family: var(--font-brand); font-weight: 600; font-size: 16.5px; line-height: 1.4; margin: 0 0 8px; }
.insight__body { font-size: 13px; color: var(--text-mid); line-height: 1.7; margin: 0 0 12px; }
.insight__foot { display: flex; gap: 8px; flex-wrap: wrap; padding-top: 10px; border-top: 1px solid var(--border); align-items: center; }
.feedback { margin-left: auto; display: flex; gap: 8px; }
.feedback button { width: 26px; height: 26px; border-radius: 6px; background: var(--surface2); border: 1px solid var(--border); color: var(--text-mid); transition: all .15s ease; cursor: pointer; }
.feedback button:hover { border-color: var(--accent-bdr); }
.topic-bars { display: flex; align-items: flex-end; gap: 12px; height: 80px; margin: 12px 0 14px; padding: 0 4px; }
.topic-bar { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 6px; }
.topic-bar__col { width: 100%; background: var(--accent); border-radius: 4px 4px 0 0; position: relative; min-height: 4px; }
.topic-bar__col::after { content: attr(data-pct) '%'; position: absolute; top: -16px; left: 50%; transform: translateX(-50%); font-family: var(--font-mono); font-size: 9.5px; color: var(--accent); white-space: nowrap; }
.topic-bar__label { font-family: var(--font-mono); font-size: 10px; color: var(--text-mid); }
.item-chip { display: inline-flex; align-items: center; gap: 8px; padding: 6px 10px; background: var(--surface2); border: 1px solid var(--border); border-radius: 8px; font-size: 11.5px; transition: all .15s ease; cursor: pointer; max-width: 220px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.item-chip:hover { background: var(--surface3); }
.item-chip__t { width: 24px; height: 18px; border-radius: 3px; overflow: hidden; flex-shrink: 0; }

/* ── Chain Explorer ── */
.chain-section { max-width: 920px; }
.chain-section__head { display: flex; align-items: baseline; gap: 12px; margin-bottom: 20px; }
.chain-section__desc { font-size: 12.5px; color: var(--text-dim); }

.chain-start { display: flex; justify-content: center; padding: 8px 0 4px; }
.chain-start__lucky { display: inline-flex; align-items: center; gap: 10px; padding: 14px 32px; background: var(--surface); border: 1px solid var(--border); border-radius: 40px; font-size: 14px; color: var(--text-mid); cursor: pointer; transition: all .18s ease; }
.chain-start__lucky:hover { border-color: var(--accent-bdr); color: var(--accent); background: var(--accent-dim); }
.chain-start__lucky:disabled { opacity: 0.5; cursor: not-allowed; }
.chain-start__lucky-icon { font-size: 18px; line-height: 1; }
.chain-start__lucky-pulse { display: flex; gap: 5px; }
.chain-start__lucky-pulse span { width: 6px; height: 6px; background: var(--accent); border-radius: 50%; animation: pulse 1.2s infinite; }
.chain-start__lucky-pulse span:nth-child(2) { animation-delay: .18s; }
.chain-start__lucky-pulse span:nth-child(3) { animation-delay: .36s; }

.chain-candidates { margin-top: 16px; }
.chain-candidates__label { font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); margin-bottom: 10px; }
.chain-cand-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.chain-cand-card { width: auto; }
.chain-cand-card--skel { pointer-events: none; }
.chain-cand-card--skel .card__thumb { animation: skel-pulse 1.4s ease infinite; }

.chain-rewrite-bar { display: flex; align-items: center; gap: 10px; padding: 8px 14px; margin-bottom: 12px; background: color-mix(in oklab, var(--tag-e) 8%, transparent); border: 1px solid color-mix(in oklab, var(--tag-e) 22%, transparent); border-radius: 8px; }
.chain-rewrite-bar__hint { font-family: var(--font-mono); font-size: 11px; color: var(--text-mid); }
.chain-rewrite-bar__btn { font-size: 11.5px; height: 28px; padding: 0 14px; margin-left: auto; }

.chain-path { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 18px; padding: 12px 14px; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; }
.chain-node { display: flex; align-items: center; gap: 7px; padding: 5px 10px; border-radius: 8px; border: 1px solid transparent; background: transparent; cursor: pointer; transition: all .15s ease; max-width: 160px; }
.chain-node:hover { background: var(--surface2); }
.chain-node--active { background: var(--accent-dim); border-color: var(--accent-bdr); color: var(--accent); }
.chain-node__thumb { width: 28px; height: 20px; border-radius: 4px; object-fit: cover; flex-shrink: 0; background: var(--surface2); }
.chain-node__thumb--empty { background: var(--surface2); }
.chain-node__label { font-size: 11.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.chain-arrow { color: var(--text-dim); font-size: 14px; flex-shrink: 0; }
.chain-reset { margin-left: auto; font-size: 11.5px; height: 28px; padding: 0 12px; }

.chain-detail { display: flex; flex-direction: column; gap: 14px; margin-bottom: 20px; }

.chain-public-badge { font-family: var(--font-mono); font-size: 9.5px; font-weight: 500; padding: 2px 7px; border-radius: 5px; background: color-mix(in oklab, var(--tag-d) 14%, transparent); color: var(--tag-d); border: 1px solid color-mix(in oklab, var(--tag-d) 25%, transparent); }
.chain-public-badge--thumb { position: absolute; left: 8px; top: 8px; background: rgba(0,0,0,0.55); color: #fff; border: none; border-radius: 4px; }

.hop-analysis { display: flex; flex-direction: column; gap: 10px; }
.hop-block { padding: 14px 16px; border-radius: 10px; }
.hop-block--connect { background: color-mix(in oklab, var(--tag-b) 8%, transparent); border: 1px solid color-mix(in oklab, var(--tag-b) 22%, transparent); }
.hop-block--idea { background: color-mix(in oklab, var(--accent) 8%, transparent); border: 1px solid var(--accent-bdr); }
.hop-block--question { background: var(--surface); border: 1px solid var(--border); }
.hop-block__label { font-family: var(--font-mono); font-size: 10.5px; font-weight: 500; display: block; margin-bottom: 7px; }
.hop-block--connect .hop-block__label { color: var(--tag-b); }
.hop-block--idea .hop-block__label { color: var(--accent); }
.hop-block--question .hop-block__label { color: var(--text-dim); }
.hop-block p { font-size: 13px; color: var(--text); line-height: 1.75; margin: 0; }
.hop-block p em { font-style: normal; font-weight: 500; color: var(--tag-b); }
.hop-question { font-style: italic; color: var(--text-mid) !important; }
.hop-start-hint { font-size: 12.5px; color: var(--text-dim); padding: 12px 0; }
.hop-loading { display: flex; align-items: center; gap: 12px; padding: 14px; font-family: var(--font-mono); font-size: 12px; color: var(--text-dim); }
.hop-loading .pulse-row { margin: 0; }
.hop-loading .pulse-row span { width: 7px; height: 7px; }

.chain-next { margin-top: 4px; }
.chain-next__label { font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); margin-bottom: 10px; }
.chain-empty { font-size: 12.5px; color: var(--text-dim); padding: 20px 0; }

.full-chain { margin-top: 6px; }
.full-chain__btn { font-size: 12.5px; }
.full-chain__result { background: var(--surface); border: 1px solid var(--accent-bdr); border-radius: 12px; padding: 18px 20px; margin-top: 12px; }
.full-chain__result p { font-size: 13.5px; line-height: 1.85; margin: 10px 0 0; color: var(--text); }
.full-chain__result p em { font-style: normal; color: var(--accent); font-weight: 500; }

.skel-line { background: var(--surface2); border-radius: 6px; animation: skel-pulse 1.4s ease infinite; }
@keyframes skel-pulse { 0%,100%{opacity:.6} 50%{opacity:1} }
.fadeup { animation: fadeup .3s ease; }
@keyframes fadeup { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

.pulse-row { display: flex; gap: 8px; }
.pulse-row span { width: 9px; height: 9px; background: var(--accent); border-radius: 50%; animation: pulse 1.2s infinite; }
.pulse-row span:nth-child(2) { animation-delay: .18s; }
.pulse-row span:nth-child(3) { animation-delay: .36s; }
@keyframes pulse { 0%, 100% { transform: scale(1); opacity: 0.5; } 50% { transform: scale(1.5); opacity: 1; } }

@media (max-width: 980px) { .chain-cand-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 640px) { .chain-start { flex-direction: column; } .chain-cand-grid { grid-template-columns: repeat(2, 1fr); } }
</style>
