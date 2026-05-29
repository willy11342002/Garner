<template>
  <main class="ex-pane">
    <!-- ── 連鎖探索 ─────────────────────────────── -->
    <section class="chain-section">
      <header class="chain-section__head">
        <span class="eyebrow">連鎖探索</span>
        <span class="chain-section__desc">從一張卡跳到下一張，每跳一次 AI 分析關聯與創意發想</span>
      </header>

      <!-- 起點選擇 -->
      <div v-if="!chain.length" class="chain-start">
        <button class="chain-start__btn" :disabled="chainLoading" @click="startChain('forgotten')">
          <span class="chain-start__icon">◌</span>
          <span>從遺忘內容開始</span>
        </button>
        <button class="chain-start__btn" :disabled="chainLoading" @click="startChain('recent')">
          <span class="chain-start__icon">◈</span>
          <span>從最近關注開始</span>
        </button>
      </div>

      <!-- 起點候選選擇 -->
      <div v-if="startCandidates.length && !chain.length" class="chain-candidates">
        <p class="chain-candidates__label">選擇起點：</p>
        <div class="chain-cand-grid">
          <button
            v-for="item in startCandidates"
            :key="item.id"
            class="cand-card"
            @click="pickStart(item)"
          >
            <div class="cand-card__thumb">
              <img v-if="item.thumbnail_url" :src="item.thumbnail_url" :alt="item.title || ''" style="width:100%;height:100%;object-fit:cover;">
              <div v-else class="placeholder placeholder--b"><div class="placeholder__stripes"></div></div>
            </div>
            <div class="cand-card__title">{{ item.title || item.url }}</div>
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
              @click="activeHopIdx = i"
            >
              <img v-if="hop.item.thumbnail_url" :src="hop.item.thumbnail_url" :alt="hop.item.title || ''" class="chain-node__thumb">
              <div v-else class="chain-node__thumb chain-node__thumb--empty"></div>
              <span class="chain-node__label">{{ hop.item.title ? hop.item.title.slice(0, 20) + (hop.item.title.length > 20 ? '...' : '') : '(無標題)' }}</span>
            </button>
            <span v-if="i < chain.length - 1" class="chain-arrow">→</span>
          </template>
          <button class="btn btn--ghost chain-reset" @click="resetChain">重新開始</button>
        </div>

        <!-- 當前節點詳情 -->
        <div class="chain-detail">
          <!-- 當前 item 卡 -->
          <NuxtLink class="chain-item-card" :to="`/app/item/${activeHop.item.id}`">
            <div class="chain-item-card__thumb">
              <img v-if="activeHop.item.thumbnail_url" :src="activeHop.item.thumbnail_url" :alt="activeHop.item.title || ''" style="width:100%;height:100%;object-fit:cover;">
              <div v-else class="placeholder placeholder--c"><div class="placeholder__stripes"></div></div>
            </div>
            <div class="chain-item-card__body">
              <div class="chain-item-card__title">{{ activeHop.item.title || activeHop.item.url }}</div>
              <div class="chain-item-card__meta">{{ timeAgo(activeHop.item.saved_at) }} · {{ sourceLabel(activeHop.item.source_type) }}</div>
            </div>
          </NuxtLink>

          <!-- AI 分析（這一跳） -->
          <template v-if="activeHop.analysis">
            <div class="hop-analysis fadeup">
              <div class="hop-block hop-block--connect">
                <span class="hop-block__label">↗ 關聯</span>
                <!-- eslint-disable-next-line vue/no-v-html -->
                <p v-html="activeHop.analysis.connection"></p>
              </div>
              <div class="hop-block hop-block--idea">
                <span class="hop-block__label">✦ 創意發想</span>
                <p>{{ activeHop.analysis.ideation }}</p>
              </div>
              <div class="hop-block hop-block--question">
                <span class="hop-block__label">? 引出的問題</span>
                <p class="hop-question">{{ activeHop.analysis.question }}</p>
              </div>
            </div>
          </template>
          <div v-else-if="activeHopIdx === 0" class="hop-start-hint">這是起點，選擇下方的卡片開始探索吧。</div>

          <!-- 分析 loading -->
          <div v-if="chainLoading && activeHopIdx === chain.length - 1 && !activeHop.analysis" class="hop-loading">
            <div class="pulse-row"><span></span><span></span><span></span></div>
            <span>AI 正在分析關聯...</span>
          </div>
        </div>

        <!-- 整條路徑分析 -->
        <div v-if="chain.length >= 3" class="full-chain">
          <button v-if="!fullAnalysis && !fullLoading" class="btn full-chain__btn" @click="doFullAnalysis">
            ✦ 分析整條探索路徑（{{ chain.length }} 個節點）
          </button>
          <div v-if="fullLoading" class="hop-loading">
            <div class="pulse-row"><span></span><span></span><span></span></div>
            <span>AI 正在分析整條路徑...</span>
          </div>
          <div v-if="fullAnalysis" class="full-chain__result fadeup">
            <span class="synth__badge">路徑洞察</span>
            <!-- eslint-disable-next-line vue/no-v-html -->
            <p v-html="fullAnalysis"></p>
          </div>
        </div>

        <!-- 候選下一跳 -->
        <div v-if="activeHopIdx === chain.length - 1" class="chain-next">
          <p class="chain-next__label">繼續探索：</p>
          <div v-if="nextLoading" class="chain-cand-grid">
            <div v-for="n in 4" :key="n" class="cand-card cand-card--skel">
              <div class="cand-card__thumb"></div>
              <div class="skel-line" style="width:80%; height:12px; margin:8px auto;"></div>
            </div>
          </div>
          <div v-else-if="activeHop.candidates.length" class="chain-cand-grid">
            <button
              v-for="item in activeHop.candidates"
              :key="item.id"
              class="cand-card"
              @click="jumpTo(item)"
            >
              <div class="cand-card__thumb">
                <img v-if="item.thumbnail_url" :src="item.thumbnail_url" :alt="item.title || ''" style="width:100%;height:100%;object-fit:cover;">
                <div v-else class="placeholder placeholder--d"><div class="placeholder__stripes"></div></div>
              </div>
              <div class="cand-card__title">{{ item.title || item.url }}</div>
            </button>
          </div>
          <p v-else class="chain-empty">找不到更多相關內容了。</p>
        </div>
      </template>
    </section>
  </main>
</template>

<script setup lang="ts">
import type { ChainHop, ChainItem } from '~/types/api'

const SOURCE_LABELS: Record<string, string> = { youtube: '▶ YouTube', article: 'Article', ig: 'IG' }

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

async function startChain(type: 'forgotten' | 'recent') {
  chainLoading.value = true
  startCandidates.value = []
  chain.value = []
  fullAnalysis.value = null
  try {
    startCandidates.value = await apiFetch<ChainItem[]>(`/explore/chain/start?type=${type}`)
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
  // 只排除當前 item 本身，避免立即往回跳；不排除整條歷史，讓 item 少時也能繼續探索
  const currentId = chain.value[hopIdx].item.id
  try {
    const candidates = await apiFetch<ChainItem[]>(
      `/explore/chain/next?item_id=${currentId}&exclude=${currentId}`
    )
    chain.value[hopIdx].candidates = candidates
  } finally {
    nextLoading.value = false
  }
}

async function jumpTo(item: ChainItem) {
  const fromItem = chain.value[chain.value.length - 1].item
  // 截斷後面（如果從中間節點跳，理論上 activeHopIdx 已是末端）
  chain.value.push({ item, analysis: null, candidates: [] })
  activeHopIdx.value = chain.value.length - 1
  fullAnalysis.value = null

  chainLoading.value = true
  try {
    const analysis = await apiFetch('/explore/chain/hop', {
      method: 'POST',
      body: { from_item_id: fromItem.id, to_item_id: item.id },
    })
    chain.value[activeHopIdx.value].analysis = analysis
  } catch {
    chain.value[activeHopIdx.value].analysis = null
  } finally {
    chainLoading.value = false
  }

  await loadCandidates(activeHopIdx.value)
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
}

function timeAgo(isoDate: string) {
  const days = Math.floor((Date.now() - new Date(isoDate).getTime()) / 86400000)
  if (days === 0) return 'today'
  if (days < 30) return `${days}d ago`
  return `${Math.floor(days / 30)}mo ago`
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

.chain-start { display: flex; gap: 10px; }
.chain-start__btn { flex: 1; display: flex; align-items: center; gap: 10px; padding: 16px 20px; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; font-size: 13.5px; color: var(--text-mid); cursor: pointer; transition: all .15s ease; }
.chain-start__btn:hover { border-color: var(--accent-bdr); color: var(--accent); background: var(--accent-dim); }
.chain-start__btn:disabled { opacity: 0.5; cursor: not-allowed; }
.chain-start__icon { font-size: 18px; }

.chain-candidates { margin-top: 16px; }
.chain-candidates__label { font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); margin-bottom: 10px; }
.chain-cand-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.cand-card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; cursor: pointer; transition: all .15s ease; text-align: left; }
.cand-card:hover { border-color: var(--accent-bdr); transform: translateY(-3px); box-shadow: 0 8px 20px -8px var(--shadow); }
.cand-card--skel { pointer-events: none; }
.cand-card__thumb { height: 70px; overflow: hidden; background: var(--surface2); }
.cand-card--skel .cand-card__thumb { animation: skel-pulse 1.4s ease infinite; }
.cand-card__title { padding: 8px 10px 10px; font-size: 11.5px; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; color: var(--text-mid); }

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
.chain-item-card { display: flex; align-items: center; gap: 14px; padding: 12px 14px; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; transition: all .15s ease; }
.chain-item-card:hover { border-color: var(--accent-bdr); }
.chain-item-card__thumb { width: 72px; height: 52px; border-radius: 8px; overflow: hidden; flex-shrink: 0; }
.chain-item-card__title { font-weight: 500; font-size: 14px; line-height: 1.4; margin-bottom: 4px; }
.chain-item-card__meta { font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); }

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

@media (max-width: 980px) { .chain-cand-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 640px) { .chain-start { flex-direction: column; } .chain-cand-grid { grid-template-columns: repeat(2, 1fr); } }
</style>
