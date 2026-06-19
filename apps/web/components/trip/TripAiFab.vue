<template>
  <BaseFab
    ref="fabRef"
    open-title="關閉 AI 修改"
    close-title="AI 修改行程"
    :panel-width="380"
    :panel-height="520"
  >
    <template #panel="{ close }">
      <div class="taf-head">
        <span class="taf-head__title">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v3M12 18v3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M3 12h3M18 12h3M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"/></svg>
          AI 修改行程
        </span>
        <button class="taf-head__close" title="關閉" @click="close">✕</button>
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
          <!-- 思考過程 -->
          <div v-if="m.role === 'assistant' && m.steps.length" class="taf-process">
            <button class="taf-process__toggle" @click="toggleProcess(m.id)">
              <span class="taf-process__icon">💭</span>
              <span class="taf-process__label">思考過程</span>
              <svg class="taf-process__chevron" :class="{ 'taf-process__chevron--open': openProcess.has(m.id) }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><path d="M6 9l6 6 6-6"/></svg>
            </button>
            <div v-if="openProcess.has(m.id)" class="taf-process__body">
              <div v-for="(step, i) in m.steps" :key="i" class="taf-step">
                <div class="taf-step__call">
                  <span>{{ stepIcon(step.toolCall.name) }}</span>
                  <code class="taf-step__name">{{ step.toolCall.name }}</code>
                  <span v-if="step.toolCall.query" class="taf-step__param">"{{ step.toolCall.query }}"</span>
                  <span v-else-if="step.toolCall.title" class="taf-step__param">"{{ step.toolCall.title }}"</span>
                </div>
                <div v-if="step.toolResult !== null" class="taf-step__result">
                  <template v-if="step.toolCall.name === 'search'">
                    ✓ 找到 {{ step.toolResult.count }} 筆
                  </template>
                  <template v-else-if="step.toolResult.ok">✓ 完成</template>
                  <template v-else>⚠️ 失敗</template>
                </div>
                <div v-else class="taf-step__pending">⋯ 執行中</div>
              </div>
            </div>
          </div>

          <!-- 對話泡泡 -->
          <div v-if="m.text" class="taf-bubble">
            <TiptapEditor v-if="m.role === 'assistant'" :model-value="m.text" :readonly="true" class="taf-md" />
            <template v-else>{{ m.text }}</template>
          </div>

          <!-- 動作標籤 -->
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
    </template>
  </BaseFab>
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

const fabRef = ref()
const inputEl = ref<HTMLTextAreaElement | null>(null)
const logEl = ref<HTMLElement | null>(null)
const draft = ref('')
const sending = ref(false)
const streamingText = ref('')

interface Step { toolCall: Record<string, any>; toolResult: Record<string, any> | null }
interface Msg { id: string; role: 'user' | 'assistant'; text: string; actions: string[]; steps: Step[] }
const messages = ref<Msg[]>([])

const openProcess = ref(new Set<string>())
function toggleProcess(id: string) {
  openProcess.value.has(id) ? openProcess.value.delete(id) : openProcess.value.add(id)
}
function stepIcon(name: string): string {
  if (name === 'search') return '🔍'
  if (name.startsWith('add_') || name.startsWith('create_')) return '➕'
  if (name.startsWith('update_')) return '✏️'
  if (name.startsWith('delete_')) return '🗑️'
  return '⚙️'
}

watch(() => fabRef.value?.open, (val) => {
  if (val) nextTick(() => inputEl.value?.focus())
})

function scrollLog() {
  nextTick(() => { if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight })
}

async function send(preset?: string) {
  const content = (preset ?? draft.value).trim()
  if (!content || sending.value) return
  draft.value = ''
  sending.value = true
  streamingText.value = ''

  const history = messages.value
    .map((m) => {
      const text = m.text || (m.actions.length ? m.actions.join('；') : '')
      return text ? { role: m.role, content: text } : null
    })
    .filter((t): t is { role: 'user' | 'assistant'; content: string } => t !== null)
    .slice(-12)

  messages.value.push({ id: crypto.randomUUID(), role: 'user', text: content, actions: [], steps: [] })
  const assistant: Msg = { id: crypto.randomUUID(), role: 'assistant', text: '', actions: [], steps: [] }
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
        } else if (event === 'tool_call') {
          assistant.steps.push({ toolCall: data, toolResult: null })
          openProcess.value.add(assistant.id)
          scrollLog()
        } else if (event === 'tool_result') {
          if (assistant.steps.length) {
            assistant.steps[assistant.steps.length - 1].toolResult = data
          }
          handleToolResult(data, assistant)
          scrollLog()
        } else if (event === 'error') {
          assistant.actions.push('⚠️ ' + (data.message || '發生錯誤'))
        } else if (event === 'done') {
          emit('done')
        }
      }
    }
    if (!assistant.text && assistant.actions.length === 0 && assistant.steps.every(s => s.toolResult !== null)) {
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
  if (data.name === 'search') return  // shown in process block only
  if (data.name === 'save_url') {
    if (data.ok) {
      assistant.actions.push(`📥 已存入「${data.title || ''}」`)
    } else if (data.error === 'quota_exceeded') {
      assistant.actions.push('⚠️ 存入額度已用完')
    } else {
      assistant.actions.push('⚠️ 存入失敗')
    }
    return
  }
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
</script>

<style scoped>
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

/* 思考過程 */
.taf-process {
  background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
  font-size: 12px; overflow: hidden; align-self: flex-start; max-width: 100%;
}
.taf-process__toggle {
  display: flex; align-items: center; gap: 5px; width: 100%;
  padding: 6px 10px; background: none; border: none; cursor: pointer;
  color: var(--text-mid); text-align: left;
}
.taf-process__toggle:hover { background: var(--surface2); }
.taf-process__icon { font-size: 12px; }
.taf-process__label { flex: 1; font-size: 11.5px; }
.taf-process__chevron { color: var(--text-dim); transition: transform .15s; flex-shrink: 0; }
.taf-process__chevron--open { transform: rotate(180deg); }
.taf-process__body { padding: 6px 10px 8px; display: flex; flex-direction: column; gap: 5px; border-top: 1px solid var(--border); }

.taf-step { display: flex; flex-direction: column; gap: 2px; }
.taf-step__call { display: flex; align-items: center; gap: 5px; color: var(--text-mid); font-size: 11.5px; }
.taf-step__name { font-family: var(--font-mono); font-size: 10.5px; background: var(--surface2); padding: 1px 5px; border-radius: 4px; color: var(--text); }
.taf-step__param { color: var(--text-dim); font-style: italic; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 160px; }
.taf-step__result { font-size: 11px; color: color-mix(in oklab, var(--tag-a, #34c759) 70%, var(--text)); padding-left: 2px; }
.taf-step__pending { font-size: 11px; color: var(--text-dim); padding-left: 2px; }

.taf-bubble {
  max-width: 92%; padding: 8px 12px; border-radius: 12px; font-size: 13px; line-height: 1.55;
  white-space: pre-wrap; word-break: break-word;
}
.taf-msg--user .taf-bubble { background: var(--accent); color: var(--accent-fg, #fff); border-bottom-right-radius: 4px; }
.taf-msg--assistant .taf-bubble { background: var(--surface2); color: var(--text); border-bottom-left-radius: 4px; white-space: normal; }

/* TipTap readonly 樣式覆蓋 */
.taf-md :deep(.tiptap) {
  padding: 0; outline: none;
  font-size: 13px; line-height: 1.55; color: var(--text);
}
.taf-md :deep(.tiptap p) { margin: 0 0 6px; }
.taf-md :deep(.tiptap p:last-child) { margin-bottom: 0; }
.taf-md :deep(.tiptap ul), .taf-md :deep(.tiptap ol) { padding-left: 18px; margin: 4px 0; }
.taf-md :deep(.tiptap li) { margin: 2px 0; }
.taf-md :deep(.tiptap h1), .taf-md :deep(.tiptap h2), .taf-md :deep(.tiptap h3) { font-size: 13px; font-weight: 600; margin: 6px 0 3px; }
.taf-md :deep(.tiptap code) { font-size: 11.5px; background: var(--surface); padding: 1px 4px; border-radius: 3px; }
.taf-md :deep(.tiptap pre) { background: var(--surface); border-radius: 6px; padding: 8px; margin: 4px 0; }

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
</style>
