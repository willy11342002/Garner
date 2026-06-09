<template>
  <div class="chat-page">
    <!-- 左側：session 列表 -->
    <aside class="chat-list" :class="{ 'chat-list--hidden-mobile': mobileView === 'chat' }">
      <div class="chat-list__head">
        <span v-if="quota?.chat" class="chat-list__quota" :class="{ 'chat-list__quota--warn': chatQuotaFull }">
          {{ chatQuotaRemaining }}<template v-if="quota.chat.limit !== null"> / {{ quota.chat.limit }}</template>
        </span>
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
      <!-- 手機版：右邊緣切換箭頭 -->
      <button class="panel-toggle panel-toggle--right" @click="mobileView = 'chat'">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="14" height="14"><path d="M15 18l-6-6 6-6"/></svg>
      </button>
    </aside>

    <!-- 右側：對話區 -->
    <div class="chat-view" :class="{ 'chat-view--hidden-mobile': mobileView === 'list' }">
      <!-- 手機版：左邊緣切換箭頭 -->
      <button class="panel-toggle panel-toggle--left" @click="mobileView = 'list'">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="14" height="14"><path d="M9 18l6-6-6-6"/></svg>
      </button>
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
          <button class="chat-back-btn" @click="mobileView = 'list'">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M15 18l-6-6 6-6"/></svg>
          </button>
          <span class="chat-view__title">{{ activeSession?.title || t('chat.untitled') }}</span>
        </div>

        <div ref="messagesEl" class="chat-view__messages">
          <!-- 歷史訊息 -->
          <template v-for="msg in messages" :key="msg.id">
            <div class="msg" :class="`msg--${msg.role}`">
              <!-- user 訊息：已選知識節點（可收合） -->
              <template v-if="msg.role === 'user' && userContextMap[msg.id]?.length">
                <div class="context-block">
                  <button class="context-block__toggle" @click="toggleContext(msg.id)">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
                    <span class="context-block__label">{{ userContextMap[msg.id].length }} 個知識節點</span>
                    <svg class="process-block__chevron" :class="{ 'process-block__chevron--open': openContexts.has(msg.id) }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M6 9l6 6 6-6"/></svg>
                  </button>
                  <Transition name="thinking">
                    <div v-if="openContexts.has(msg.id)" class="context-block__body">
                      <NuxtLink
                        v-for="item in userContextMap[msg.id]"
                        :key="item.id"
                        class="src-card"
                        :to="`/app/item/${item.id}`"
                      >
                        <img v-if="item.thumbnail_url" :src="item.thumbnail_url" :alt="item.title || ''" class="src-card__thumb">
                        <div v-else class="src-card__thumb src-card__thumb--empty"></div>
                        <div class="src-card__body">
                          <span class="src-card__title">{{ item.title || item.url }}</span>
                          <span class="src-card__type">{{ sourceLabel(item.source_type) }}</span>
                        </div>
                      </NuxtLink>
                    </div>
                  </Transition>
                </div>
              </template>

              <!-- assistant 訊息：顯示永久保存的 process log -->
              <template v-if="msg.role === 'assistant' && processMap[msg.id]">
                <div class="process-block">
                  <button class="process-block__toggle" @click="toggleThinking(msg.id)">
                    <span class="process-block__icon">💭</span>
                    <span class="process-block__label">{{ t('chat.thinking') }}</span>
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
                        <template v-if="step.toolCall.name === 'structured_filter'">
                          <span v-if="step.toolCall.tags?.length" class="process-body__param">tags: {{ step.toolCall.tags.join(', ') }}</span>
                          <span v-if="step.toolCall.source_type" class="process-body__param">source: {{ step.toolCall.source_type }}</span>
                          <span v-if="step.toolCall.start_date || step.toolCall.end_date" class="process-body__param">date: {{ step.toolCall.start_date ?? '…' }} ～ {{ step.toolCall.end_date ?? '…' }}</span>
                        </template>
                      </div>
                      <div v-if="step.toolResult" class="process-body__tool-result">
                        <span class="process-body__step-icon">✓</span>
                        <template v-if="step.toolCall.name === 'create_article'">
                          <span>文章已建立：{{ step.toolResult.title }}</span>
                        </template>
                        <template v-else>
                          <span>找到 {{ step.toolResult.count }} 筆</span>
                          <span v-if="step.toolResult.titles?.length" class="process-body__result-titles">{{ step.toolResult.titles.join('、') }}</span>
                        </template>
                      </div>
                    </div>
                  </div>
                  </Transition>
                </div>
              </template>

              <div
                class="msg__bubble"
                :class="{ 'msg__bubble--has-sources': msg.role === 'assistant' && sourcesMap[msg.id]?.length }"
              >
                {{ msg.content }}
                <button
                  v-if="msg.role === 'assistant' && sourcesMap[msg.id]?.length"
                  class="src-badge"
                  :class="{ 'src-badge--open': openSources.has(msg.id) }"
                  @click.stop="toggleSources(msg.id)"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M6 9l6 6 6-6"/></svg>
                </button>
              </div>
              <Transition name="sources">
                <div v-if="msg.role === 'assistant' && openSources.has(msg.id) && sourcesMap[msg.id]?.length" class="sources-list">
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
              </Transition>
              <!-- 文章草稿卡片 -->
              <ChatArticleCard
                v-if="msg.role === 'assistant' && draftMap[msg.id]"
                :draft="draftMap[msg.id]"
                @preview="(id) => previewItemId = id"
              />
            </div>
          </template>

          <!-- 進行中的 agentic process -->
          <div v-if="loading || streamingText" class="msg msg--assistant">
            <div v-if="liveProcess.thinking || liveProcess.steps.length" class="process-block">
              <button class="process-block__toggle" @click="toggleThinking('live')">
                <span class="process-block__icon">💭</span>
                <span class="process-block__label">{{ t('chat.thinking') }}</span>
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
                    <template v-if="step.toolCall.name === 'structured_filter'">
                      <span v-if="step.toolCall.tags?.length" class="process-body__param">tags: {{ step.toolCall.tags.join(', ') }}</span>
                      <span v-if="step.toolCall.source_type" class="process-body__param">source: {{ step.toolCall.source_type }}</span>
                      <span v-if="step.toolCall.start_date || step.toolCall.end_date" class="process-body__param">date: {{ step.toolCall.start_date ?? '…' }} ～ {{ step.toolCall.end_date ?? '…' }}</span>
                    </template>
                  </div>
                  <div v-if="step.toolResult" class="process-body__tool-result">
                    <span class="process-body__step-icon">✓</span>
                    <template v-if="step.toolCall.name === 'create_article'">
                      <span>文章已建立：{{ step.toolResult.title }}</span>
                    </template>
                    <template v-else>
                      <span>找到 {{ step.toolResult.count }} 筆</span>
                      <span v-if="step.toolResult.titles?.length" class="process-body__result-titles">{{ step.toolResult.titles.join('、') }}</span>
                    </template>
                  </div>
                  <div v-else class="process-body__tool-result process-body__tool-result--pending">
                    <span class="process-body__step-icon">⋯</span>
                    <span>{{ step.toolCall.name === 'create_article' ? '生成中' : '搜尋中' }}</span>
                  </div>
                </div>
              </div>
              </Transition>
            </div>

            <div v-if="loading && !streamingText" class="msg-thinking">
              <span></span><span></span><span></span>
            </div>

            <div
              v-if="streamingText"
              class="msg__bubble msg__bubble--streaming"
              :class="{ 'msg__bubble--has-sources': liveProcess.sources.length }"
            >
              {{ streamingText }}<span class="cursor">▍</span>
              <button
                v-if="liveProcess.sources.length"
                class="src-badge"
                :class="{ 'src-badge--open': openSources.has('live') }"
                @click.stop="toggleSources('live')"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M6 9l6 6 6-6"/></svg>
              </button>
            </div>
            <Transition name="sources">
              <div v-if="openSources.has('live') && liveProcess.sources.length" class="sources-list">
                <NuxtLink
                  v-for="src in liveProcess.sources"
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
            </Transition>
            <ChatArticleCard
              v-if="liveDraft"
              :draft="liveDraft"
              @preview="(id) => previewItemId = id"
            />
          </div>
        </div>

        <div class="chat-view__input-wrap">
          <div class="chat-input-box" :class="{ 'chat-input-box--disabled': chatQuotaFull }">
            <textarea
              ref="inputEl"
              v-model="inputText"
              class="chat-input"
              :placeholder="chatQuotaFull ? t('chat.quota_full') : t('chat.placeholder')"
              :disabled="chatQuotaFull"
              rows="1"
              @keydown.enter.exact.prevent="send"
              @input="autoResize"
            ></textarea>
            <button class="chat-send-btn" :disabled="loading || !inputText.trim() || chatQuotaFull" @click="send">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" width="16" height="16"><path d="M12 19V5M5 12l7-7 7 7"/></svg>
            </button>
          </div>
          <p class="chat-hint">{{ t('chat.hint') }}</p>
        </div>
      </template>
    </div>
  </div>

  <!-- 文章草稿預覽 Modal -->
  <ItemDetailModal :item-id="previewItemId" @close="previewItemId = null" />
</template>

<script setup lang="ts">
import type { ArticleDraft, ChatFolder, ChatMessage, ChatSession, ChatSessionDetail, ChatSource, UsageSummary } from '~/types/api'
useHead({ title: 'Garner — AI Chat' })

const { t } = useI18n()
const apiFetch = useApiFetch()
const router = useRouter()
const route = useRoute()
const config = useRuntimeConfig()
const session = useSupabaseSession()

// ── State ─────────────────────────────────────────────────────────────────────
const folders = ref<ChatFolder[]>([])
const sessions = ref<ChatSession[]>([])
const quota = ref<UsageSummary | null>(null)
const activeSessionId = ref<string | null>(null)
const activeSession = ref<ChatSessionDetail | null>(null)
const messages = ref<ChatMessage[]>([])
const sourcesMap = ref<Record<string, ChatSource[]>>({})
const inputText = ref('')
const loading = ref(false)
const streamingText = ref('')

const mobileView = ref<'list' | 'chat'>('list')

const openThinking = ref<Set<string>>(new Set(['live']))
const openContexts = ref<Set<string>>(new Set())
const openSources = ref<Set<string>>(new Set())

type ProcessStep = { toolCall: Record<string, any>; toolResult: { count: number; titles: string[] } | null }
type ProcessLog = { thinking: string; steps: ProcessStep[] }
const liveProcess = ref<ProcessLog & { sources: ChatSource[] }>({ thinking: '', steps: [], sources: [] })

const processMap = ref<Record<string, ProcessLog>>({})

const pendingItemIds = ref<string[]>([])

const userContextMap = ref<Record<string, ChatSource[]>>({})

const draftMap = ref<Record<string, ArticleDraft>>({})
const liveDraft = ref<ArticleDraft | null>(null)
const previewItemId = ref<string | null>(null)

const messagesEl = ref<HTMLElement | null>(null)
const inputEl = ref<HTMLTextAreaElement | null>(null)

const SOURCE_LABELS: Record<string, string> = { youtube: '▶ YouTube', article: 'Article', ig: 'IG' }

// ── Computed ──────────────────────────────────────────────────────────────────
const unfoldered = computed(() => sessions.value.filter(s => !s.folder_id))
const sessionsInFolder = (folderId: string) => sessions.value.filter(s => s.folder_id === folderId)
const chatQuotaFull = computed(() => {
  const q = quota.value?.chat
  return !!q && q.limit !== null && q.used >= q.limit
})
const chatQuotaRemaining = computed(() => {
  const q = quota.value?.chat
  if (!q || q.limit === null) return '∞'
  return Math.max(0, q.limit - q.used)
})

// ── Init ──────────────────────────────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([loadFolders(), loadSessions(), loadQuota()])
  const sid = route.query.session as string | undefined
  const prefill = route.query.prefill as string | undefined
  const itemsParam = route.query.items as string | undefined
  if (sid) {
    await openSession(sid)
    router.replace({ query: {} })  // 清掉 URL query
    if (prefill) {
      if (itemsParam) pendingItemIds.value = itemsParam.split(',').filter(Boolean)
      inputText.value = prefill
      await nextTick()
      send()
    }
  }
})

async function loadQuota() {
  try { quota.value = await apiFetch<UsageSummary>('/quota/me') } catch {}
}

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
    mobileView.value = 'chat'
  } catch {}
}

async function openSession(id: string) {
  if (activeSessionId.value === id) return
  try {
    const detail = await apiFetch<ChatSessionDetail>(`/chat/sessions/${id}`)
    activeSessionId.value = id
    activeSession.value = detail
    messages.value = detail.messages
    sourcesMap.value = {}
    processMap.value = {}
    const lastWithSources = [...detail.messages].reverse().find(m => m.role === 'assistant' && m.cited_item_ids?.length)
    openSources.value = lastWithSources ? new Set([lastWithSources.id]) : new Set()
    resetProcess()

    draftMap.value = {}
    for (const msg of detail.messages) {
      if (msg.role === 'assistant' && msg.process_log) {
        processMap.value[msg.id] = msg.process_log as ProcessLog
        openThinking.value.delete(msg.id)
        const draftStep = (msg.process_log.steps as any[])?.find((s: any) => s.articleDraft)
        if (draftStep?.articleDraft) draftMap.value[msg.id] = draftStep.articleDraft
      }
    }
    const lastAssistant = [...detail.messages].reverse().find(m => m.role === 'assistant' && m.process_log)
    if (lastAssistant) openThinking.value.add(lastAssistant.id)

    const assistantMsgs = detail.messages.filter(m => m.role === 'assistant' && m.cited_item_ids?.length)
    const userCtxMsgs = detail.messages.filter(m => m.role === 'user' && m.cited_item_ids?.length)
    const allIds = [...new Set([
      ...assistantMsgs.flatMap(m => m.cited_item_ids!),
      ...userCtxMsgs.flatMap(m => m.cited_item_ids!),
    ])]
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
      for (const msg of userCtxMsgs) {
        const items = (msg.cited_item_ids ?? []).map(iid => itemMap[iid]).filter(Boolean)
        if (items.length) userContextMap.value[msg.id] = items
      }
    }

    mobileView.value = 'chat'
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
  liveProcess.value = { thinking: '', steps: [], sources: [] }
  streamingText.value = ''
  liveDraft.value = null
  openThinking.value = new Set(['live'])
  openSources.value.delete('live')
}

function toggleThinking(id: string) {
  const s = openThinking.value
  if (s.has(id)) { s.delete(id) } else { s.add(id) }
  openThinking.value = new Set(s)
}

function toggleSources(id: string) {
  const s = openSources.value
  if (s.has(id)) { s.delete(id) } else { s.add(id) }
  openSources.value = new Set(s)
}

function toggleContext(id: string) {
  const s = openContexts.value
  if (s.has(id)) { s.delete(id) } else { s.add(id) }
  openContexts.value = new Set(s)
}

async function send() {
  if (!inputText.value.trim() || loading.value || !activeSessionId.value || chatQuotaFull.value) return

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
    const itemIds = pendingItemIds.value.slice()
    pendingItemIds.value = []

    if (itemIds.length) {
      userMsg.cited_item_ids = itemIds
      const msgId = userMsg.id
      Promise.allSettled(
        itemIds.map(id => apiFetch<ChatSource>(`/items/${id}`))
      ).then(results => {
        const items = results
          .filter((r): r is PromiseFulfilledResult<ChatSource> => r.status === 'fulfilled')
          .map(r => r.value)
        if (items.length) {
          userContextMap.value[msgId] = items
          openContexts.value = new Set([...openContexts.value, msgId])
        }
      })
    }

    const resp = await fetch(`${apiBase}/chat/sessions/${activeSessionId.value}/messages`, {
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
          liveProcess.value.thinking = data.text
          await nextTick(); scrollBottom()

        } else if (event === 'tool_call') {
          liveProcess.value.steps.push({ toolCall: data, toolResult: null })
          await nextTick(); scrollBottom()

        } else if (event === 'tool_result') {
          const steps = liveProcess.value.steps
          if (steps.length) steps[steps.length - 1].toolResult = { count: data.count, titles: data.titles }
          await nextTick(); scrollBottom()

        } else if (event === 'article_draft') {
          liveDraft.value = data as ArticleDraft
          await nextTick(); scrollBottom()

        } else if (event === 'sources') {
          pendingSources = data as ChatSource[]
          liveProcess.value.sources = pendingSources

        } else if (event === 'delta') {
          streamingText.value += data.text
          await nextTick(); scrollBottom()

        } else if (event === 'done') {
          processMap.value[assistantId] = {
            thinking: liveProcess.value.thinking,
            steps: liveProcess.value.steps,
          }
          if (liveDraft.value) {
            draftMap.value[assistantId] = liveDraft.value
            liveDraft.value = null
          }
          openThinking.value.delete('live')
          openThinking.value.add(assistantId)

          const assistantMsg: ChatMessage = {
            id: assistantId,
            role: 'assistant',
            content: streamingText.value,
            cited_item_ids: pendingSources.map(s => s.id),
            created_at: new Date().toISOString(),
          }
          messages.value.push(assistantMsg)
          if (pendingSources.length) {
            sourcesMap.value[assistantId] = pendingSources
            openSources.value = new Set([...openSources.value, assistantId])
          }

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
  if (messagesEl.value) messagesEl.value.scrollTo({ top: messagesEl.value.scrollHeight, behavior: 'smooth' })
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
