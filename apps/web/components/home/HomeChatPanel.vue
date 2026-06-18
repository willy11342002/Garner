<template>
  <div class="hcp">
    <!-- Header -->
    <div class="hcp__head">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="15" height="15"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      <span class="hcp__title">{{ sessionTitle }}</span>
      <span class="hcp__quota-badge" :class="{ 'hcp__quota-badge--empty': chatQuotaFull }">
        {{ chatQuotaFull ? t('fab.quota_full') : t('fab.quota_warn', { n: chatQuotaRemaining }) }}
      </span>
      <button class="hcp__close" @click="emit('close')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M18 6L6 18M6 6l12 12"/></svg>
      </button>
    </div>

    <!-- Messages -->
    <div ref="messagesEl" class="hcp__messages">
      <div v-if="!messages.length" class="hcp__empty">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="32" height="32"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        <p>{{ t('fab.empty') }}</p>
      </div>

      <template v-for="msg in messages" :key="msg.id">
        <div class="msg" :class="`msg--${msg.role}`">
          <!-- user context block -->
          <template v-if="msg.role === 'user' && userContextMap[msg.id]?.length">
            <div class="context-block">
              <button class="context-block__toggle" @click="toggleContext(msg.id)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
                <span class="context-block__label">{{ t('fab.nodes', { n: userContextMap[msg.id].length }) }}</span>
                <svg class="process-block__chevron" :class="{ 'process-block__chevron--open': openContexts.has(msg.id) }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M6 9l6 6 6-6"/></svg>
              </button>
              <Transition name="thinking">
                <div v-if="openContexts.has(msg.id)" class="context-block__body">
                  <div v-for="item in userContextMap[msg.id]" :key="item.id" class="src-card">
                    <img v-if="item.thumbnail_url" :src="item.thumbnail_url" :alt="item.title || ''" class="src-card__thumb">
                    <div v-else class="src-card__thumb src-card__thumb--empty"></div>
                    <div class="src-card__body">
                      <span class="src-card__title">{{ item.title || item.url }}</span>
                      <span class="src-card__type">{{ sourceLabel(item.source_type) }}</span>
                    </div>
                  </div>
                </div>
              </Transition>
            </div>
          </template>

          <!-- assistant process block -->
          <template v-if="msg.role === 'assistant' && processMap[msg.id]">
            <div class="process-block">
              <button class="process-block__toggle" @click="toggleThinking(msg.id)">
                <span class="process-block__icon">💭</span>
                <span class="process-block__label">{{ t('fab.thinking') }}</span>
                <svg class="process-block__chevron" :class="{ 'process-block__chevron--open': openThinking.has(msg.id) }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M6 9l6 6 6-6"/></svg>
              </button>
              <Transition name="thinking">
                <div v-if="openThinking.has(msg.id)" class="process-block__body">
                  <p v-if="processMap[msg.id].thinking" class="process-body__reasoning">{{ processMap[msg.id].thinking }}</p>
                  <div v-for="(step, i) in processMap[msg.id].steps" :key="i" class="process-body__step">
                    <div class="process-body__tool-call">
                      <span class="process-body__step-icon">🔍</span>
                      <code class="process-body__tool-name">{{ step.toolCall.name }}</code>
                      <span v-if="step.toolCall.query" class="process-body__param">query: "{{ step.toolCall.query }}"</span>
                    </div>
                    <div v-if="step.toolResult" class="process-body__tool-result">
                      <span class="process-body__step-icon">✓</span>
                      <span v-if="step.toolCall.name === 'create_report'">報告已建立：{{ step.toolResult.title }}</span>
                      <span v-else-if="step.toolCall.name === 'save_url'">{{ step.toolResult.ok ? `已存入「${step.toolResult.title}」` : (step.toolResult.error === 'quota_exceeded' ? '存入額度已用完' : '存入失敗') }}</span>
                      <span v-else>找到 {{ step.toolResult.count }} 筆</span>
                      <button
                        v-if="step.toolResult?.titles?.length"
                        class="process-body__step-toggle"
                        @click="toggleStep(msg.id, i)"
                      >
                        <svg :class="{ 'process-body__step-chevron--open': openSteps.has(`${msg.id}-${i}`) }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="11" height="11"><path d="M6 9l6 6 6-6"/></svg>
                      </button>
                    </div>
                    <Transition name="thinking">
                      <div v-if="step.toolResult?.titles?.length && openSteps.has(`${msg.id}-${i}`)" class="process-body__tool-titles">
                        <button v-for="item in step.toolResult.titles" :key="item.id ?? item" class="process-body__tool-title" @click="previewItemId = item.id ?? null">{{ item.title ?? item }}</button>
                      </div>
                    </Transition>
                  </div>
                </div>
              </Transition>
            </div>
          </template>

          <div class="msg__bubble">
            <template v-if="msg.role === 'assistant'">
              <TiptapEditor :model-value="msg.content" readonly />
            </template>
            <template v-else>{{ msg.content }}</template>
          </div>
        </div>
      </template>

      <!-- Streaming / loading -->
      <div v-if="loading || streamingText" class="msg msg--assistant">
        <div v-if="liveProcess.thinking || liveProcess.steps.length" class="process-block">
          <button class="process-block__toggle" @click="toggleThinking('live')">
            <span class="process-block__icon">💭</span>
            <span class="process-block__label">思考中</span>
            <svg class="process-block__chevron" :class="{ 'process-block__chevron--open': openThinking.has('live') }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M6 9l6 6 6-6"/></svg>
          </button>
          <Transition name="thinking">
            <div v-if="openThinking.has('live')" class="process-block__body">
              <p v-if="liveProcess.thinking" class="process-body__reasoning">{{ liveProcess.thinking }}</p>
              <div v-for="(step, i) in liveProcess.steps" :key="i" class="process-body__step">
                <div class="process-body__tool-call">
                  <span class="process-body__step-icon">🔍</span>
                  <code class="process-body__tool-name">{{ step.toolCall.name }}</code>
                  <span v-if="step.toolCall.query" class="process-body__param">query: "{{ step.toolCall.query }}"</span>
                </div>
                <div v-if="step.toolResult" class="process-body__tool-result">
                  <span class="process-body__step-icon">✓</span>
                  <span v-if="step.toolCall.name === 'create_report'">報告已建立：{{ step.toolResult.title }}</span>
                  <span v-else-if="step.toolCall.name === 'save_url'">{{ step.toolResult.ok ? `已存入「${step.toolResult.title}」` : (step.toolResult.error === 'quota_exceeded' ? '存入額度已用完' : '存入失敗') }}</span>
                  <span v-else>找到 {{ step.toolResult.count }} 筆</span>
                  <button
                    v-if="step.toolResult?.titles?.length"
                    class="process-body__step-toggle"
                    @click="toggleStep('live', i)"
                  >
                    <svg :class="{ 'process-body__step-chevron--open': openSteps.has(`live-${i}`) }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="11" height="11"><path d="M6 9l6 6 6-6"/></svg>
                  </button>
                </div>
                <Transition name="thinking">
                  <div v-if="step.toolResult?.titles?.length && openSteps.has(`live-${i}`)" class="process-body__tool-titles">
                    <div v-for="title in step.toolResult.titles" :key="title" class="process-body__tool-title">{{ title }}</div>
                  </div>
                </Transition>
                <div v-if="!step.toolResult" class="process-body__tool-result process-body__tool-result--pending">
                  <span class="process-body__step-icon">⋯</span>
                  <span>{{ step.toolCall.name === 'create_report' ? '生成中' : step.toolCall.name === 'save_url' ? '存入中' : t('fab.searching') }}</span>
                </div>
              </div>
            </div>
          </Transition>
        </div>
        <div v-if="loading && !streamingText" class="msg-thinking">
          <span></span><span></span><span></span>
        </div>
        <div v-if="streamingText" class="msg__bubble msg__bubble--streaming">
          <TiptapEditor :model-value="streamingText" readonly class="streaming-md" />
        </div>
      </div>
    </div>

    <!-- Chain attachments -->
    <div v-if="chainItems.length" class="hcp__chain">
      <div class="hcp__chain-nodes">
        <div v-for="item in chainItems" :key="item.id" class="hcp__node">
          <img v-if="item.thumbnail_url" :src="item.thumbnail_url" :alt="item.title || ''" class="hcp__node-thumb">
          <div v-else class="hcp__node-thumb hcp__node-thumb--empty"></div>
          <span class="hcp__node-label">{{ truncate(item.title || item.url || '', 16) }}</span>
          <button class="hcp__node-remove" @click="chain.remove(item.id)">×</button>
        </div>
      </div>
      <button class="hcp__chain-clear" @click="chain.clear()">{{ t('fab.chain_clear') }}</button>
    </div>

    <!-- Input -->
    <div class="hcp__input-wrap">
      <div class="chat-input-box" :class="{ 'chat-input-box--disabled': chatQuotaFull }">
        <textarea
          ref="inputEl"
          v-model="inputText"
          class="chat-input"
          :placeholder="chatQuotaFull ? t('fab.placeholder_full') : t('fab.placeholder')"
          :disabled="chatQuotaFull"
          rows="1"
          @keydown.enter.exact.prevent="send"
          @input="autoResize"
        ></textarea>
        <button class="chat-send-btn" :disabled="loading || !inputText.trim() || chatQuotaFull" @click="send">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" width="16" height="16"><path d="M12 19V5M5 12l7-7 7 7"/></svg>
        </button>
      </div>
    </div>
  </div>
  <ItemDetailModal :item-id="previewItemId" @close="previewItemId = null" />
</template>

<script setup lang="ts">
import type { ChatMessage, ChatSession, ChatSessionDetail, ChatSource, UsageSummary } from '~/types/api'

const emit = defineEmits<{ close: [] }>()

const { t } = useI18n()
const apiFetch = useApiFetch()
const config = useRuntimeConfig()
const session = useSupabaseSession()
const chain = useChain()
const { chainItems } = chain

const SOURCE_LABELS: Record<string, string> = { youtube: '▶ YouTube', article: 'Article', ig: 'IG' }

// ── Quota ──────────────────────────────────────────────────
const quota = ref<UsageSummary | null>(null)
const chatQuotaFull = computed(() => {
  const q = quota.value?.chat
  return !!q && q.limit !== null && q.used >= q.limit
})
const chatQuotaRemaining = computed(() => {
  const q = quota.value?.chat
  if (!q || q.limit === null) return null
  return Math.max(0, q.limit - q.used)
})
const quotaWarning = computed(() => {
  const q = quota.value?.chat
  if (!q || q.limit === null) return false
  const remaining = q.limit - q.used
  return remaining <= Math.ceil(q.limit * 0.2) // 剩餘 ≤ 20% 才顯示
})
onMounted(async () => {
  try { quota.value = await apiFetch<UsageSummary>('/quota/me') } catch {}
})

// ── Session ────────────────────────────────────────────────
const previewItemId = ref<string | null>(null)
const activeSessionId = ref<string | null>(null)
const activeSession = ref<ChatSessionDetail | null>(null)
const sessionTitle = computed(() => activeSession.value?.title || t('fab.title'))

async function ensureSession(): Promise<string> {
  if (activeSessionId.value) return activeSessionId.value
  const s = await apiFetch<ChatSession>('/chat/sessions', { method: 'POST', body: {} })
  activeSessionId.value = s.id
  activeSession.value = { ...s, messages: [] }
  return s.id
}

// ── Messages ───────────────────────────────────────────────
const messages = ref<ChatMessage[]>([])
const sourcesMap = ref<Record<string, ChatSource[]>>({})
const userContextMap = ref<Record<string, ChatSource[]>>({})
const inputText = ref('')
const loading = ref(false)
const streamingText = ref('')

const openThinking = ref<Set<string>>(new Set(['live']))
const openSteps = ref<Set<string>>(new Set())
const openContexts = ref<Set<string>>(new Set())

function toggleStep(msgId: string, stepIdx: number) {
  const key = `${msgId}-${stepIdx}`
  const s = openSteps.value
  s.has(key) ? s.delete(key) : s.add(key)
  openSteps.value = new Set(s)
}
const openSources = ref<Set<string>>(new Set())

type ProcessStep = { toolCall: Record<string, any>; toolResult: { count: number; titles: string[]; title?: string } | null }
type ProcessLog = { thinking: string; steps: ProcessStep[]; sources: ChatSource[] }
const liveProcess = ref<ProcessLog>({ thinking: '', steps: [], sources: [] })
const processMap = ref<Record<string, ProcessLog>>({})

const messagesEl = ref<HTMLElement | null>(null)
const inputEl = ref<HTMLTextAreaElement | null>(null)

function resetProcess() {
  liveProcess.value = { thinking: '', steps: [], sources: [] }
  streamingText.value = ''
  openThinking.value = new Set(['live'])
  openSources.value.delete('live')
}

function toggleThinking(id: string) {
  const s = openThinking.value
  s.has(id) ? s.delete(id) : s.add(id)
  openThinking.value = new Set(s)
}

function toggleSources(id: string) {
  const s = openSources.value
  s.has(id) ? s.delete(id) : s.add(id)
  openSources.value = new Set(s)
}

function toggleContext(id: string) {
  const s = openContexts.value
  s.has(id) ? s.delete(id) : s.add(id)
  openContexts.value = new Set(s)
}

async function send() {
  if (!inputText.value.trim() || loading.value || chatQuotaFull.value) return

  const content = inputText.value.trim()
  inputText.value = ''
  resetInputHeight()
  loading.value = true
  resetProcess()

  const sessionId = await ensureSession()

  const itemIds = chainItems.value.map(i => i.id)
  chain.clear()

  const userMsg: ChatMessage = {
    id: crypto.randomUUID(),
    role: 'user',
    content,
    cited_item_ids: itemIds.length ? itemIds : null,
    created_at: new Date().toISOString(),
  }
  messages.value.push(userMsg)
  await nextTick()
  scrollBottom()

  const apiBase = config.public.apiBase as string
  const token = session.value?.access_token
  const isFirstMessage = messages.value.filter(m => m.role === 'user').length === 1

  if (itemIds.length) {
    const msgId = userMsg.id
    Promise.allSettled(itemIds.map(id => apiFetch<ChatSource>(`/items/${id}`))).then(results => {
      const items = results.filter((r): r is PromiseFulfilledResult<ChatSource> => r.status === 'fulfilled').map(r => r.value)
      if (items.length) {
        userContextMap.value[msgId] = items
        openContexts.value = new Set([...openContexts.value, msgId])
      }
    })
  }

  try {
    const resp = await fetch(`${apiBase}/chat/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ content, ...(itemIds.length ? { item_ids: itemIds } : {}) }),
    })
    if (!resp.ok) throw new Error('request failed')

    const reader = resp.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let pendingCitedSources: ChatSource[] = []
    const assistantId = crypto.randomUUID()

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
        const data = JSON.parse(lines[1].replace('data: ', ''))

        if (event === 'thinking') {
          liveProcess.value.thinking = data.text
          await nextTick(); scrollBottom()
        } else if (event === 'tool_call') {
          liveProcess.value.steps.push({ toolCall: data, toolResult: null })
          await nextTick(); scrollBottom()
        } else if (event === 'tool_result') {
          const steps = liveProcess.value.steps
          if (steps.length) steps[steps.length - 1].toolResult = { count: data.count, titles: data.titles, title: data.title }
          await nextTick(); scrollBottom()
        } else if (event === 'sources') {
          liveProcess.value.sources = data as ChatSource[]
        } else if (event === 'cited_sources') {
          pendingCitedSources = data as ChatSource[]
        } else if (event === 'delta') {
          streamingText.value += data.text
          await nextTick(); scrollBottom()
        } else if (event === 'done') {
          processMap.value[assistantId] = { thinking: liveProcess.value.thinking, steps: liveProcess.value.steps, sources: liveProcess.value.sources }
          openThinking.value.delete('live')
          openThinking.value.add(assistantId)

          const assistantMsg: ChatMessage = {
            id: assistantId,
            role: 'assistant',
            content: streamingText.value,
            cited_item_ids: pendingCitedSources.map(s => s.id),
            created_at: new Date().toISOString(),
          }
          messages.value.push(assistantMsg)
          if (pendingCitedSources.length) {
            sourcesMap.value[assistantId] = pendingCitedSources
          }

          if (isFirstMessage && !activeSession.value?.title) {
            const title = content.slice(0, 40) + (content.length > 40 ? '…' : '')
            if (activeSession.value) activeSession.value.title = title
          }

          resetProcess()
          await nextTick(); scrollBottom()
        }
      }
    }
  } catch {
    resetProcess()
    messages.value.push({
      id: crypto.randomUUID(),
      role: 'assistant',
      content: t('fab.error'),
      cited_item_ids: null,
      created_at: new Date().toISOString(),
    })
  } finally {
    loading.value = false
  }
}

function scrollBottom() {
  if (messagesEl.value) messagesEl.value.scrollTo({ top: messagesEl.value.scrollHeight, behavior: 'smooth' })
}

function autoResize() {
  if (!inputEl.value) return
  inputEl.value.style.height = 'auto'
  inputEl.value.style.height = Math.min(inputEl.value.scrollHeight, 120) + 'px'
}

function resetInputHeight() {
  if (inputEl.value) inputEl.value.style.height = ''
}

function truncate(str: string, len: number) {
  return str.length > len ? str.slice(0, len) + '...' : str
}

function sourceLabel(type: string | null) {
  return type ? (SOURCE_LABELS[type] ?? type) : 'Article'
}
</script>

<style scoped>
.hcp {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg);
  overflow: hidden;
}

/* Header */
.hcp__head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px 11px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  color: var(--text-dim);
}
.hcp__title {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.hcp__quota-badge {
  font-family: var(--font-mono);
  font-size: 10.5px;
  padding: 2px 7px;
  border-radius: 5px;
  background: color-mix(in oklab, var(--warn) 10%, transparent);
  color: var(--warn);
  border: 1px solid color-mix(in oklab, var(--warn) 28%, transparent);
  white-space: nowrap;
  flex-shrink: 0;
}
.hcp__quota-badge--empty {
  background: color-mix(in oklab, var(--danger) 10%, transparent);
  color: var(--danger);
  border-color: color-mix(in oklab, var(--danger) 28%, transparent);
}

.hcp__close {
  width: 26px;
  height: 26px;
  border: none;
  background: transparent;
  color: var(--text-dim);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  flex-shrink: 0;
  transition: background .12s, color .12s;
}
.hcp__close:hover {
  background: var(--surface2);
  color: var(--text);
}

/* Messages */
.hcp__messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 14px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.hcp__empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--text-dim);
  font-size: 13px;
  text-align: center;
  padding: 40px 20px;
}
.hcp__empty p { margin: 0; }

/* Raw search result titles in process block */
.process-body__tool-titles {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-left: 20px;
  margin-top: 3px;
}
.process-body__tool-title {
  font-size: 11px;
  color: var(--text-dim);
  padding: 2px 6px;
  border-left: 2px solid var(--border2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Tiptap in assistant bubble */
.hcp .msg--assistant .msg__bubble { white-space: normal; }
.hcp .msg--assistant .msg__bubble :deep(.tiptap-wrap) { font-size: 13px; line-height: 1.7; }
.hcp .msg--assistant .msg__bubble :deep(.tiptap-root) { position: static; }

/* Override bubble widths for panel */
.hcp .msg__bubble,
.hcp .msg__bubble--streaming,
.hcp .sources-list,
.hcp .process-block,
.hcp .context-block {
  width: 100%;
  max-width: 100%;
  text-wrap: auto;
  overflow-wrap: break-word;
}

/* Chain attachments */
.hcp__chain {
  padding: 8px 14px;
  border-top: 1px solid var(--border);
  background: var(--surface);
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.hcp__chain-nodes {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-width: 0;
}
.hcp__node {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 3px 6px 3px 4px;
  background: var(--surface2);
  border: 1px solid var(--border2);
  border-radius: 7px;
  max-width: 160px;
}
.hcp__node-thumb {
  width: 22px;
  height: 16px;
  border-radius: 3px;
  object-fit: cover;
  flex-shrink: 0;
}
.hcp__node-thumb--empty {
  background: var(--surface3);
}
.hcp__node-label {
  font-size: 11px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
  color: var(--text);
}
.hcp__node-remove {
  flex-shrink: 0;
  width: 14px;
  height: 14px;
  border: none;
  background: transparent;
  color: var(--text-dim);
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border-radius: 3px;
  transition: color .1s, background .1s;
}
.hcp__node-remove:hover {
  color: var(--danger);
  background: var(--danger-dim);
}
.hcp__chain-clear {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--text-dim);
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  transition: color .12s;
  white-space: nowrap;
  align-self: center;
}
.hcp__chain-clear:hover { color: var(--text); }

/* Input */
.hcp__input-wrap {
  padding: 10px 14px 14px;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}

/* streaming 游標 */
:deep(.streaming-md .tiptap-root p:last-child::after) {
  content: '▍';
  display: inline;
  color: var(--accent);
  animation: blink 1s step-start infinite;
}
@keyframes blink { 50% { opacity: 0; } }
</style>
