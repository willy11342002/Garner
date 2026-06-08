<template>
  <div class="chat-page">
    <!-- 左側：session 列表 -->
    <aside class="chat-list" :class="{ 'chat-list--hidden-mobile': mobileView === 'chat' }">
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
                        <span>找到 {{ step.toolResult.count }} 筆</span>
                        <span v-if="step.toolResult.titles?.length" class="process-body__result-titles">{{ step.toolResult.titles.join('、') }}</span>
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
            <!-- 思考過程 + tool steps（可收合，進行中） -->
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
                    <span>找到 {{ step.toolResult.count }} 筆</span>
                    <span v-if="step.toolResult.titles?.length" class="process-body__result-titles">{{ step.toolResult.titles.join('、') }}</span>
                  </div>
                  <div v-else class="process-body__tool-result process-body__tool-result--pending">
                    <span class="process-body__step-icon">⋯</span>
                    <span>搜尋中</span>
                  </div>
                </div>
              </div>
              </Transition>
            </div>

            <!-- 等待開始串流 -->
            <div v-if="loading && !streamingText" class="msg-thinking">
              <span></span><span></span><span></span>
            </div>

            <!-- 串流中的回覆 -->
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
            <!-- 進行中：文章草稿卡片 -->
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

// 手機版視圖切換
const mobileView = ref<'list' | 'chat'>('list')

// 哪些訊息的 thinking 是展開的（'live' = 進行中）
const openThinking = ref<Set<string>>(new Set(['live']))
// 哪些 user 訊息的知識節點是展開的
const openContexts = ref<Set<string>>(new Set())
// 哪些訊息的 sources 是展開的
const openSources = ref<Set<string>>(new Set())

// 進行中的 agentic process（每次 send 重置）
type ProcessStep = { toolCall: Record<string, any>; toolResult: { count: number; titles: string[] } | null }
type ProcessLog = { thinking: string; steps: ProcessStep[] }
const liveProcess = ref<ProcessLog & { sources: ChatSource[] }>({ thinking: '', steps: [], sources: [] })

// 每則 assistant 訊息永久保存的 process log
const processMap = ref<Record<string, ProcessLog>>({})

// 探索頁跳轉時帶入的知識節點 IDs（一次性，send() 後清空）
const pendingItemIds = ref<string[]>([])

// user message 的知識節點詳細資料（keyed by message id）
const userContextMap = ref<Record<string, ChatSource[]>>({})

// 文章草稿（keyed by assistantId）
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
  try {
    const detail = await apiFetch<ChatSessionDetail>(`/chat/sessions/${id}`)
    activeSessionId.value = id
    activeSession.value = detail
    messages.value = detail.messages
    sourcesMap.value = {}
    processMap.value = {}
    // 只展開最新一則有來源的 assistant 訊息
    const lastWithSources = [...detail.messages].reverse().find(m => m.role === 'assistant' && m.cited_item_ids?.length)
    openSources.value = lastWithSources ? new Set([lastWithSources.id]) : new Set()
    resetProcess()

    // 從訊息的 process_log 重建 processMap 和 draftMap
    draftMap.value = {}
    for (const msg of detail.messages) {
      if (msg.role === 'assistant' && msg.process_log) {
        processMap.value[msg.id] = msg.process_log as ProcessLog
        openThinking.value.delete(msg.id)
        // 還原文章草稿
        const draftStep = (msg.process_log.steps as any[])?.find((s: any) => s.articleDraft)
        if (draftStep?.articleDraft) draftMap.value[msg.id] = draftStep.articleDraft
      }
    }
    // 最新一則 assistant 訊息預設展開
    const lastAssistant = [...detail.messages].reverse().find(m => m.role === 'assistant' && m.process_log)
    if (lastAssistant) openThinking.value.add(lastAssistant.id)

    // 收集所有需要 fetch 的 item IDs（assistant citations + user context items）
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
    pendingItemIds.value = []  // 一次性，立即清空

    // 立即設定 userMsg 的 cited_item_ids，並非同步 fetch item 詳細資料
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
          // 把 process log 永久存到 processMap
          processMap.value[assistantId] = {
            thinking: liveProcess.value.thinking,
            steps: liveProcess.value.steps,
          }
          // 把文章草稿移至 draftMap
          if (liveDraft.value) {
            draftMap.value[assistantId] = liveDraft.value
            liveDraft.value = null
          }
          // thinking 預設收合（已完成），保留展開狀態
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
            openSources.value = new Set([...openSources.value, assistantId]) // 新回覆預設展開
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
.msg__bubble { padding: 11px 16px; border-radius: 14px; font-size: 14px; line-height: 1.7; white-space: pre-wrap; }
.msg--user .msg__bubble { background: var(--accent-dim); color: var(--accent); border: 1px solid var(--accent-bdr); }
.msg--assistant .msg__bubble { background: var(--surface); border: 1px solid var(--border); color: var(--text); }
.msg__bubble--streaming { position: relative; width: 480px; max-width: 480px; background: var(--surface); border: 1px solid var(--border); color: var(--text); padding: 11px 16px; border-radius: 14px; font-size: 14px; line-height: 1.7; white-space: pre-wrap; }
.cursor { display: inline-block; animation: blink 1s infinite; color: var(--accent); margin-left: 2px; }
@keyframes blink { 50% { opacity: 0; } }

/* Agentic process blocks */
.process-block {
  width: 480px;
  max-width: 480px;
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
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 推理文字 */
.process-body__reasoning {
  margin: 0;
  font-style: italic;
  color: var(--text-mid);
}

/* 每個 tool step 區塊 */
.process-body__step {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 6px 8px;
  border-radius: 7px;
  background: var(--surface);
  border: 1px solid var(--border);
}

/* tool call 那一行 */
.process-body__tool-call {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}
.process-body__step-icon { font-size: 12px; flex-shrink: 0; }
.process-body__tool-name {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  color: var(--tag-b);
  background: color-mix(in oklab, var(--tag-b) 10%, transparent);
  padding: 1px 6px;
  border-radius: 4px;
}
.process-body__param {
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--text-dim);
  background: var(--surface2);
  padding: 1px 6px;
  border-radius: 4px;
}

/* tool result 那一行 */
.process-body__tool-result {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 5px;
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--accent);
  padding-left: 2px;
}
.process-body__tool-result--pending { color: var(--text-dim); }
.process-body__result-titles {
  color: var(--text-dim);
  font-size: 10px;
}

/* User context block（知識節點摺疊框，右對齊） */
.context-block {
  width: 480px;
  max-width: 480px;
  border: 1px solid var(--accent-bdr);
  border-radius: 10px;
  overflow: hidden;
  font-size: 12.5px;
}
.context-block__toggle {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 8px 12px;
  background: var(--accent-dim);
  border: none;
  cursor: pointer;
  text-align: left;
  color: var(--accent);
  transition: background .1s;
}
.context-block__toggle:hover { background: color-mix(in oklab, var(--accent) 15%, transparent); }
.context-block__label { flex: 1; font-family: var(--font-mono); font-size: 11px; }
.context-block__body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px 10px;
  background: var(--bg);
  border-top: 1px solid var(--accent-bdr);
}

/* Bubble with sources gets extra bottom padding for badge */
.msg__bubble { position: relative; width: 480px; max-width: 480px; }
.msg__bubble--has-sources { padding-bottom: 26px; }

/* Source badge — inside bubble, bottom-right, matches process-block chevron style */
.src-badge {
  position: absolute;
  bottom: 8px;
  right: 10px;
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--text-dim);
  padding: 0;
  transition: color .15s ease;
}
.src-badge svg { transition: transform .2s ease; }
.src-badge:hover { color: var(--text-mid); }
.src-badge--open { color: var(--text-dim); }
.src-badge--open svg { transform: rotate(180deg); }

/* Expanded source list */
.sources-list { display: flex; flex-direction: column; gap: 6px; width: 480px; max-width: 480px; }

/* Sources transition */
.sources-enter-active { animation: sources-drop .2s ease; }
.sources-leave-active { animation: sources-drop .15s ease reverse; }
@keyframes sources-drop {
  from { opacity: 0; transform: translateY(-6px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* Thinking body transition */
.thinking-enter-active,
.thinking-leave-active {
  overflow: hidden;
  transition: max-height .25s ease, opacity .2s ease;
}
.thinking-enter-from,
.thinking-leave-to { max-height: 0; opacity: 0; }
.thinking-enter-to,
.thinking-leave-from { max-height: 600px; opacity: 1; }

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
.chat-input-box--disabled { opacity: 0.6; cursor: not-allowed; }
.chat-input { flex: 1; background: transparent; border: none; outline: none; font-family: var(--font-ui); font-size: 14px; color: var(--text); resize: none; line-height: 1.6; max-height: 160px; overflow-y: auto; }
.chat-input::placeholder { color: var(--text-dim); }
.chat-input:disabled { cursor: not-allowed; }
.chat-send-btn { width: 36px; height: 36px; border-radius: 9px; background: var(--accent); color: var(--accent-fg); border: none; cursor: pointer; flex-shrink: 0; display: flex; align-items: center; justify-content: center; transition: opacity .15s; }
.chat-send-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.chat-hint { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); margin: 8px 0 0; text-align: center; }

.chat-back-btn { display: none; }
.panel-toggle { display: none; }

@media (max-width: 768px) {
  .chat-page {
    display: block;
    position: relative;
    overflow: hidden;
  }

  .chat-list,
  .chat-view {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    transition: transform .3s cubic-bezier(.4, 0, .2, 1);
    will-change: transform;
  }

  /* list 面板：chat 模式時滑出左側 */
  .chat-list { transform: translateX(0); }
  .chat-list--hidden-mobile { transform: translateX(-100%); }

  /* chat 面板：list 模式時在右側等待 */
  .chat-view { transform: translateX(100%); }
  .chat-view--hidden-mobile { transform: translateX(100%); }
  .chat-view:not(.chat-view--hidden-mobile) { transform: translateX(0); }

  .panel-toggle {
    display: flex;
    align-items: center;
    justify-content: center;
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    z-index: 10;
    width: 22px;
    height: 48px;
    background: var(--surface);
    color: var(--text-mid);
    cursor: pointer;
    border: 1px solid var(--border);
    transition: background .15s, color .15s;
  }
  .panel-toggle--right {
    right: 0;
    border-right: none;
    border-radius: 10px 0 0 10px;
    box-shadow: -2px 0 8px rgba(0,0,0,.06);
  }
  .panel-toggle--left {
    left: 0;
    border-left: none;
    border-radius: 0 10px 10px 0;
    box-shadow: 2px 0 8px rgba(0,0,0,.06);
  }
  .panel-toggle:active {
    background: #16a34a;
    color: #fff;
    border-color: #16a34a;
  }

  .chat-back-btn { display: none; }
  .chat-view__head { display: flex; align-items: center; }

  .msg__bubble, .msg__bubble--streaming, .sources-list, .process-block, .context-block, .chat-article-card { width: 92%; max-width: 92%; }
}
</style>
