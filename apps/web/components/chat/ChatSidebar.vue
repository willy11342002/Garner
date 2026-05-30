<template>
  <aside class="chat-sidebar">
    <!-- 頂部 header -->
    <div class="chat-header">
      <span class="chat-header__title">AI Chat</span>
      <button class="chat-new-btn" title="新對話" @click="newSession">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
          <path d="M12 5v14M5 12h14"/>
        </svg>
      </button>
    </div>

    <!-- session 列表 -->
    <div v-if="!activeSession" class="chat-sessions">
      <!-- 無分類 sessions -->
      <div v-if="unfoldered.length" class="session-group">
        <div
          v-for="s in unfoldered"
          :key="s.id"
          class="session-item"
          :class="{ 'session-item--active': activeSession?.id === s.id }"
          @click="openSession(s.id)"
        >
          <span class="session-item__title">{{ s.title || '新對話' }}</span>
          <button class="session-item__del" @click.stop="deleteSession(s.id)">×</button>
        </div>
      </div>

      <!-- 資料夾 -->
      <div v-for="folder in folders" :key="folder.id" class="folder-group">
        <div class="folder-label">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>
          {{ folder.name }}
        </div>
        <div
          v-for="s in sessionsInFolder(folder.id)"
          :key="s.id"
          class="session-item session-item--indent"
          :class="{ 'session-item--active': activeSession?.id === s.id }"
          @click="openSession(s.id)"
        >
          <span class="session-item__title">{{ s.title || '新對話' }}</span>
          <button class="session-item__del" @click.stop="deleteSession(s.id)">×</button>
        </div>
      </div>

      <div v-if="!sessions.length" class="chat-empty">
        <p>還沒有對話。<br>點右上角 + 開始詢問你的知識庫。</p>
      </div>
    </div>

    <!-- 對話介面 -->
    <template v-else>
      <div class="chat-back-bar">
        <button class="chat-back" @click="closeSession">← 返回</button>
        <span class="chat-session-title">{{ activeSession.title || '新對話' }}</span>
      </div>

      <!-- 訊息串 -->
      <div ref="messagesEl" class="chat-messages">
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="chat-msg"
          :class="`chat-msg--${msg.role}`"
        >
          <div class="chat-msg__bubble">{{ msg.content }}</div>
          <!-- source cards -->
          <div v-if="msg.role === 'assistant' && sourcesMap[msg.id]?.length" class="chat-sources">
            <NuxtLink
              v-for="src in sourcesMap[msg.id]"
              :key="src.id"
              class="chat-src"
              :to="`/app/item/${src.id}`"
            >
              <img v-if="src.thumbnail_url" :src="src.thumbnail_url" :alt="src.title || ''" class="chat-src__thumb">
              <div v-else class="chat-src__thumb chat-src__thumb--empty"></div>
              <span class="chat-src__title">{{ src.title || src.url }}</span>
            </NuxtLink>
          </div>
        </div>

        <!-- 串流中的訊息 -->
        <div v-if="streamingText" class="chat-msg chat-msg--assistant">
          <div class="chat-msg__bubble chat-msg__bubble--streaming">{{ streamingText }}<span class="cursor">▍</span></div>
        </div>

        <!-- loading -->
        <div v-if="loading && !streamingText" class="chat-thinking">
          <span></span><span></span><span></span>
        </div>
      </div>

      <!-- 輸入框 -->
      <div class="chat-input-area">
        <textarea
          ref="inputEl"
          v-model="inputText"
          class="chat-input"
          placeholder="問你的知識庫..."
          rows="1"
          @keydown.enter.exact.prevent="send"
          @input="autoResize"
        ></textarea>
        <button class="chat-send" :disabled="loading || !inputText.trim()" @click="send">↑</button>
      </div>
    </template>
  </aside>
</template>

<script setup lang="ts">
import type { ChatFolder, ChatMessage, ChatSession, ChatSessionDetail, ChatSource } from '~/types/api'

const apiFetch = useApiFetch()
const { $config } = useNuxtApp()

// ── State ─────────────────────────────────────────────────────────────────────
const folders = ref<ChatFolder[]>([])
const sessions = ref<ChatSession[]>([])
const activeSession = ref<ChatSessionDetail | null>(null)
const messages = ref<ChatMessage[]>([])
const sourcesMap = ref<Record<string, ChatSource[]>>({})
const inputText = ref('')
const loading = ref(false)
const streamingText = ref('')

const messagesEl = ref<HTMLElement | null>(null)
const inputEl = ref<HTMLTextAreaElement | null>(null)

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
    activeSession.value = detail
    messages.value = detail.messages
    sourcesMap.value = {}
    await nextTick()
    scrollBottom()
  } catch {}
}

function closeSession() {
  activeSession.value = null
  streamingText.value = ''
  loadSessions()
}

async function deleteSession(id: string) {
  try {
    await apiFetch(`/chat/sessions/${id}`, { method: 'DELETE' })
    sessions.value = sessions.value.filter(s => s.id !== id)
    if (activeSession.value?.id === id) closeSession()
  } catch {}
}

// ── Send message ──────────────────────────────────────────────────────────────
async function send() {
  if (!inputText.value.trim() || loading.value || !activeSession.value) return

  const content = inputText.value.trim()
  inputText.value = ''
  resetInputHeight()
  loading.value = true
  streamingText.value = ''

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

  const apiBase = ($config.public as Record<string, string>).apiBase ?? ''
  const token = useCookie('access_token').value ?? ''

  try {
    const resp = await fetch(`${apiBase}/chat/sessions/${activeSession.value.id}/messages`, {
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

        if (event === 'sources') {
          pendingSources = data as ChatSource[]
        } else if (event === 'delta') {
          loading.value = false
          streamingText.value += data.text
          await nextTick()
          scrollBottom()
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
          streamingText.value = ''

          // 更新 session title（如果是第一則訊息）
          if (!activeSession.value!.title) {
            activeSession.value!.title = content.slice(0, 40) + (content.length > 40 ? '…' : '')
            const idx = sessions.value.findIndex(s => s.id === activeSession.value!.id)
            if (idx !== -1) sessions.value[idx].title = activeSession.value!.title
          }

          await nextTick()
          scrollBottom()
        }
      }
    }
  } catch {
    streamingText.value = ''
    messages.value.push({
      id: crypto.randomUUID(),
      role: 'assistant',
      content: 'AI 服務暫時無法使用，請稍後再試。',
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
  inputEl.value.style.height = Math.min(inputEl.value.scrollHeight, 120) + 'px'
}

function resetInputHeight() {
  if (inputEl.value) inputEl.value.style.height = ''
}
</script>

<style scoped>
.chat-sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg);
  overflow: hidden;
}

.chat-header {
  display: flex;
  align-items: center;
  padding: 20px 16px 14px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.chat-header__title {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 500;
  color: var(--text-dim);
  letter-spacing: 0.08em;
  flex: 1;
}
.chat-new-btn {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text-mid);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all .15s ease;
}
.chat-new-btn:hover { background: var(--surface2); color: var(--text); }

/* Session list */
.chat-sessions { flex: 1; overflow-y: auto; padding: 8px 0; }
.session-group { padding: 0 8px; }
.folder-group { padding: 0 8px; margin-top: 12px; }
.folder-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--text-dim);
  padding: 4px 8px;
}
.session-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background .1s ease;
}
.session-item:hover { background: var(--surface2); }
.session-item--active { background: var(--accent-dim); }
.session-item--indent { padding-left: 22px; }
.session-item__title {
  flex: 1;
  font-size: 12.5px;
  color: var(--text-mid);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.session-item--active .session-item__title { color: var(--accent); }
.session-item__del {
  opacity: 0;
  font-size: 14px;
  color: var(--text-dim);
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0 2px;
  line-height: 1;
  transition: opacity .1s;
}
.session-item:hover .session-item__del { opacity: 1; }
.session-item__del:hover { color: var(--tag-e); }

.chat-empty {
  padding: 40px 20px;
  text-align: center;
  color: var(--text-dim);
  font-size: 12.5px;
  line-height: 1.7;
}

/* Back bar */
.chat-back-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.chat-back {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-dim);
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0;
  white-space: nowrap;
}
.chat-back:hover { color: var(--text); }
.chat-session-title {
  font-size: 12px;
  color: var(--text-mid);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Messages */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 14px 14px 8px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.chat-msg { display: flex; flex-direction: column; gap: 6px; }
.chat-msg--user { align-items: flex-end; }
.chat-msg--assistant { align-items: flex-start; }
.chat-msg__bubble {
  max-width: 85%;
  padding: 9px 13px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.65;
  white-space: pre-wrap;
}
.chat-msg--user .chat-msg__bubble {
  background: var(--accent);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.chat-msg--assistant .chat-msg__bubble {
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text);
  border-bottom-left-radius: 4px;
}
.chat-msg__bubble--streaming { position: relative; }
.cursor {
  display: inline-block;
  animation: blink 1s infinite;
  color: var(--accent);
  margin-left: 2px;
}
@keyframes blink { 50% { opacity: 0; } }

/* Source cards */
.chat-sources {
  display: flex;
  flex-direction: column;
  gap: 5px;
  max-width: 85%;
}
.chat-src {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 9px;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 8px;
  transition: all .15s ease;
}
.chat-src:hover { border-color: var(--accent-bdr); }
.chat-src__thumb {
  width: 36px;
  height: 26px;
  border-radius: 4px;
  object-fit: cover;
  flex-shrink: 0;
  background: var(--surface);
}
.chat-src__thumb--empty { background: var(--surface2); }
.chat-src__title {
  font-size: 11.5px;
  color: var(--text-mid);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Thinking dots */
.chat-thinking {
  display: flex;
  gap: 5px;
  padding: 10px 14px;
}
.chat-thinking span {
  width: 7px;
  height: 7px;
  background: var(--accent);
  border-radius: 50%;
  animation: thinking 1.2s infinite;
}
.chat-thinking span:nth-child(2) { animation-delay: .2s; }
.chat-thinking span:nth-child(3) { animation-delay: .4s; }
@keyframes thinking { 0%, 100% { opacity: .3; transform: scale(1); } 50% { opacity: 1; transform: scale(1.3); } }

/* Input */
.chat-input-area {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}
.chat-input {
  flex: 1;
  background: var(--surface);
  border: 1px solid var(--border2);
  border-radius: 10px;
  padding: 9px 13px;
  font-family: var(--font-ui);
  font-size: 13px;
  color: var(--text);
  resize: none;
  outline: none;
  line-height: 1.5;
  transition: border-color .15s;
  overflow-y: hidden;
}
.chat-input:focus { border-color: var(--accent-bdr); }
.chat-input::placeholder { color: var(--text-dim); }
.chat-send {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: var(--accent);
  color: #fff;
  border: none;
  font-size: 16px;
  cursor: pointer;
  flex-shrink: 0;
  transition: opacity .15s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.chat-send:disabled { opacity: 0.4; cursor: not-allowed; }

@media (max-width: 1100px) {
  .chat-sidebar {
    height: 500px;
    border-top: 1px solid var(--border);
  }
}
</style>
