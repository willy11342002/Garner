<template>
  <main class="ex-pane">
    <p class="focus-hint">問你的知識庫一個問題，AI 會從你存過的所有內容中合成回答。</p>

    <div class="focus-input-row">
      <textarea
        v-model="query"
        class="focus-input"
        placeholder="例如：三個月前我存了什麼跟 Karpathy 有關的東西？"
        @keydown.enter.exact.prevent="submit"
      ></textarea>
      <button class="btn btn--accent focus-submit" :disabled="loading || !query.trim()" @click="submit">
        {{ loading ? '思考中...' : '探索 →' }}
      </button>
    </div>

    <div v-if="!result && !loading" class="focus-chips">
      <button v-for="chip in CHIPS" :key="chip" class="chip" @click="query = chip; submit()">{{ chip }}</button>
    </div>

    <!-- loading -->
    <div v-if="loading" class="focus-loading">
      <div class="pulse-row"><span></span><span></span><span></span><span></span><span></span></div>
      <ul class="focus-loading__steps">
        <li :class="loadStep >= 1 ? 'done' : 'active'">搜索相關內容</li>
        <li :class="loadStep >= 2 ? 'done' : loadStep === 1 ? 'active' : ''">分析語意關聯</li>
        <li :class="loadStep >= 3 ? 'done' : loadStep === 2 ? 'active' : ''">整合洞察與摘要...</li>
      </ul>
    </div>

    <!-- error -->
    <div v-if="error" class="focus-error">{{ error }}</div>

    <!-- result -->
    <template v-if="result">
      <article class="synth fadeup">
        <header class="synth__head">
          <span class="synth__badge">AI SYNTHESIS</span>
          <div class="synth__actions">
            <button @click="copyResult">{{ copied ? '已複製！' : '複製' }}</button>
            <button @click="reset">新問題</button>
          </div>
        </header>
        <!-- eslint-disable-next-line vue/no-v-html -->
        <p class="synth__text" v-html="result.synthesis"></p>
        <div v-if="result.sources.length" class="synth__sources">
          <span class="label">SOURCES</span>
          <NuxtLink
            v-for="src in result.sources"
            :key="src.id"
            class="src-chip"
            :to="`/app/item/${src.id}`"
          >↗ {{ src.title || src.url }}</NuxtLink>
        </div>
      </article>

      <template v-if="result.sources.length">
        <header class="result-head">
          <span class="eyebrow">相關內容</span>
          <span class="line"></span>
          <span class="mono" style="font-size:11px; color:var(--text-dim);">{{ result.sources.length }} 筆 · 按相似度排序</span>
        </header>
        <div class="result-grid">
          <NuxtLink
            v-for="src in result.sources"
            :key="src.id"
            class="rcard"
            :to="`/app/item/${src.id}`"
          >
            <div class="rcard__thumb">
              <img v-if="src.thumbnail_url" :src="src.thumbnail_url" :alt="src.title || ''" style="width:100%;height:100%;object-fit:cover;">
              <div v-else class="placeholder placeholder--a"><div class="placeholder__stripes"></div></div>
              <span class="source-badge">{{ sourceLabel(src.source_type) }}</span>
            </div>
            <div class="rcard__body">
              <h4 class="rcard__title">{{ src.title || src.url }}</h4>
              <div class="rcard__foot">
                <span>{{ timeAgo(src.saved_at) }}</span>
              </div>
            </div>
          </NuxtLink>
        </div>
      </template>
    </template>
  </main>
</template>

<script setup lang="ts">
import type { FocusResult } from '~/types/api'

const CHIPS = [
  '三個月前存了什麼？',
  '有哪些和 AI 相關？',
  '最常被關聯到的主題',
  '這週新增的產品策略內容',
]

const SOURCE_LABELS: Record<string, string> = { youtube: '▶', article: 'Article', ig: 'IG' }

const apiFetch = useApiFetch()
const query = ref('')
const loading = ref(false)
const loadStep = ref(0)
const result = ref<FocusResult | null>(null)
const error = ref('')
const copied = ref(false)

let stepTimer: ReturnType<typeof setInterval>

async function submit() {
  if (!query.value.trim() || loading.value) return
  loading.value = true
  loadStep.value = 0
  result.value = null
  error.value = ''

  stepTimer = setInterval(() => {
    if (loadStep.value < 2) loadStep.value++
  }, 1200)

  try {
    result.value = await apiFetch<FocusResult>('/explore/focus', {
      method: 'POST',
      body: { query: query.value.trim() },
    })
    loadStep.value = 3
  } catch {
    error.value = 'AI 服務暫時無法使用，請稍後再試。'
  } finally {
    clearInterval(stepTimer)
    loading.value = false
  }
}

function reset() {
  result.value = null
  query.value = ''
  error.value = ''
}

async function copyResult() {
  if (!result.value) return
  await navigator.clipboard.writeText(result.value.synthesis.replace(/<[^>]+>/g, ''))
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

function sourceLabel(type: string | null) {
  return type ? (SOURCE_LABELS[type] ?? type) : 'Article'
}

function timeAgo(isoDate: string) {
  const diff = Date.now() - new Date(isoDate).getTime()
  const days = Math.floor(diff / 86400000)
  if (days === 0) return 'today'
  if (days < 30) return `${days}d ago`
  return `${Math.floor(days / 30)}mo ago`
}
</script>

<style>
.focus-hint { font-size: 13px; color: var(--text-mid); margin-bottom: 12px; }
.focus-input-row { display: flex; gap: 10px; margin-bottom: 14px; }
.focus-input { flex: 1; background: var(--surface); border: 1px solid var(--border2); border-radius: 12px; padding: 14px 18px; font-family: var(--font-ui); font-size: 14px; color: var(--text); resize: none; outline: none; height: 52px; line-height: 1.5; transition: all .15s ease; }
.focus-input:focus { border-color: var(--accent-bdr); box-shadow: 0 0 0 3px var(--accent-dim); }
.focus-input::placeholder { color: var(--text-dim); }
.focus-submit { flex-shrink: 0; height: 52px; padding: 0 24px; border-radius: 10px; }
.focus-submit:disabled { opacity: 0.5; cursor: not-allowed; }
.focus-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 28px; }
.focus-chips .chip { font-family: var(--font-mono); font-size: 11.5px; padding: 6px 12px; border-radius: 16px; background: var(--surface2); color: var(--text-mid); border: 1px solid var(--border); cursor: pointer; transition: all .15s ease; }
.focus-chips .chip:hover { background: var(--accent-dim); color: var(--accent); border-color: var(--accent-bdr); }

.focus-loading { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px; margin-bottom: 24px; }
.pulse-row { display: flex; gap: 8px; margin-bottom: 14px; }
.pulse-row span { width: 9px; height: 9px; background: var(--accent); border-radius: 50%; animation: pulse 1.2s infinite; }
.pulse-row span:nth-child(2) { animation-delay: .18s; }
.pulse-row span:nth-child(3) { animation-delay: .36s; }
.pulse-row span:nth-child(4) { animation-delay: .54s; }
.pulse-row span:nth-child(5) { animation-delay: .72s; }
@keyframes pulse { 0%, 100% { transform: scale(1); opacity: 0.5; } 50% { transform: scale(1.5); opacity: 1; } }
.focus-loading__steps { display: flex; flex-direction: column; gap: 8px; font-family: var(--font-mono); font-size: 12px; color: var(--text-mid); padding: 0; margin: 0; }
.focus-loading__steps li { list-style: none; display: flex; align-items: center; gap: 8px; }
.focus-loading__steps li.done { color: var(--accent); }
.focus-loading__steps li.active { color: var(--text); }
.focus-loading__steps li::before { content: '○'; opacity: 0.5; }
.focus-loading__steps li.done::before { content: '✓'; opacity: 1; }
.focus-loading__steps li.active::before { content: '●'; opacity: 1; animation: blink 1s infinite; }
@keyframes blink { 50% { opacity: 0.4; } }

.focus-error { background: color-mix(in oklab, var(--tag-e) 12%, transparent); border: 1px solid color-mix(in oklab, var(--tag-e) 30%, transparent); color: var(--tag-e); border-radius: 10px; padding: 14px 18px; font-size: 13px; margin-bottom: 20px; }

.synth { position: relative; background: var(--surface); border: 1px solid var(--accent-bdr); border-radius: 14px; padding: 22px 24px; margin-bottom: 24px; overflow: hidden; }
.synth::before { content: ''; position: absolute; left: 0; top: 0; width: 70%; height: 2px; background: linear-gradient(90deg, var(--accent), transparent); }
.synth__head { display: flex; align-items: center; margin-bottom: 14px; }
.synth__badge { display: inline-flex; align-items: center; gap: 6px; font-family: var(--font-mono); font-size: 10.5px; font-weight: 500; color: var(--accent); letter-spacing: 0.06em; }
.synth__badge::before { content: ''; width: 6px; height: 6px; background: var(--accent); border-radius: 50%; }
.synth__actions { margin-left: auto; display: flex; gap: 6px; }
.synth__actions button { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-mid); padding: 5px 10px; border-radius: 6px; border: 1px solid var(--border); background: transparent; transition: all .15s ease; cursor: pointer; }
.synth__actions button:hover { color: var(--text); background: var(--surface2); }
.synth__text { font-size: 13.5px; color: var(--text); line-height: 1.85; margin: 0; }
.synth__text em { font-style: normal; color: var(--accent); font-weight: 500; }
.synth__sources { margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border); display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.synth__sources .label { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); margin-right: 4px; }
.synth__sources .src-chip { font-family: var(--font-mono); font-size: 11px; color: var(--text-mid); padding: 4px 10px; background: var(--surface2); border: 1px solid var(--border); border-radius: 6px; transition: all .15s ease; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 200px; }
.synth__sources .src-chip:hover { color: var(--accent); border-color: var(--accent-bdr); }

.result-head { display: flex; align-items: center; gap: 10px; margin: 18px 0 12px; }
.result-head .eyebrow { color: var(--text-dim); }
.result-head .line { flex: 1; height: 1px; background: var(--border); }
.result-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.rcard { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; transition: all .2s ease; cursor: pointer; }
.rcard:hover { transform: translateY(-3px); border-color: var(--border2); box-shadow: 0 10px 24px -10px var(--shadow); }
.rcard__thumb { height: 88px; position: relative; overflow: hidden; }
.rcard__thumb .source-badge { position: absolute; right: 8px; bottom: 8px; }
.rcard__body { padding: 11px 13px 13px; display: flex; flex-direction: column; gap: 10px; }
.rcard__title { font-size: 12.5px; font-weight: 500; line-height: 1.45; margin: 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.rcard__foot { display: flex; align-items: center; justify-content: space-between; font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); }

.fadeup { animation: fadeup .3s ease; }
@keyframes fadeup { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

@media (max-width: 640px) { .focus-input-row { flex-direction: column; } .focus-submit { width: 100%; height: 44px; } }
</style>
