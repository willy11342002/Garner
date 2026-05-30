<template>
  <div class="chat-page">
    <!-- 左側：session 列表 -->
    <aside class="chat-list">
      <div class="chat-list__head">
        <span class="chat-list__title">{{ t('chat.title') }}</span>
        <button class="chat-icon-btn" :title="t('chat.new')" @click="newSession">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><path d="M12 5v14M5 12h14"/></svg>
        </button>
      </div>
      <div class="chat-list__body">
        <div v-if="unfoldered.length" class="session-group">
          <ChatSessionRow
            v-for="s in unfoldered"
            :key="s.id"
            :session="s"
            :active="activeSessionId === s.id"
            @click="openSession(s.id)"
            @rename="(id, name) => renameSession(id, name)"
            @delete="deleteSession(s.id)"
          />
        </div>
        <div v-for="folder in folders" :key="folder.id" class="folder-block">
          <div class="folder-block__label">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>
            {{ folder.name }}
          </div>
          <ChatSessionRow
            v-for="s in sessionsInFolder(folder.id)"
            :key="s.id"
            :session="s"
            :active="activeSessionId === s.id"
            indent
            @click="openSession(s.id)"
            @rename="(id, name) => renameSession(id, name)"
            @delete="deleteSession(s.id)"
          />
        </div>
        <div v-if="!sessions.length" class="chat-list__empty">{{ t('chat.empty_list') }}</div>
      </div>
    </aside>

    <!-- 右側：對話區 -->
    <div class="chat-view">
      <div v-if="!activeSessionId" class="chat-welcome">
        <div class="chat-welcome__icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="44" height="44"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        </div>
        <h2 class="chat-welcome__title">{{ t('chat.welcome_title') }}</h2>
        <p class="chat-welcome__desc">{{ t('chat.welcome_desc') }}</p>
        <button class="btn btn--accent" @click="newSession">{{ t('chat.start') }}</button>
      </div>

      <template v-else>
        <div class="chat-view__head">
          <span class="chat-view__title">{{ activeSession?.title || t('chat.untitled') }}</span>
        </div>

        <div ref="messagesEl" class="chat-view__messages">
          <!-- 歷史訊息 -->
          <template v-for="msg in messages" :key="msg.id">
            <div class="msg" :class="`msg--${msg.role}`">
              <div class="msg__bubble">{{ msg.content }}</div>
              <div v-if="msg.role === 'assistant' && sourcesMap[msg.id]?.length" class="msg__sources">
                <NuxtLink
                  v-for="src in sourcesMap[msg.id]"
                  :key="src.id"
                  class="src-card"
                  :to="`/app/item/${src.id}`"
                >
                  <img v-if="src.thumbnail_url" :src="src.thumbnail_url" :alt="src.title || ''" class="src-card__thumb">
                  <div v-else class="src-card__thumb src-card__thumb--empty"></div>
                  <div class="src-card__body">
                    <span class="src-card__title">{{ src.title || src.url }}</span>
                    <span class="src-card__type">{{ sourceLabel(src.source_type) }}</span>
                  </div>
                </NuxtLink>
              </div>
            </div>
          </template>

          <!-- 進行中的 agentic process -->
          <div v-if="loading || streamingText" class="msg msg--assistant">
            <!-- 思考過程（可收合） -->
            <div v-if="process.thinking" class="process-block">
              <button class="process-block__toggle" @click="thinkingOpen = !thinkingOpen">
                <span class="process-block__icon">💭</span>
                <span class="process-block__label">{{ t('chat.thinking') }}</span>
                <svg class="process-block__chevron" :class="{ 'process-block__chevron--open': thinkingOpen }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M6 9l6 6 6-6"/></svg>
              </button>
              <div v-if="thinkingOpen" class="process-block__body">{{ process.thinking }}</div>
            </div>

            <!-- Tool call -->
            <div v-if="process.toolCall" class="process-step process-step--tool">
              <span class="process-step__icon">🔍</span>
              <span class="process-step__label">{{ t('chat.tool_call') }}</span>
              <code class="process-step__query">{{ process.toolCall.query }}</code>
            </div>

            <!-- Tool result -->
            <div v-if="process.toolResult" class="process-step process-step--result">
              <span class="process-step__icon">✓</span>
              <span class="process-step__label">{{ t('chat.tool_result', { count: process.toolResult.count }) }}</span>
              <span v-if="process.toolResult.titles.length" class="process-step__titles">
                {{ process.toolResult.titles.join('、') }}
              </span>
            </div>

            <!-- 等待開始串流 -->
            <div v-if="loading && !streamingText" class="msg-thinking">
              <span></span><span></span><span></span>
            </div>

            <!-- 串流中的回覆 -->
            <div v-if="streamingText" class="msg__bubble msg__bubble--streaming">
              {{ streamingText }}<span class="cursor">▍</span>
            </div>

            <!-- 串流完成的 sources -->
            <div v-if="process.sources.length" class="msg__sources">
              <NuxtLink
                v-for="src in process.sources"
                :key="src.id"
                class="src-card"
                :to="`/app/item/${src.id}`"
              >
                <img v-if="src.thumbnail_url" :src="src.thumbnail_url" :alt="src.title || ''" class="src-card__thumb">
                <div v-else class="src-card__thumb src-card__thumb--empty"></div>
                <div class="src-card__body">
                  <span class="src-card__title">{{ src.title || src.url }}</span>
                  <span class="src-card__type">{{ sourceLabel(src.source_type) }}</span>
                </div>
              </NuxtLink>
            </div>
          </div>
        </div>

        <div class="chat-view__input-wrap">
          <div class="chat-input-box">
            <textarea
              ref="inputEl"
              v-model="inputText"
              class="chat-input"
              :placeholder="t('chat.placeholder')"
              rows="1"
              @keydown.enter.exact.prevent="send"
              @input="autoResize"
            ></textarea>
            <button class="chat-send-btn" :disabled="loading || !inputText.trim()" @click="send">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" width="16" height="16"><path d="M12 19V5M5 12l7-7 7 7"/></svg>
            </button>
          </div>
          <p class="chat-hint">{{ t('chat.hint') }}</p>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ChatFolder, ChatMessage, ChatSession, ChatSessionDetail, ChatSource } from '~/types/api'

const { t } = useI18n()
const apiFetch = useApiFetch()
const config = useRuntimeConfig()
const session = useSupabaseSession()

// ── State ─────────────────────────────────────────────────────────────────────
const folders = ref<ChatFolder[]>([])
const sessions = ref<ChatSession[]>([])
const activeSessionId = ref<string | null>(null)
const activeSession = ref<ChatSessionDetail | null>(null)
const messages = ref<ChatMessage[]>([])
const sourcesMap = ref<Record<string, ChatSource[]>>({})
const inputText = ref('')
const loading = ref(false)
const streamingText = ref('')
const thinkingOpen = ref(true)

// 進行中的 agentic process 狀態
const process = ref<{
  thinking: string
  toolCall: { name: string; query: string } | null
  toolResult: { count: number; titles: string[] } | null
  sources: ChatSource[]
}>({ thinking: '', toolCall: null, toolResult: null, sources: [] })

const messagesEl = ref<HTMLElement | null>(null)
const inputEl = ref<HTMLTextAreaElement | null>(null)

const SOURCE_LABELS: Record<string, string> = { youtube: '▶ YouTube', article: 'Article', ig: 'IG' }

// ── Computed ──────────────────────────────────────────────────────────────────
const unfoldered = computed(() => sessions.value.filter(s => !s.folder_id))
const sessionsInFolder = (folderId: string) => sessions.value.filter(s => s.folder_id === folderId)

// ── Init ──────────────────────────────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([loadFolders(), loadSessions()])
})

async function loadFolders() {
  try { folders.value = await apiFetch<ChatFolder[]>('/chat/folders') } catch {}
}

async function loadSessions() {
  try { sessions.value = await apiFetch<ChatSession[]>('/chat/sessions') } catch {}
}

// ── Session actions ───────────────────────────────────────────────────────────
async function newSession() {
  try {
    const s = await apiFetch<ChatSession>('/chat/sessions', { method: 'POST', body: {} })
    sessions.value.unshift(s)
    await openSession(s.id)
  } catch {}
}

async function openSession(id: string) {
  try {
    const detail = await apiFetch<ChatSessionDetail>(`/chat/sessions/${id}`)
    activeSessionId.value = id
    activeSession.value = detail
    messages.value = detail.messages
    sourcesMap.value = {}
    resetProcess()

    const assistantMsgs = detail.messages.filter(m => m.role === 'assistant' && m.cited_item_ids?.length)
    const allIds = [...new Set(assistantMsgs.flatMap(m => m.cited_item_ids!))]
    if (allIds.length) {
      const itemResults = await Promise.allSettled(
        allIds.map(itemId => apiFetch<ChatSource>(`/items/${itemId}`))
      )
      const itemMap: Record<string, ChatSource> = {}
      itemResults.forEach((r, i) => {
        if (r.status === 'fulfilled') itemMap[allIds[i]] = r.value
      })
      for (const msg of assistantMsgs) {
        const sources = (msg.cited_item_ids ?? []).map(iid => itemMap[iid]).filter(Boolean)
        if (sources.length) sourcesMap.value[msg.id] = sources
      }
    }

    await nextTick()
    scrollBottom()
  } catch {}
}

async function renameSession(id: string, name: string) {
  try {
    await apiFetch(`/chat/sessions/${id}`, { method: 'PATCH', body: { title: name } })
    const idx = sessions.value.findIndex(s => s.id === id)
    if (idx !== -1) sessions.value[idx].title = name
    if (activeSession.value?.id === id) activeSession.value.title = name
  } catch {}
}

async function deleteSession(id: string) {
  try {
    await apiFetch(`/chat/sessions/${id}`, { method: 'DELETE' })
    sessions.value = sessions.value.filter(s => s.id !== id)
    if (activeSessionId.value === id) {
      activeSessionId.value = null
      activeSession.value = null
      messages.value = []
    }
  } catch {}
}

// ── Send message ──────────────────────────────────────────────────────────────
function resetProcess() {
  process.value = { thinking: '', toolCall: null, toolResult: null, sources: [] }
  streamingText.value = ''
  thinkingOpen.value = true
}

async function send() {
  if (!inputText.value.trim() || loading.value || !activeSessionId.value) return

  const content = inputText.value.trim()
  inputText.value = ''
  resetInputHeight()
  loading.value = true
  resetProcess()

  const userMsg: ChatMessage = {
    id: crypto.randomUUID(),
    role: 'user',
    content,
    cited_item_ids: null,
    created_at: new Date().toISOString(),
  }
  messages.value.push(userMsg)
  await nextTick()
  scrollBottom()

  const apiBase = config.public.apiBase as string
  const token = session.value?.access_token
  const isFirstMessage = messages.value.filter(m => m.role === 'user').length === 1

  try {
    const resp = await fetch(`${apiBase}/chat/sessions/${activeSessionId.value}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ content }),
    })
    if (!resp.ok) throw new Error('request failed')

    const reader = resp.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let pendingSources: ChatSource[] = []
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
          process.value.thinking = data.text
          await nextTick(); scrollBottom()

        } else if (event === 'tool_call') {
          process.value.toolCall = { name: data.name, query: data.query }
          await nextTick(); scrollBottom()

        } else if (event === 'tool_result') {
          process.value.toolResult = { count: data.count, titles: data.titles }
          await nextTick(); scrollBottom()

        } else if (event === 'sources') {
          pendingSources = data as ChatSource[]
          process.value.sources = pendingSources

        } else if (event === 'delta') {
          streamingText.value += data.text
          await nextTick(); scrollBottom()

        } else if (event === 'done') {
          const assistantMsg: ChatMessage = {
            id: assistantId,
            role: 'assistant',
            content: streamingText.value,
            cited_item_ids: pendingSources.map(s => s.id),
            created_at: new Date().toISOString(),
          }
          messages.value.push(assistantMsg)
          if (pendingSources.length) sourcesMap.value[assistantId] = pendingSources

          if (isFirstMessage && !activeSession.value?.title) {
            const title = content.slice(0, 40) + (content.length > 40 ? '…' : '')
            if (activeSession.value) activeSession.value.title = title
            const idx = sessions.value.findIndex(s => s.id === activeSessionId.value)
            if (idx !== -1) sessions.value[idx].title = title
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
      content: t('chat.error'),
      cited_item_ids: null,
      created_at: new Date().toISOString(),
    })
  } finally {
    loading.value = false
  }
}

// ── UI helpers ────────────────────────────────────────────────────────────────
function scrollBottom() {
  if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
}

function autoResize() {
  if (!inputEl.value) return
  inputEl.value.style.height = 'auto'
  inputEl.value.style.height = Math.min(inputEl.value.scrollHeight, 160) + 'px'
}

function resetInputHeight() {
  if (inputEl.value) inputEl.value.style.height = ''
}

function sourceLabel(type: string | null) {
  return type ? (SOURCE_LABELS[type] ?? type) : 'Article'
}
</script>

<style>
.chat-page {
  display: grid;
  grid-template-columns: 260px 1fr;
  height: calc(100vh - var(--nav-h, 56px));
  overflow: hidden;
}

/* ── 左側 ── */
.chat-list { display: flex; flex-direction: column; border-right: 1px solid var(--border); background: var(--bg); overflow: hidden; }
.chat-list__head { display: flex; align-items: center; padding: 18px 16px 14px; border-bottom: 1px solid var(--border); flex-shrink: 0; }
.chat-list__title { flex: 1; font-family: var(--font-mono); font-size: 11px; font-weight: 500; color: var(--text-dim); letter-spacing: 0.08em; }
.chat-icon-btn { width: 28px; height: 28px; border-radius: 7px; border: 1px solid var(--border); background: transparent; color: var(--text-mid); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all .15s ease; }
.chat-icon-btn:hover { background: var(--surface2); color: var(--text); }
.chat-list__body { flex: 1; overflow-y: auto; padding: 8px 0; }
.chat-list__empty { padding: 40px 16px; text-align: center; font-size: 12.5px; color: var(--text-dim); line-height: 1.8; white-space: pre-line; }
.session-group { padding: 0 8px; }
.folder-block { padding: 12px 8px 0; }
.folder-block__label { display: flex; align-items: center; gap: 6px; font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); padding: 4px 8px 6px; }

/* ── 右側 ── */
.chat-view { display: flex; flex-direction: column; overflow: hidden; background: var(--bg); }

.chat-welcome { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 14px; padding: 40px; text-align: center; }
.chat-welcome__icon { color: var(--text-dim); margin-bottom: 4px; }
.chat-welcome__title { font-family: var(--font-brand); font-size: 22px; font-weight: 600; margin: 0; }
.chat-welcome__desc { font-size: 14px; color: var(--text-mid); line-height: 1.7; max-width: 380px; margin: 0; }

.chat-view__head { padding: 16px 28px; border-bottom: 1px solid var(--border); flex-shrink: 0; }
.chat-view__title { font-size: 14px; font-weight: 500; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; }

.chat-view__messages { flex: 1; overflow-y: auto; padding: 24px 28px; display: flex; flex-direction: column; gap: 20px; }

/* 訊息 */
.msg { display: flex; flex-direction: column; gap: 8px; }
.msg--user { align-items: flex-end; }
.msg--assistant { align-items: flex-start; }
.msg__bubble { max-width: 68%; padding: 11px 16px; border-radius: 14px; font-size: 14px; line-height: 1.7; white-space: pre-wrap; }
.msg--user .msg__bubble { background: var(--accent-dim); color: var(--accent); border: 1px solid var(--accent-bdr); border-bottom-right-radius: 4px; }
.msg--assistant .msg__bubble { background: var(--surface); border: 1px solid var(--border); color: var(--text); border-bottom-left-radius: 4px; }
.msg__bubble--streaming { background: var(--surface); border: 1px solid var(--border); color: var(--text); border-bottom-left-radius: 4px; max-width: 68%; padding: 11px 16px; border-radius: 14px; font-size: 14px; line-height: 1.7; white-space: pre-wrap; }
.cursor { display: inline-block; animation: blink 1s infinite; color: var(--accent); margin-left: 2px; }
@keyframes blink { 50% { opacity: 0; } }

/* Agentic process blocks */
.process-block {
  max-width: 68%;
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  font-size: 12.5px;
}
.process-block__toggle {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 8px 12px;
  background: var(--surface);
  border: none;
  cursor: pointer;
  text-align: left;
  color: var(--text-mid);
  transition: background .1s;
}
.process-block__toggle:hover { background: var(--surface2); }
.process-block__icon { font-size: 13px; }
.process-block__label { flex: 1; font-family: var(--font-mono); font-size: 11px; }
.process-block__chevron { transition: transform .2s ease; flex-shrink: 0; color: var(--text-dim); }
.process-block__chevron--open { transform: rotate(180deg); }
.process-block__body {
  padding: 10px 12px;
  background: var(--bg);
  border-top: 1px solid var(--border);
  color: var(--text-mid);
  font-size: 12.5px;
  line-height: 1.65;
  font-style: italic;
}

.process-step {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 8px;
  font-family: var(--font-mono);
  font-size: 11.5px;
  max-width: 68%;
}
.process-step--tool { background: color-mix(in oklab, var(--tag-b) 10%, transparent); border: 1px solid color-mix(in oklab, var(--tag-b) 25%, transparent); color: var(--tag-b); }
.process-step--result { background: color-mix(in oklab, var(--accent) 8%, transparent); border: 1px solid var(--accent-bdr); color: var(--accent); }
.process-step__icon { font-size: 13px; }
.process-step__label { font-weight: 500; }
.process-step__query { background: color-mix(in oklab, var(--tag-b) 18%, transparent); padding: 1px 7px; border-radius: 5px; font-size: 11px; }
.process-step__titles { color: var(--text-dim); font-size: 10.5px; }

/* Source cards */
.msg__sources { display: flex; flex-direction: column; gap: 6px; max-width: 68%; }
.src-card { display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: var(--surface2); border: 1px solid var(--border); border-radius: 10px; transition: all .15s ease; }
.src-card:hover { border-color: var(--accent-bdr); }
.src-card__thumb { width: 48px; height: 34px; border-radius: 6px; object-fit: cover; flex-shrink: 0; }
.src-card__thumb--empty { background: var(--surface2); border: 1px solid var(--border); }
.src-card__body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.src-card__title { font-size: 12.5px; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.src-card__type { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); }

/* Thinking dots */
.msg-thinking { display: flex; gap: 5px; padding: 4px 0; }
.msg-thinking span { width: 7px; height: 7px; background: var(--accent); border-radius: 50%; animation: thinking-dot 1.2s infinite; }
.msg-thinking span:nth-child(2) { animation-delay: .2s; }
.msg-thinking span:nth-child(3) { animation-delay: .4s; }
@keyframes thinking-dot { 0%, 100% { opacity: .3; transform: scale(1); } 50% { opacity: 1; transform: scale(1.3); } }

/* Input */
.chat-view__input-wrap { padding: 16px 28px 20px; border-top: 1px solid var(--border); flex-shrink: 0; }
.chat-input-box { display: flex; align-items: flex-end; gap: 10px; background: var(--surface); border: 1px solid var(--border2); border-radius: 14px; padding: 10px 10px 10px 16px; transition: border-color .15s; }
.chat-input-box:focus-within { border-color: var(--accent-bdr); }
.chat-input { flex: 1; background: transparent; border: none; outline: none; font-family: var(--font-ui); font-size: 14px; color: var(--text); resize: none; line-height: 1.6; max-height: 160px; overflow-y: auto; }
.chat-input::placeholder { color: var(--text-dim); }
.chat-send-btn { width: 36px; height: 36px; border-radius: 9px; background: var(--accent); color: var(--accent-fg); border: none; cursor: pointer; flex-shrink: 0; display: flex; align-items: center; justify-content: center; transition: opacity .15s; }
.chat-send-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.chat-hint { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); margin: 8px 0 0; text-align: center; }

@media (max-width: 768px) {
  .chat-page { grid-template-columns: 1fr; }
  .chat-list { display: none; }
  .msg__bubble, .msg__sources, .process-block, .process-step, .msg__bubble--streaming { max-width: 92%; }
}
</style>
