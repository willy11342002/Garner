<script setup lang="ts">
import type { Report, ReportListItem } from '~/types/api'

definePageMeta({ ssr: false })
useHead({ title: 'Garner — AI 報告' })

const { t } = useI18n()
const route = useRoute()
const { listReports, getReport, updateReport, reviseReport, regenerateReport, deleteReport } = useReports()
const { open: openItemModal } = useItemModal()

const reports = ref<ReportListItem[]>([])
const loadingList = ref(true)

const selectedId = ref<string | null>(null)
const current = ref<Report | null>(null)
const loadingDetail = ref(false)

const editing = ref(false)
const editTitle = ref('')
const editBody = ref('')
const busy = ref(false)

const reviseOpen = ref(false)
const reviseText = ref('')
const copied = ref(false)

onMounted(async () => {
  await loadList()
  const openId = route.query.open
  if (typeof openId === 'string' && openId) select(openId)
})

async function loadList() {
  loadingList.value = true
  try {
    reports.value = await listReports()
  } finally {
    loadingList.value = false
  }
}

async function select(id: string) {
  if (editing.value) cancelEdit()
  selectedId.value = id
  loadingDetail.value = true
  current.value = null
  try {
    current.value = await getReport(id)
  } finally {
    loadingDetail.value = false
  }
}

function backToList() {
  selectedId.value = null
  current.value = null
}

function syncListItem(r: Report) {
  const idx = reports.value.findIndex(x => x.id === r.id)
  if (idx !== -1) {
    reports.value[idx] = {
      ...reports.value[idx],
      title: r.title,
      summary: r.summary,
      last_edited_by: r.last_edited_by,
      updated_at: r.updated_at,
    }
  }
}

// ── 編輯（人） ────────────────────────────────────────────────────────────────
function startEdit() {
  if (!current.value) return
  editTitle.value = current.value.title
  editBody.value = current.value.body_md
  editing.value = true
}

function cancelEdit() {
  editing.value = false
}

async function saveEdit() {
  if (!current.value || busy.value) return
  busy.value = true
  try {
    const updated = await updateReport(current.value.id, {
      title: editTitle.value,
      body_md: editBody.value,
    })
    current.value = updated
    syncListItem(updated)
    editing.value = false
  } finally {
    busy.value = false
  }
}

// ── AI 調整（revise） ─────────────────────────────────────────────────────────
async function submitRevise() {
  if (!current.value || busy.value) return
  const instruction = reviseText.value.trim()
  if (!instruction) return
  busy.value = true
  try {
    const updated = await reviseReport(current.value.id, instruction)
    current.value = updated
    syncListItem(updated)
    reviseOpen.value = false
    reviseText.value = ''
  } finally {
    busy.value = false
  }
}

// ── 重新生成（覆蓋） ──────────────────────────────────────────────────────────
async function doRegenerate() {
  if (!current.value || busy.value) return
  if (!window.confirm(t('reports.regenerateConfirm'))) return
  busy.value = true
  try {
    const updated = await regenerateReport(current.value.id)
    current.value = updated
    syncListItem(updated)
  } finally {
    busy.value = false
  }
}

// ── 刪除（軟刪除） ────────────────────────────────────────────────────────────
async function doDelete() {
  if (!current.value || busy.value) return
  if (!window.confirm(t('reports.deleteConfirm'))) return
  busy.value = true
  const id = current.value.id
  try {
    await deleteReport(id)
    reports.value = reports.value.filter(r => r.id !== id)
    backToList()
  } finally {
    busy.value = false
  }
}

async function copyMd() {
  if (!current.value) return
  try {
    await navigator.clipboard.writeText(current.value.body_md)
    copied.value = true
    setTimeout(() => (copied.value = false), 1500)
  } catch { /* ignore */ }
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('zh-TW', { year: 'numeric', month: 'short', day: 'numeric' })
}

function sourceLabel(st: string | null) {
  if (st === 'youtube') return '▶ YouTube'
  if (st === 'ig') return 'IG'
  return 'Article'
}
</script>

<template>
  <div class="reports" :class="{ 'reports--detail': selectedId }">
    <!-- 列表 -->
    <aside class="reports__list">
      <h1 class="reports__heading">{{ t('reports.title') }}</h1>
      <div v-if="loadingList" class="reports__placeholder">…</div>
      <div v-else-if="!reports.length" class="reports__empty">{{ t('reports.empty') }}</div>
      <ul v-else class="reports__items">
        <li
          v-for="r in reports"
          :key="r.id"
          class="report-item"
          :class="{ 'report-item--active': r.id === selectedId }"
          @click="select(r.id)"
        >
          <span class="report-item__title">{{ r.title }}</span>
          <span v-if="r.summary" class="report-item__summary">{{ r.summary }}</span>
          <span class="report-item__meta">{{ formatDate(r.updated_at) }}</span>
        </li>
      </ul>
    </aside>

    <!-- 詳情 -->
    <section class="reports__detail">
      <div v-if="!selectedId" class="reports__hint">{{ t('reports.selectHint') }}</div>
      <div v-else-if="loadingDetail || !current" class="reports__placeholder">…</div>
      <article v-else class="report-view">
        <header class="report-view__head">
          <button class="report-view__back" @click="backToList">←</button>
          <div class="report-view__head-main">
            <input v-if="editing" v-model="editTitle" class="report-view__title-input" />
            <h2 v-else class="report-view__title">{{ current.title }}</h2>
            <div class="report-view__meta">
              <span class="report-view__badge report-view__badge--ai">{{ t('reports.title') }}</span>
              <span v-if="current.last_edited_by === 'ai'" class="report-view__tag">{{ t('reports.lastEditedAi') }}</span>
              <span v-else-if="current.last_edited_by === 'user'" class="report-view__tag">{{ t('reports.lastEditedUser') }}</span>
            </div>
          </div>
        </header>

        <!-- provenance -->
        <div v-if="current.sources.length" class="report-view__sources">
          <span class="report-view__sources-label">{{ t('reports.sources', { n: current.sources.length }) }}</span>
          <div class="report-view__sources-row">
            <button
              v-for="s in current.sources"
              :key="s.id"
              class="source-chip"
              @click="openItemModal(s.id)"
            >
              <img v-if="s.thumbnail_url" :src="s.thumbnail_url" :alt="s.title || ''" class="source-chip__thumb">
              <span class="source-chip__title">{{ s.title || s.url }}</span>
              <span class="source-chip__type">{{ sourceLabel(s.source_type) }}</span>
            </button>
          </div>
        </div>

        <!-- 工具列 -->
        <div class="report-view__toolbar">
          <template v-if="editing">
            <button class="btn btn--accent" :disabled="busy" @click="saveEdit">{{ busy ? t('reports.saving') : t('reports.save') }}</button>
            <button class="btn" :disabled="busy" @click="cancelEdit">{{ t('reports.cancel') }}</button>
          </template>
          <template v-else>
            <button class="btn" :disabled="busy" @click="startEdit">{{ t('reports.edit') }}</button>
            <button class="btn" :disabled="busy" @click="reviseOpen = !reviseOpen">{{ t('reports.revise') }}</button>
            <button class="btn" :disabled="busy" @click="doRegenerate">{{ t('reports.regenerate') }}</button>
            <button class="btn" :disabled="busy" @click="copyMd">{{ copied ? t('reports.copied') : t('reports.copy') }}</button>
            <button class="btn btn--danger" :disabled="busy" @click="doDelete">{{ t('reports.delete') }}</button>
          </template>
        </div>

        <!-- AI 調整輸入 -->
        <div v-if="reviseOpen && !editing" class="report-view__revise">
          <input
            v-model="reviseText"
            class="report-view__revise-input"
            :placeholder="t('reports.revisePlaceholder')"
            :disabled="busy"
            @keydown.enter="submitRevise"
          />
          <button class="btn btn--accent" :disabled="busy || !reviseText.trim()" @click="submitRevise">
            {{ busy ? t('reports.saving') : t('reports.revise') }}
          </button>
        </div>

        <!-- 內文 -->
        <div class="report-view__body">
          <TiptapEditor v-if="editing" v-model="editBody" />
          <TiptapEditor v-else :model-value="current.body_md" readonly />
        </div>
      </article>
    </section>
  </div>
</template>

<style scoped>
.reports {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 0;
  height: calc(100vh - 56px);
  max-width: 1200px;
}

.reports__list {
  border-right: 1px solid var(--border);
  overflow-y: auto;
  padding: 16px 12px;
}

.reports__heading {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
  margin: 4px 8px 12px;
}

.reports__empty,
.reports__hint,
.reports__placeholder {
  color: var(--text-dim);
  font-size: 13px;
  padding: 24px 12px;
  line-height: 1.6;
}

.reports__items { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }

.report-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  border: 1px solid transparent;
}
.report-item:hover { background: var(--surface2); }
.report-item--active { background: var(--surface2); border-color: var(--border2); }
.report-item__title { font-size: 13.5px; font-weight: 600; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.report-item__summary {
  font-size: 12px; color: var(--text-dim); line-height: 1.4;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.report-item__meta { font-size: 10.5px; color: var(--text-dim); font-family: var(--font-mono); }

.reports__detail { overflow-y: auto; padding: 24px 32px; }

.report-view__head { display: flex; align-items: flex-start; gap: 10px; }
.report-view__back { display: none; background: none; border: none; color: var(--text-dim); font-size: 20px; cursor: pointer; line-height: 1; }
.report-view__head-main { flex: 1; min-width: 0; }
.report-view__title { font-size: 22px; font-weight: 700; color: var(--text); margin: 0 0 8px; }
.report-view__title-input {
  width: 100%; font-size: 22px; font-weight: 700; color: var(--text);
  background: var(--surface2); border: 1px solid var(--border2); border-radius: 8px; padding: 6px 10px; margin-bottom: 8px;
}
.report-view__meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.report-view__badge {
  font-family: var(--font-mono); font-size: 10px; letter-spacing: .06em; text-transform: uppercase;
  padding: 2px 8px; border-radius: 999px;
}
.report-view__badge--ai { color: var(--accent); background: var(--accent-dim); border: 1px solid var(--accent-bdr); }
.report-view__tag { font-size: 11px; color: var(--text-dim); }

.report-view__sources { margin: 16px 0; }
.report-view__sources-label { font-size: 12px; color: var(--text-dim); }
.report-view__sources-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.source-chip {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--surface2); border: 1px solid var(--border2); border-radius: 999px;
  padding: 4px 10px 4px 4px; cursor: pointer; max-width: 240px;
}
.source-chip:hover { border-color: var(--accent-bdr); }
.source-chip__thumb { width: 20px; height: 20px; border-radius: 50%; object-fit: cover; }
.source-chip__title { font-size: 12px; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.source-chip__type { font-size: 10px; color: var(--text-dim); font-family: var(--font-mono); flex-shrink: 0; }

.report-view__toolbar { display: flex; flex-wrap: wrap; gap: 8px; margin: 16px 0; }

.report-view__revise { display: flex; gap: 8px; margin-bottom: 16px; }
.report-view__revise-input {
  flex: 1; background: var(--surface2); border: 1px solid var(--border2); border-radius: 8px;
  padding: 8px 12px; color: var(--text); font-size: 13px;
}

.report-view__body { margin-top: 8px; }

@media (max-width: 768px) {
  .reports { grid-template-columns: 1fr; height: calc(100vh - 56px); }
  .reports__detail { display: none; }
  .reports--detail .reports__list { display: none; }
  .reports--detail .reports__detail { display: block; }
  .report-view__back { display: block; }
}
</style>
