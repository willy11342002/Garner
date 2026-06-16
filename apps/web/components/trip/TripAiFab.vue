<template>
  <!-- Panel -->
  <Transition name="taf-panel">
    <div
      v-if="open"
      class="taf-panel"
      :class="{ 'taf-panel--left': side === 'left' }"
      :style="panelStyle"
    >
      <div class="taf-head">
        <span class="taf-head__title">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v3M12 18v3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M3 12h3M18 12h3M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"/></svg>
          AI 修改行程
        </span>
        <button class="taf-head__close" title="關閉" @click="open = false">✕</button>
      </div>

      <div ref="logEl" class="taf-log">
        <div v-if="messages.length === 0" class="taf-empty">
          <p>用一句話描述想怎麼調整這份行程，AI 會幫你即時新增、修改或刪除卡片。</p>
          <div class="taf-examples">
            <button
              v-for="ex in EXAMPLES"
              :key="ex"
              class="taf-chip"
              type="button"
              :disabled="sending"
              @click="send(ex)"
            >{{ ex }}</button>
          </div>
        </div>

        <div v-for="m in messages" :key="m.id" class="taf-msg" :class="`taf-msg--${m.role}`">
          <div v-if="m.text" class="taf-bubble">{{ m.text }}</div>
          <div v-if="m.actions.length" class="taf-actions">
            <div v-for="(a, i) in m.actions" :key="i" class="taf-action">{{ a }}</div>
          </div>
        </div>

        <div v-if="sending && !streamingText" class="taf-thinking">
          <span class="taf-dot" /><span class="taf-dot" /><span class="taf-dot" />
        </div>
      </div>

      <form class="taf-input" @submit.prevent="send()">
        <textarea
          ref="inputEl"
          v-model="draft"
          class="taf-input__field"
          rows="1"
          :disabled="sending"
          placeholder="例如：第 2 天加一個咖啡廳…"
          @keydown.enter.exact.prevent="send()"
        />
        <button
          class="taf-input__send"
          type="submit"
          :disabled="sending || !draft.trim()"
          :title="sending ? '處理中…' : '送出'"
        >
          <svg v-if="!sending" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>
          <span v-else class="taf-spin" />
        </button>
      </form>
    </div>
  </Transition>

  <!-- FAB -->
  <button
    ref="fabEl"
    class="taf-fab"
    :class="{ 'taf-fab--open': open, 'taf-fab--dragging': dragging }"
    :style="fabStyle"
    :title="open ? '關閉 AI 修改' : 'AI 修改行程'"
    @pointerdown="onPointerDown"
    @click="onClick"
  >
    <Transition name="taf-icon" mode="out-in">
      <svg v-if="open" key="close" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><path d="M18 6L6 18M6 6l12 12"/></svg>
      <svg v-else key="chat" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="20" height="20"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
    </Transition>
  </button>
</template>

<script setup lang="ts">
import type { TripItem } from '~/types/api'

const props = defineProps<{ tripId: string }>()
const emit = defineEmits<{
  (e: 'card-added', item: TripItem): void
  (e: 'card-updated', item: TripItem): void
  (e: 'card-deleted', id: string): void
  (e: 'done'): void
}>()

const config = useRuntimeConfig()
const session = useSupabaseSession()

const EXAMPLES = [
  '幫每一天補上午餐和晚餐',
  '行程太趕，幫我精簡一下',
  '加一個必去的夜景景點',
]

const open = ref(false)

// ── Conversation ─────────────────────────────────────────────────────────────
interface Msg { id: string; role: 'user' | 'assistant'; text: string; actions: string[] }
const messages = ref<Msg[]>([])
const draft = ref('')
const sending = ref(false)
const streamingText = ref('')
const inputEl = ref<HTMLTextAreaElement | null>(null)
const logEl = ref<HTMLElement | null>(null)

function scrollLog() {
  nextTick(() => { if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight })
}

async function send(preset?: string) {
  const content = (preset ?? draft.value).trim()
  if (!content || sending.value) return
  draft.value = ''
  sending.value = true
  streamingText.value = ''

  // 把先前對話帶上去（純文字），讓多輪追問有記憶。assistant 若只有動作沒文字，補成文字脈絡。
  const history = messages.value
    .map((m) => {
      const text = m.text || (m.actions.length ? m.actions.join('；') : '')
      return text ? { role: m.role, content: text } : null
    })
    .filter((t): t is { role: 'user' | 'assistant'; content: string } => t !== null)
    .slice(-12)

  messages.value.push({ id: crypto.randomUUID(), role: 'user', text: content, actions: [] })
  const assistant: Msg = { id: crypto.randomUUID(), role: 'assistant', text: '', actions: [] }
  messages.value.push(assistant)
  scrollLog()

  const apiBase = config.public.apiBase as string
  const token = session.value?.access_token

  try {
    const resp = await fetch(`${apiBase}/trips/${props.tripId}/ai-edit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ instruction: content, history }),
    })
    if (!resp.ok || !resp.body) throw new Error('request failed')

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() ?? ''

      for (const part of parts) {
        if (!part.startsWith('event: ')) continue
        const lines = part.split('\n')
        const event = lines[0].replace('event: ', '')
        let data: any = {}
        try { data = JSON.parse(lines[1].replace('data: ', '')) } catch { continue }

        if (event === 'delta') {
          streamingText.value += data.text
          assistant.text = streamingText.value
          scrollLog()
        } else if (event === 'tool_result') {
          handleToolResult(data, assistant)
          scrollLog()
        } else if (event === 'error') {
          assistant.actions.push('⚠️ ' + (data.message || '發生錯誤'))
        } else if (event === 'done') {
          emit('done')
        }
      }
    }
    if (!assistant.text && assistant.actions.length === 0) {
      assistant.text = '沒有需要調整的地方。'
    }
  } catch {
    assistant.actions.push('⚠️ AI 修改失敗，請稍後再試。')
  } finally {
    sending.value = false
    streamingText.value = ''
    scrollLog()
  }
}

function handleToolResult(data: any, assistant: Msg) {
  if (!data.ok) return
  if (data.name === 'add_card' && data._item) {
    emit('card-added', data._item as TripItem)
    assistant.actions.push(`➕ 新增「${data.title || data._item.title}」`)
  } else if (data.name === 'update_card' && data._item) {
    emit('card-updated', data._item as TripItem)
    assistant.actions.push(`✏️ 修改「${data.title || data._item.title}」`)
  } else if (data.name === 'delete_card' && data._deleted_id) {
    emit('card-deleted', data._deleted_id as string)
    assistant.actions.push('🗑️ 刪除一張卡片')
  }
}

// ── Drag / dock（參考首頁 HomeChatFab）──────────────────────────────────────────
const FAB_SIZE = 52
const SNAP_GAP = 16
const EDGE_GAP = 28

const fabEl = ref<HTMLButtonElement | null>(null)
const dragging = ref(false)
const side = ref<'left' | 'right'>('right')
const bottomPx = ref(EDGE_GAP)

let dragStartX = 0
let dragStartY = 0
let pointerStartClientX = 0
let pointerStartClientY = 0
let moved = false

const fabStyle = computed(() => side.value === 'right'
  ? { right: `${SNAP_GAP}px`, left: 'auto', bottom: `${bottomPx.value}px`, top: 'auto' }
  : { left: `${SNAP_GAP}px`, right: 'auto', bottom: `${bottomPx.value}px`, top: 'auto' })

const panelStyle = computed(() => {
  const bottom = bottomPx.value + FAB_SIZE + 12
  return side.value === 'right'
    ? { bottom: `${bottom}px`, right: `${SNAP_GAP}px`, left: 'auto' }
    : { bottom: `${bottom}px`, left: `${SNAP_GAP}px`, right: 'auto' }
})

function onPointerDown(e: PointerEvent) {
  if (e.button !== 0) return
  moved = false
  pointerStartClientX = e.clientX
  pointerStartClientY = e.clientY
  const rect = fabEl.value!.getBoundingClientRect()
  dragStartX = rect.left
  dragStartY = rect.top
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
}

function onPointerMove(e: PointerEvent) {
  const dx = e.clientX - pointerStartClientX
  const dy = e.clientY - pointerStartClientY
  if (!moved && Math.hypot(dx, dy) < 5) return
  moved = true
  dragging.value = true
  const vw = window.innerWidth
  const vh = window.innerHeight
  const newLeft = Math.max(0, Math.min(vw - FAB_SIZE, dragStartX + dx))
  const newTop = Math.max(0, Math.min(vh - FAB_SIZE, dragStartY + dy))
  bottomPx.value = vh - newTop - FAB_SIZE
  side.value = newLeft + FAB_SIZE / 2 < vw / 2 ? 'left' : 'right'
}

function onPointerUp() {
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  dragging.value = false
  if (!moved) return
  const vh = window.innerHeight
  bottomPx.value = Math.max(SNAP_GAP, Math.min(vh - FAB_SIZE - SNAP_GAP, bottomPx.value))
}

function onClick() {
  if (moved) return // 是拖曳不是點擊
  open.value = !open.value
  if (open.value) nextTick(() => inputEl.value?.focus())
}
</script>

<style scoped>
/* ── FAB ── */
.taf-fab {
  position: fixed;
  width: 52px; height: 52px; border-radius: 50%;
  border: none; background: var(--accent); color: var(--accent-fg, #fff);
  cursor: grab; display: flex; align-items: center; justify-content: center;
  z-index: 1000; box-shadow: 0 4px 20px rgba(0,0,0,0.35);
  transition: background .2s, transform .2s, box-shadow .2s; touch-action: none; user-select: none;
}
.taf-fab:hover { transform: scale(1.07); box-shadow: 0 6px 28px rgba(0,0,0,0.45); }
.taf-fab--open { background: var(--surface3, var(--surface2)); color: var(--text); }
.taf-fab--dragging { cursor: grabbing; transform: scale(1.1); box-shadow: 0 8px 32px rgba(0,0,0,0.5); transition: transform .05s, box-shadow .05s; }

/* ── Panel ── */
.taf-panel {
  position: fixed; width: 380px; height: 520px; max-height: calc(100vh - 120px);
  background: var(--bg); border: 1px solid var(--border2); border-radius: 16px;
  box-shadow: 0 12px 48px rgba(0,0,0,0.45); z-index: 999; overflow: hidden;
  display: flex; flex-direction: column;
}
.taf-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 13px 14px; border-bottom: 1px solid var(--border); flex-shrink: 0;
}
.taf-head__title { display: inline-flex; align-items: center; gap: 7px; font-family: var(--font-brand); font-weight: 600; font-size: 14px; color: var(--text); }
.taf-head__title svg { width: 16px; height: 16px; color: var(--accent); }
.taf-head__close { background: none; border: none; color: var(--text-dim); font-size: 15px; cursor: pointer; padding: 4px 7px; border-radius: 6px; }
.taf-head__close:hover { background: var(--surface2); color: var(--text); }

.taf-log { flex: 1 1 auto; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 12px; }
.taf-empty { color: var(--text-mid); font-size: 12.5px; line-height: 1.55; }
.taf-empty p { margin: 0 0 12px; }
.taf-examples { display: flex; flex-wrap: wrap; gap: 7px; }
.taf-chip {
  padding: 5px 11px; border-radius: 20px; font-size: 12px;
  border: 1px solid var(--border); background: var(--surface); color: var(--text-mid); cursor: pointer; transition: all .14s ease;
}
.taf-chip:hover { border-color: var(--accent-bdr); color: var(--accent); background: var(--accent-dim); }

.taf-msg { display: flex; flex-direction: column; gap: 6px; }
.taf-msg--user { align-items: flex-end; }
.taf-bubble {
  max-width: 85%; padding: 8px 12px; border-radius: 12px; font-size: 13px; line-height: 1.55;
  white-space: pre-wrap; word-break: break-word;
}
.taf-msg--user .taf-bubble { background: var(--accent); color: var(--accent-fg, #fff); border-bottom-right-radius: 4px; }
.taf-msg--assistant .taf-bubble { background: var(--surface2); color: var(--text); border-bottom-left-radius: 4px; }
.taf-actions { display: flex; flex-direction: column; gap: 4px; }
.taf-action {
  font-size: 11.5px; color: var(--text-mid); font-family: var(--font-mono);
  background: color-mix(in oklab, var(--tag-a, #34c759) 12%, transparent);
  border: 1px solid color-mix(in oklab, var(--tag-a, #34c759) 24%, transparent);
  padding: 3px 9px; border-radius: 7px; width: fit-content;
}

.taf-thinking { display: flex; gap: 4px; padding: 4px 2px; }
.taf-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--text-dim); animation: taf-bounce 1.2s infinite ease-in-out; }
.taf-dot:nth-child(2) { animation-delay: .15s; }
.taf-dot:nth-child(3) { animation-delay: .3s; }
@keyframes taf-bounce { 0%, 80%, 100% { opacity: .3; transform: translateY(0); } 40% { opacity: 1; transform: translateY(-4px); } }

.taf-input { display: flex; align-items: flex-end; gap: 8px; padding: 12px 14px; border-top: 1px solid var(--border); flex-shrink: 0; }
.taf-input__field {
  flex: 1; resize: none; max-height: 96px; box-sizing: border-box;
  background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
  padding: 9px 11px; font-size: 13px; line-height: 1.5; color: var(--text); outline: none; font-family: inherit;
  transition: border-color .15s;
}
.taf-input__field:focus { border-color: var(--accent); }
.taf-input__send {
  flex: 0 0 auto; width: 38px; height: 38px; border-radius: 10px; border: none;
  background: var(--accent); color: var(--accent-fg, #fff); cursor: pointer;
  display: flex; align-items: center; justify-content: center; transition: opacity .15s, transform .12s;
}
.taf-input__send svg { width: 16px; height: 16px; }
.taf-input__send:disabled { opacity: .45; cursor: default; }
.taf-input__send:not(:disabled):hover { transform: scale(1.06); }
.taf-spin { width: 15px; height: 15px; border: 2px solid color-mix(in oklab, var(--accent-fg, #fff) 45%, transparent); border-top-color: var(--accent-fg, #fff); border-radius: 50%; animation: taf-rot .7s linear infinite; }
@keyframes taf-rot { to { transform: rotate(360deg); } }

/* Transitions */
.taf-panel-enter-active { animation: taf-panel-in .22s cubic-bezier(.2,.8,.4,1); }
.taf-panel-leave-active { animation: taf-panel-in .18s cubic-bezier(.4,0,.8,.2) reverse; }
@keyframes taf-panel-in { from { opacity: 0; transform: translateY(16px) scale(0.97); } to { opacity: 1; transform: translateY(0) scale(1); } }
.taf-icon-enter-active, .taf-icon-leave-active { transition: opacity .15s, transform .15s; }
.taf-icon-enter-from { opacity: 0; transform: rotate(-45deg) scale(0.7); }
.taf-icon-leave-to { opacity: 0; transform: rotate(45deg) scale(0.7); }

@media (max-width: 640px) {
  .taf-panel { bottom: 0 !important; right: 0 !important; left: 0 !important; width: 100vw; height: 72vh; max-height: 72vh; border-radius: 16px 16px 0 0; }
}
</style>
