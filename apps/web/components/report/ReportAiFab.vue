<template>
  <BaseFab
    ref="fabRef"
    open-title="關閉 AI 調整"
    close-title="AI 調整報告"
    :panel-width="380"
    :panel-height="380"
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
          <p>輸入指令，AI 會幫你修改這份報告的內容。</p>
          <div class="raf-examples">
            <button
              v-for="ex in EXAMPLES"
              :key="ex"
              class="raf-chip"
              type="button"
              :disabled="busy"
              @click="submitRevise(ex)"
            >{{ ex }}</button>
          </div>
        </div>

        <div v-for="m in messages" :key="m.id" class="raf-msg" :class="`raf-msg--${m.role}`">
          <div v-if="m.text" class="raf-bubble">{{ m.text }}</div>
        </div>

        <div v-if="busy && messages.length > 0" class="raf-thinking">
          <span class="raf-dot" /><span class="raf-dot" /><span class="raf-dot" />
        </div>
      </div>

      <form class="raf-input" @submit.prevent="submitRevise()">
        <textarea
          ref="inputEl"
          v-model="draft"
          class="raf-input__field"
          rows="1"
          :disabled="busy"
          placeholder="例如：讓語氣更輕鬆一點…"
          @keydown.enter.exact.prevent="submitRevise()"
        />
        <button
          class="raf-input__send"
          type="submit"
          :disabled="busy || !draft.trim()"
          :title="busy ? '處理中…' : '送出'"
        >
          <svg v-if="!busy" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>
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

const { reviseReport } = useReports()

const EXAMPLES = [
  '讓語氣更輕鬆易讀',
  '幫我加入更多細節',
  '精簡成重點摘要',
]

const fabRef = ref()
const inputEl = ref<HTMLTextAreaElement | null>(null)
const logEl = ref<HTMLElement | null>(null)
const draft = ref('')
const busy = ref(false)

interface Msg { id: string; role: 'user' | 'assistant'; text: string }
const messages = ref<Msg[]>([])

watch(() => fabRef.value?.open, (val) => {
  if (val) nextTick(() => inputEl.value?.focus())
})

function scrollLog() {
  nextTick(() => { if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight })
}

async function submitRevise(preset?: string) {
  const instruction = (preset ?? draft.value).trim()
  if (!instruction || busy.value) return
  draft.value = ''
  busy.value = true

  messages.value.push({ id: crypto.randomUUID(), role: 'user', text: instruction })
  scrollLog()

  try {
    const updated = await reviseReport(props.reportId, instruction)
    emit('revised', updated)
    messages.value.push({ id: crypto.randomUUID(), role: 'assistant', text: '✓ 報告已更新。' })
  } catch {
    messages.value.push({ id: crypto.randomUUID(), role: 'assistant', text: '⚠️ 調整失敗，請稍後再試。' })
  } finally {
    busy.value = false
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
.raf-bubble {
  max-width: 85%; padding: 8px 12px; border-radius: 12px; font-size: 13px; line-height: 1.55;
  white-space: pre-wrap; word-break: break-word;
}
.raf-msg--user .raf-bubble { background: var(--accent); color: var(--accent-fg, #fff); border-bottom-right-radius: 4px; }
.raf-msg--assistant .raf-bubble { background: var(--surface2); color: var(--text); border-bottom-left-radius: 4px; }

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
