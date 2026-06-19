<template>
  <BaseFab
    ref="fabRef"
    open-title="關閉 AI 調整"
    close-title="AI 調整報告"
    :panel-width="380"
    :panel-height="480"
  >
    <template #panel="{ close }">
      <div class="raf-head">
        <span class="raf-head__title">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          AI 調整報告
        </span>
        <button class="raf-head__close" title="關閉" @click="close">✕</button>
      </div>

      <div ref="logEl" class="raf-log">
        <div v-if="messages.length === 0" class="raf-empty">
          <p>輸入指令，AI 會幫你修改這份報告的內容。也可以要求 AI 先查詢你的知識庫再修改。</p>
          <div class="raf-examples">
            <button
              v-for="ex in EXAMPLES"
              :key="ex"
              class="raf-chip"
              type="button"
              :disabled="sending"
              @click="send(ex)"
            >{{ ex }}</button>
          </div>
        </div>

        <div v-for="m in messages" :key="m.id" class="raf-msg" :class="`raf-msg--${m.role}`">
          <!-- 思考過程 -->
          <div v-if="m.role === 'assistant' && m.steps.length" class="raf-process">
            <button class="raf-process__toggle" @click="toggleProcess(m.id)">
              <span class="raf-process__icon">💭</span>
              <span class="raf-process__label">思考過程</span>
              <svg class="raf-process__chevron" :class="{ 'raf-process__chevron--open': openProcess.has(m.id) }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><path d="M6 9l6 6 6-6"/></svg>
            </button>
            <div v-if="openProcess.has(m.id)" class="raf-process__body">
              <div v-for="(step, i) in m.steps" :key="i" class="raf-step">
                <div class="raf-step__call">
                  <span>{{ stepIcon(step.toolCall.name) }}</span>
                  <code class="raf-step__name">{{ step.toolCall.name }}</code>
                  <span v-if="step.toolCall.query" class="raf-step__param">"{{ step.toolCall.query }}"</span>
                  <span v-else-if="step.toolCall.title" class="raf-step__param">"{{ step.toolCall.title }}"</span>
                </div>
                <div v-if="step.toolResult !== null" class="raf-step__result">
                  <template v-if="step.toolCall.name === 'search'">
                    ✓ 找到 {{ step.toolResult.count }} 筆
                  </template>
                  <template v-else-if="step.toolResult.ok">✓ 完成</template>
                  <template v-else>⚠️ 失敗</template>
                </div>
                <div v-else class="raf-step__pending">⋯ 執行中</div>
              </div>
            </div>
          </div>

          <!-- 對話泡泡 -->
          <div v-if="m.text" class="raf-bubble">
            <TiptapEditor v-if="m.role === 'assistant'" :model-value="m.text" :readonly="true" class="raf-md" />
            <template v-else>{{ m.text }}</template>
          </div>

          <!-- 動作標籤 -->
          <div v-if="m.actions.length" class="raf-actions">
            <div v-for="(a, i) in m.actions" :key="i" class="raf-action">{{ a }}</div>
          </div>
        </div>

        <div v-if="sending && !streamingText" class="raf-thinking">
          <span class="raf-dot" /><span class="raf-dot" /><span class="raf-dot" />
        </div>
      </div>

      <form class="raf-input" @submit.prevent="send()">
        <textarea
          ref="inputEl"
          v-model="draft"
          class="raf-input__field"
          rows="1"
          :disabled="sending"
          placeholder="例如：讓語氣更輕鬆一點…"
          @keydown.enter.exact.prevent="send()"
        />
        <button
          class="raf-input__send"
          type="submit"
          :disabled="sending || !draft.trim()"
          :title="sending ? '處理中…' : '送出'"
        >
          <svg v-if="!sending" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>
          <span v-else class="raf-spin" />
        </button>
      </form>
    </template>
  </BaseFab>
</template>

<script setup lang="ts">
import type { Report } from '~/types/api'

const props = defineProps<{ reportId: string }>()
const emit = defineEmits<{ (e: 'revised', report: Report): void }>()

const config = useRuntimeConfig()
const session = useSupabaseSession()

const EXAMPLES = [
  '讓語氣更輕鬆易讀',
  '幫我加入更多細節',
  '精簡成重點摘要',
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
  if (name.startsWith('update_')) return '✏️'
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
    const resp = await fetch(`${apiBase}/reports/${props.reportId}/ai-edit`, {
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
          if (data.name === 'update_report' && data.ok && data._report) {
            emit('revised', data._report as Report)
            assistant.actions.push('✓ 報告已更新')
          }
          scrollLog()
        } else if (event === 'error') {
          assistant.actions.push('⚠️ ' + (data.message || '發生錯誤'))
        }
      }
    }
    if (!assistant.text && assistant.actions.length === 0) {
      assistant.text = '沒有需要調整的地方。'
    }
  } catch {
    assistant.actions.push('⚠️ AI 調整失敗，請稍後再試。')
  } finally {
    sending.value = false
    streamingText.value = ''
    scrollLog()
  }
}
</script>

<style scoped>
.raf-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 13px 14px; border-bottom: 1px solid var(--border); flex-shrink: 0;
}
.raf-head__title {
  display: inline-flex; align-items: center; gap: 7px;
  font-family: var(--font-brand); font-weight: 600; font-size: 14px; color: var(--text);
}
.raf-head__title svg { width: 16px; height: 16px; color: var(--accent); }
.raf-head__close { background: none; border: none; color: var(--text-dim); font-size: 15px; cursor: pointer; padding: 4px 7px; border-radius: 6px; }
.raf-head__close:hover { background: var(--surface2); color: var(--text); }

.raf-log { flex: 1 1 auto; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 12px; }
.raf-empty { color: var(--text-mid); font-size: 12.5px; line-height: 1.55; }
.raf-empty p { margin: 0 0 12px; }
.raf-examples { display: flex; flex-wrap: wrap; gap: 7px; }
.raf-chip {
  padding: 5px 11px; border-radius: 20px; font-size: 12px;
  border: 1px solid var(--border); background: var(--surface); color: var(--text-mid); cursor: pointer; transition: all .14s ease;
}
.raf-chip:hover { border-color: var(--accent-bdr); color: var(--accent); background: var(--accent-dim); }

.raf-msg { display: flex; flex-direction: column; gap: 6px; }
.raf-msg--user { align-items: flex-end; }

/* 思考過程 */
.raf-process {
  background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
  font-size: 12px; overflow: hidden; align-self: flex-start; max-width: 100%;
}
.raf-process__toggle {
  display: flex; align-items: center; gap: 5px; width: 100%;
  padding: 6px 10px; background: none; border: none; cursor: pointer;
  color: var(--text-mid); text-align: left;
}
.raf-process__toggle:hover { background: var(--surface2); }
.raf-process__icon { font-size: 12px; }
.raf-process__label { flex: 1; font-size: 11.5px; }
.raf-process__chevron { color: var(--text-dim); transition: transform .15s; flex-shrink: 0; }
.raf-process__chevron--open { transform: rotate(180deg); }
.raf-process__body { padding: 6px 10px 8px; display: flex; flex-direction: column; gap: 5px; border-top: 1px solid var(--border); }

.raf-step { display: flex; flex-direction: column; gap: 2px; }
.raf-step__call { display: flex; align-items: center; gap: 5px; color: var(--text-mid); font-size: 11.5px; }
.raf-step__name { font-family: var(--font-mono); font-size: 10.5px; background: var(--surface2); padding: 1px 5px; border-radius: 4px; color: var(--text); }
.raf-step__param { color: var(--text-dim); font-style: italic; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 160px; }
.raf-step__result { font-size: 11px; color: color-mix(in oklab, var(--tag-a, #34c759) 70%, var(--text)); padding-left: 2px; }
.raf-step__pending { font-size: 11px; color: var(--text-dim); padding-left: 2px; }

.raf-bubble {
  max-width: 92%; padding: 8px 12px; border-radius: 12px; font-size: 13px; line-height: 1.55;
  white-space: pre-wrap; word-break: break-word;
}
.raf-msg--user .raf-bubble { background: var(--accent); color: var(--accent-fg, #fff); border-bottom-right-radius: 4px; }
.raf-msg--assistant .raf-bubble { background: var(--surface2); color: var(--text); border-bottom-left-radius: 4px; white-space: normal; }

/* TipTap readonly 樣式覆蓋 */
.raf-md :deep(.tiptap) {
  padding: 0; outline: none;
  font-size: 13px; line-height: 1.55; color: var(--text);
}
.raf-md :deep(.tiptap p) { margin: 0 0 6px; }
.raf-md :deep(.tiptap p:last-child) { margin-bottom: 0; }
.raf-md :deep(.tiptap ul), .raf-md :deep(.tiptap ol) { padding-left: 18px; margin: 4px 0; }
.raf-md :deep(.tiptap li) { margin: 2px 0; }
.raf-md :deep(.tiptap h1), .raf-md :deep(.tiptap h2), .raf-md :deep(.tiptap h3) { font-size: 13px; font-weight: 600; margin: 6px 0 3px; }
.raf-md :deep(.tiptap code) { font-size: 11.5px; background: var(--surface); padding: 1px 4px; border-radius: 3px; }
.raf-md :deep(.tiptap pre) { background: var(--surface); border-radius: 6px; padding: 8px; margin: 4px 0; }

.raf-actions { display: flex; flex-direction: column; gap: 4px; }
.raf-action {
  font-size: 11.5px; color: var(--text-mid); font-family: var(--font-mono);
  background: color-mix(in oklab, var(--tag-a, #34c759) 12%, transparent);
  border: 1px solid color-mix(in oklab, var(--tag-a, #34c759) 24%, transparent);
  padding: 3px 9px; border-radius: 7px; width: fit-content;
}

.raf-thinking { display: flex; gap: 4px; padding: 4px 2px; }
.raf-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--text-dim); animation: raf-bounce 1.2s infinite ease-in-out; }
.raf-dot:nth-child(2) { animation-delay: .15s; }
.raf-dot:nth-child(3) { animation-delay: .3s; }
@keyframes raf-bounce { 0%, 80%, 100% { opacity: .3; transform: translateY(0); } 40% { opacity: 1; transform: translateY(-4px); } }

.raf-input { display: flex; align-items: flex-end; gap: 8px; padding: 12px 14px; border-top: 1px solid var(--border); flex-shrink: 0; }
.raf-input__field {
  flex: 1; resize: none; max-height: 96px; box-sizing: border-box;
  background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
  padding: 9px 11px; font-size: 13px; line-height: 1.5; color: var(--text); outline: none; font-family: inherit;
  transition: border-color .15s;
}
.raf-input__field:focus { border-color: var(--accent); }
.raf-input__send {
  flex: 0 0 auto; width: 38px; height: 38px; border-radius: 10px; border: none;
  background: var(--accent); color: var(--accent-fg, #fff); cursor: pointer;
  display: flex; align-items: center; justify-content: center; transition: opacity .15s, transform .12s;
}
.raf-input__send svg { width: 16px; height: 16px; }
.raf-input__send:disabled { opacity: .45; cursor: default; }
.raf-input__send:not(:disabled):hover { transform: scale(1.06); }
.raf-spin { width: 15px; height: 15px; border: 2px solid color-mix(in oklab, var(--accent-fg, #fff) 45%, transparent); border-top-color: var(--accent-fg, #fff); border-radius: 50%; animation: raf-rot .7s linear infinite; }
@keyframes raf-rot { to { transform: rotate(360deg); } }
</style>
