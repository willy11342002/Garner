<template>
  <div class="chat-page">
    <!-- 左側：session 列表 -->
    <aside class="chat-list" :class="{ 'chat-list--hidden-mobile': mobileView === 'chat' }">
      <div class="chat-list__head">
        <div v-if="quota?.chat" class="chat-quota" :class="{ 'chat-quota--warn': chatQuotaFull }">
          <div class="chat-quota__top">
            <span class="chat-quota__nums">
              <span class="chat-quota__remain">{{ chatQuotaRemaining }}</span><template v-if="quota.chat.limit !== null"> <span class="chat-quota__limit">/ {{ quota.chat.limit }}</span></template>
            </span>
            <span class="chat-quota__label">{{ t('chat.quota_label') }}</span>
          </div>
          <div v-if="quota.chat.limit !== null" class="chat-quota__bar">
            <div class="chat-quota__fill" :style="{ width: chatQuotaPct + '%' }"></div>
          </div>
        </div>
        <button class="chat-icon-btn" :title="t('chat.new')" @click="newSession">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><path d="M12 5v14M5 12h14"/></svg>
        </button>
      </div>
      <div class="chat-list__body">
        <!-- 資料夾區塊 -->
        <div class="folder-section">
          <div class="folder-section__head">
            <span class="folder-section__title">{{ t('chat.folders') }}</span>
            <button class="chat-icon-btn chat-icon-btn--sm" :title="t('chat.new_folder')" @click="startCreateFolder">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M12 5v14M5 12h14"/></svg>
            </button>
          </div>
          <input
            v-if="creatingFolder"
            ref="newFolderInput"
            v-model="newFolderName"
            class="folder-create-input"
            :placeholder="t('chat.folder_name_placeholder')"
            @keydown.enter.prevent="commitCreateFolder"
            @keydown.escape.prevent="creatingFolder = false"
            @blur="commitCreateFolder"
          >
          <p v-if="!folders.length && !creatingFolder" class="folder-section__empty">{{ t('chat.folder_hint') }}</p>
          <template v-for="folder in folders" :key="folder.id">
            <ChatFolderRow
              :folder="folder"
              :count="sessionsInFolder(folder.id).length"
              :expanded="expandedFolders.has(folder.id)"
              :dragging="draggingSessionId !== null"
              @toggle="toggleFolder(folder.id)"
              @rename="(id, name) => renameFolder(id, name)"
              @delete="deleteFolder(folder.id)"
              @drop-session="(sid) => moveSession(sid, folder.id)"
            />
            <div v-if="expandedFolders.has(folder.id)" class="folder-children">
              <ChatSessionRow
                v-for="s in sessionsInFolder(folder.id)"
                :key="s.id"
                :session="s"
                :active="activeSessionId === s.id"
                :disabled="sessionLoading"
                indent
                @click="openSession(s.id)"
                @rename="(id, name) => renameSession(id, name)"
                @delete="deleteSession(s.id)"
                @dragstart="draggingSessionId = $event"
                @dragend="draggingSessionId = null"
              />
            </div>
          </template>
        </div>

        <!-- 未分類：依時間分組，並作為「拖出資料夾」的 drop 區 -->
        <div
          class="uncategorized-zone"
          :class="{ 'uncategorized-zone--drop': draggingSessionId !== null }"
          @dragover.prevent
          @drop="(e) => onDropUncategorized(e)"
        >
          <div v-for="g in timeGroups" :key="g.key" class="session-group">
            <div class="time-label">{{ g.label }}</div>
            <ChatSessionRow
              v-for="s in g.sessions"
              :key="s.id"
              :session="s"
              :active="activeSessionId === s.id"
              :disabled="sessionLoading"
              @click="openSession(s.id)"
              @rename="(id, name) => renameSession(id, name)"
              @delete="deleteSession(s.id)"
              @dragstart="draggingSessionId = $event"
              @dragend="draggingSessionId = null"
            />
          </div>
        </div>
        <div v-if="!sessions.length" class="chat-list__empty">{{ t('chat.empty_list') }}</div>
      </div>
      <!-- 手機版：右邊緣切換箭頭 -->
    </aside>

    <!-- 右側：對話區 -->
    <div class="chat-view" :class="{ 'chat-view--hidden-mobile': mobileView === 'list' }">
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
                        <span class="process-body__step-icon">{{ stepIcon(step.toolCall.name) }}</span>
                        <code class="process-body__tool-name">{{ step.toolCall.name }}</code>
                        <span v-if="step.toolCall.query" class="process-body__param">query: "{{ step.toolCall.query }}"</span>
                        <span v-if="step.toolCall.name === 'add_trip_card' && step.toolCall.title" class="process-body__param">{{ step.toolCall.title }}</span>
                        <template v-if="step.toolCall.name === 'structured_filter'">
                          <span v-if="step.toolCall.tags?.length" class="process-body__param">tags: {{ step.toolCall.tags.join(', ') }}</span>
                          <span v-if="step.toolCall.source_type" class="process-body__param">source: {{ step.toolCall.source_type }}</span>
                          <span v-if="step.toolCall.start_date || step.toolCall.end_date" class="process-body__param">date: {{ step.toolCall.start_date ?? '…' }} ～ {{ step.toolCall.end_date ?? '…' }}</span>
                        </template>
                      </div>
                      <div v-if="step.toolResult" class="process-body__tool-result">
                        <span class="process-body__step-icon">✓</span>
                        <span>{{ stepResultLabel(step) }}</span>
                        <button
                          v-if="step.toolResult?.titles?.length && step.toolCall.name !== 'create_report'"
                          class="process-body__step-toggle"
                          @click="toggleStep(msg.id, i)"
                        >
                          <svg :class="{ 'process-body__step-chevron--open': openSteps.has(`${msg.id}-${i}`) }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="11" height="11"><path d="M6 9l6 6 6-6"/></svg>
                        </button>
                      </div>
                      <Transition name="thinking">
                        <div v-if="step.toolResult?.titles?.length && step.toolCall.name !== 'create_report' && openSteps.has(`${msg.id}-${i}`)" class="process-body__tool-titles">
                          <button v-for="item in step.toolResult.titles" :key="item.id ?? item" class="process-body__tool-title" @click="previewItemId = item.id ?? null">{{ item.title ?? item }}</button>
                        </div>
                      </Transition>
                    </div>
                  </div>
                  </Transition>
                </div>
              </template>

              <div
                class="msg__bubble"
                :class="{ 'msg__bubble--has-sources': msg.role === 'assistant' && sourcesMap[msg.id]?.length }"
              >
                <template v-if="msg.role === 'assistant'">
                  <TiptapEditor :model-value="msg.content" readonly />
                </template>
                <template v-else>{{ msg.content }}</template>
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
                  <div
                    v-for="src in sourcesMap[msg.id]"
                    :key="src.id"
                    class="src-card"
                    role="button"
                    @click="previewItemId = src.id"
                  >
                    <img v-if="src.thumbnail_url" :src="src.thumbnail_url" :alt="src.title || ''" class="src-card__thumb">
                    <div v-else class="src-card__thumb src-card__thumb--empty"></div>
                    <div class="src-card__body">
                      <span class="src-card__title">{{ src.title || src.url }}</span>
                      <span class="src-card__type">{{ sourceLabel(src.source_type) }}</span>
                    </div>
                  </div>
                </div>
              </Transition>
              <!-- AI 報告卡片 -->
              <ChatReportCard
                v-if="msg.role === 'assistant' && draftMap[msg.id]"
                :draft="draftMap[msg.id]"
              />
              <!-- AI 旅遊行程卡片 -->
              <ChatTripCard
                v-if="msg.role === 'assistant' && tripDraftMap[msg.id]"
                :draft="tripDraftMap[msg.id]"
              />
            </div>
          </template>

          <!-- 進行中的 agentic process（只在對應 session 顯示） -->
          <div v-if="(loading || streamingText) && streamingSessionId === activeSessionId" class="msg msg--assistant">
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
                    <span class="process-body__step-icon">{{ stepIcon(step.toolCall.name) }}</span>
                    <code class="process-body__tool-name">{{ step.toolCall.name }}</code>
                    <span v-if="step.toolCall.query" class="process-body__param">query: "{{ step.toolCall.query }}"</span>
                    <span v-if="step.toolCall.name === 'add_trip_card' && step.toolCall.title" class="process-body__param">{{ step.toolCall.title }}</span>
                    <template v-if="step.toolCall.name === 'structured_filter'">
                      <span v-if="step.toolCall.tags?.length" class="process-body__param">tags: {{ step.toolCall.tags.join(', ') }}</span>
                      <span v-if="step.toolCall.source_type" class="process-body__param">source: {{ step.toolCall.source_type }}</span>
                      <span v-if="step.toolCall.start_date || step.toolCall.end_date" class="process-body__param">date: {{ step.toolCall.start_date ?? '…' }} ～ {{ step.toolCall.end_date ?? '…' }}</span>
                    </template>
                  </div>
                  <div v-if="step.toolResult" class="process-body__tool-result">
                    <span class="process-body__step-icon">✓</span>
                    <span>{{ stepResultLabel(step) }}</span>
                    <button
                      v-if="step.toolResult?.titles?.length && step.toolCall.name !== 'create_report'"
                      class="process-body__step-toggle"
                      @click="toggleStep('live', i)"
                    >
                      <svg :class="{ 'process-body__step-chevron--open': openSteps.has(`live-${i}`) }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="11" height="11"><path d="M6 9l6 6 6-6"/></svg>
                    </button>
                  </div>
                  <Transition name="thinking">
                    <div v-if="step.toolResult?.titles?.length && step.toolCall.name !== 'create_report' && openSteps.has(`live-${i}`)" class="process-body__tool-titles">
                      <div v-for="title in step.toolResult.titles" :key="title" class="process-body__tool-title">{{ title }}</div>
                    </div>
                  </Transition>
                  <div v-if="!step.toolResult" class="process-body__tool-result process-body__tool-result--pending">
                    <span class="process-body__step-icon">⋯</span>
                    <span>{{ stepPendingLabel(step.toolCall.name) }}</span>
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
              <TiptapEditor :model-value="streamingText" readonly class="streaming-md" />
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
                <div
                  v-for="src in liveProcess.sources"
                  :key="src.id"
                  class="src-card"
                  role="button"
                  @click="previewItemId = src.id"
                >
                  <img v-if="src.thumbnail_url" :src="src.thumbnail_url" :alt="src.title || ''" class="src-card__thumb">
                  <div v-else class="src-card__thumb src-card__thumb--empty"></div>
                  <div class="src-card__body">
                    <span class="src-card__title">{{ src.title || src.url }}</span>
                    <span class="src-card__type">{{ sourceLabel(src.source_type) }}</span>
                  </div>
                </div>
              </div>
            </Transition>
            <ChatReportCard
              v-if="liveDraft"
              :draft="liveDraft"
            />
            <ChatTripCard
              v-if="liveTripDraft"
              :draft="liveTripDraft"
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
            <button
              v-if="loading && streamingSessionId === activeSessionId"
              class="chat-send-btn chat-send-btn--stop"
              :title="t('chat.stop')"
              @click="stopStreaming"
            >
              <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
            </button>
            <button v-else class="chat-send-btn" :disabled="!inputText.trim() || chatQuotaFull" @click="send">
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
import type { ReportDraft, TripDraft, ChatFolder, ChatMessage, ChatSession, ChatSessionDetail, ChatSource, UsageSummary } from '~/types/api'
useHead({ title: 'Garner — AI Chat' })

// keepalive：切換頁面時不 unmount 本頁，進行中的串流（send 迴圈與所有狀態）持續運作，
// 回來時同一個 instance 被重新啟用 → 直接看到即時生成內容，不中斷。
definePageMeta({ keepalive: true })

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
const sessionLoading = ref(false)
const streamingText = ref('')
// 追蹤正在串流的 session/message，供 openSession 切回時識別
const streamingSessionId = ref<string | null>(null)
const streamingMessageId = ref<string | null>(null)

// 串流中斷控制：停止鈕呼叫 abort()；idle timer 在長時間無事件時自動 abort 視為斷線
const abortController = ref<AbortController | null>(null)
const IDLE_TIMEOUT_MS = 45000

function stopStreaming() {
  // reason 用 AbortError 與 idle 逾時（TimeoutError）區分，catch 端據此決定是否提示
  abortController.value?.abort(new DOMException('stopped by user', 'AbortError'))
}

// idle 偵測提到 component scope，這樣 keepalive 切頁（onDeactivated）時可暫停計時器：
// 離開頁面時不該因「沒人看」而誤判斷線，後端會繼續跑完並存檔；回頁再重新計時。
const pageActive = ref(true)
const idleTimer = ref<ReturnType<typeof setTimeout> | null>(null)
function clearIdle() {
  if (idleTimer.value) { clearTimeout(idleTimer.value); idleTimer.value = null }
}
function armIdle() {
  clearIdle()
  // 只有「頁面在前景 + 正在串流」才計時；背景或非串流不計時
  if (!pageActive.value || !loading.value) return
  idleTimer.value = setTimeout(
    () => abortController.value?.abort(new DOMException('stream idle timeout', 'TimeoutError')),
    IDLE_TIMEOUT_MS,
  )
}

const mobileView = ref<'list' | 'chat'>('list')

// ── 資料夾 ──
const expandedFolders = ref<Set<string>>(new Set())
const draggingSessionId = ref<string | null>(null)
const creatingFolder = ref(false)
const newFolderName = ref('')
const newFolderInput = ref<HTMLInputElement | null>(null)

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

type ProcessStep = { toolCall: Record<string, any>; toolResult: Record<string, any> | null }
type ProcessLog = { thinking: string; steps: ProcessStep[] }
const liveProcess = ref<ProcessLog & { sources: ChatSource[] }>({ thinking: '', steps: [], sources: [] })

const processMap = ref<Record<string, ProcessLog>>({})

const pendingItemIds = ref<string[]>([])

const userContextMap = ref<Record<string, ChatSource[]>>({})

const draftMap = ref<Record<string, ReportDraft>>({})
const liveDraft = ref<ReportDraft | null>(null)
const tripDraftMap = ref<Record<string, TripDraft>>({})
const liveTripDraft = ref<TripDraft | null>(null)
const previewItemId = ref<string | null>(null)

const messagesEl = ref<HTMLElement | null>(null)
const inputEl = ref<HTMLTextAreaElement | null>(null)

const SOURCE_LABELS: Record<string, string> = { youtube: '▶ YouTube', article: 'Article', ig: 'IG', tiktok: '♪ TikTok' }

// ── Computed ──────────────────────────────────────────────────────────────────
const unfoldered = computed(() => sessions.value.filter(s => !s.folder_id))
const sessionsInFolder = (folderId: string) => sessions.value.filter(s => s.folder_id === folderId)

// 依 updated_at 把未分類對話切成「今天 / 本週 / 更早」三段
const timeGroups = computed(() => {
  const now = new Date()
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const startWeek = startToday - 6 * 86400000 // 含今天往前 7 天
  const today: ChatSession[] = []
  const week: ChatSession[] = []
  const earlier: ChatSession[] = []
  for (const s of unfoldered.value) {
    const ts = new Date(s.updated_at || s.created_at).getTime()
    if (ts >= startToday) today.push(s)
    else if (ts >= startWeek) week.push(s)
    else earlier.push(s)
  }
  return [
    { key: 'today', label: t('chat.group_today'), sessions: today },
    { key: 'week', label: t('chat.group_week'), sessions: week },
    { key: 'earlier', label: t('chat.group_earlier'), sessions: earlier },
  ].filter(g => g.sessions.length)
})
const chatQuotaFull = computed(() => {
  const q = quota.value?.chat
  return !!q && q.limit !== null && q.used >= q.limit
})
const chatQuotaRemaining = computed(() => {
  const q = quota.value?.chat
  if (!q || q.limit === null) return '∞'
  return Math.max(0, q.limit - q.used)
})
const chatQuotaPct = computed(() => {
  const q = quota.value?.chat
  if (!q || q.limit === null || q.limit === 0) return 100
  return Math.max(0, Math.min(100, ((q.limit - q.used) / q.limit) * 100))
})

// ── Init ──────────────────────────────────────────────────────────────────────
// 深連結處理：從別頁帶 ?session=&prefill=&items= 進來時開啟對話並（可選）自動送出。
// 抽成函式供 onMounted（首訪）與 onActivated（keepalive 回頁）共用。
async function handleRouteQuery() {
  const sid = route.query.session as string | undefined
  const prefill = route.query.prefill as string | undefined
  const itemsParam = route.query.items as string | undefined
  if (!sid) return
  await openSession(sid)
  router.replace({ query: {} })  // 清掉 URL query
  if (prefill) {
    if (itemsParam) pendingItemIds.value = itemsParam.split(',').filter(Boolean)
    inputText.value = prefill
    await nextTick()
    send()
  }
}

onMounted(async () => {
  await Promise.all([loadFolders(), loadSessions(), loadQuota()])
  await handleRouteQuery()
})

// keepalive 回頁：首次 activate 與 onMounted 同時發生，跳過以免重複處理；
// 之後每次回來才檢查是否有新的深連結，沒有就維持現狀（含進行中的串流）。
let firstActivate = true
onActivated(() => {
  pageActive.value = true
  if (loading.value) armIdle()  // 回頁若仍在串流，恢復 idle 計時
  if (firstActivate) { firstActivate = false; return }
  loadQuota()
  handleRouteQuery()
})

onDeactivated(() => {
  // 切走頁面：暫停 idle 計時，避免「沒人看」時把仍在跑的串流誤判為斷線並中止
  pageActive.value = false
  clearIdle()
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

// 樂觀建立中的臨時 session → 真實建立請求的 promise（供 send() 在送訊息前解析出真實 id）
const pendingSessionCreates = new Map<string, Promise<ChatSession>>()

// ── Session actions ───────────────────────────────────────────────────────────
async function newSession() {
  // 樂觀更新：先在本地插入臨時 session 並立即切到空白對話，背景建立，回來再換成真實 id。
  // 省去原本「POST 再 GET detail」兩次往返，點擊即時開新對話。
  const tempId = `temp-${Date.now()}`
  const now = new Date().toISOString()
  sessions.value.unshift({ id: tempId, folder_id: null, title: null, created_at: now, updated_at: now })

  // 直接在本地開啟空 session，不打 detail 請求
  activeSessionId.value = tempId
  activeSession.value = { id: tempId, folder_id: null, title: null, created_at: now, updated_at: now, messages: [] }
  messages.value = []
  sourcesMap.value = {}
  userContextMap.value = {}
  processMap.value = {}
  draftMap.value = {}
  tripDraftMap.value = {}
  openSources.value = new Set()
  resetProcess()
  mobileView.value = 'chat'

  const p = apiFetch<ChatSession>('/chat/sessions', { method: 'POST', body: {} })
  pendingSessionCreates.set(tempId, p)
  try {
    const real = await p
    const i = sessions.value.findIndex(x => x.id === tempId)
    if (i !== -1) sessions.value[i] = real
    if (activeSessionId.value === tempId) activeSessionId.value = real.id
    if (activeSession.value?.id === tempId) activeSession.value.id = real.id
  } catch {
    // 建立失敗：移除臨時 session，若仍停留其上則清空
    sessions.value = sessions.value.filter(x => x.id !== tempId)
    if (activeSessionId.value === tempId) {
      activeSessionId.value = null
      activeSession.value = null
      messages.value = []
    }
  } finally {
    pendingSessionCreates.delete(tempId)
  }
}

// 把（可能是樂觀建立中的）臨時 session id 解析成真實 id；失敗或仍無真實 id 回傳 null
async function resolveSessionId(id: string): Promise<string | null> {
  if (!id.startsWith('temp-')) return id
  const pending = pendingSessionCreates.get(id)
  if (pending) {
    try {
      const real = await pending
      if (activeSessionId.value === id) activeSessionId.value = real.id
      return real.id
    } catch {
      return null
    }
  }
  // 建立已完成並換好 id：採用目前的真實 active id
  const current = activeSessionId.value
  return current && !current.startsWith('temp-') ? current : null
}

async function openSession(id: string) {
  if (activeSessionId.value === id) { mobileView.value = 'chat'; return }
  if (sessionLoading.value) return
  sessionLoading.value = true
  activeSessionId.value = id
  const resumeStream = id === streamingSessionId.value
  try {
    const detail = await apiFetch<ChatSessionDetail>(`/chat/sessions/${id}`)
    if (activeSessionId.value !== id) { sessionLoading.value = false; return } // 載入期間又切到別的 session
    activeSession.value = detail
    messages.value = detail.messages
    sourcesMap.value = {}
    userContextMap.value = {}
    processMap.value = {}
    openSources.value = new Set()
    if (resumeStream) {
      // 切回正在串流的 session：保留 liveProcess，從 localStorage 還原已收到的文字
      streamingText.value = lsRead(streamingMessageId.value ?? '')
    } else if (!streamingSessionId.value) {
      // 無進行中 stream：正常重置
      resetProcess()
    }
    // 若有其他 session 在 stream 中（resumeStream=false but streamingSessionId != null）：
    // 不呼叫 resetProcess()，保留 liveProcess 讓切回時能還原

    draftMap.value = {}
    tripDraftMap.value = {}
    for (const msg of detail.messages) {
      if (msg.role === 'assistant' && msg.process_log) {
        processMap.value[msg.id] = msg.process_log as ProcessLog
        openThinking.value.delete(msg.id)
        const draftStep = (msg.process_log.steps as any[])?.find((s: any) => s.reportDraft)
        if (draftStep?.reportDraft) draftMap.value[msg.id] = draftStep.reportDraft
        const tripStep = (msg.process_log.steps as any[])?.find((s: any) => s.tripDraft)
        if (tripStep?.tripDraft) tripDraftMap.value[msg.id] = tripStep.tripDraft
      }
    }
    const lastAssistant = [...detail.messages].reverse().find(m => m.role === 'assistant' && m.process_log)
    if (lastAssistant) openThinking.value.add(lastAssistant.id)

    // 訊息已可顯示：立即切換畫面、結束 loading、捲到底，不等來源 item
    mobileView.value = 'chat'
    sessionLoading.value = false
    await nextTick()
    // 開啟時直接跳到底（instant），避免 smooth 動畫在內容高度未定時只捲一半
    requestAnimationFrame(() => scrollBottom(false))

    // 來源卡（cited items）在背景載入，避免 N+1 請求擋住整個讀取
    loadSourcesForMessages(id, detail.messages)
    return
  } catch {}
  sessionLoading.value = false
}

// 背景抓取訊息引用的 item，逐一填入來源卡；若期間切了別的 session 就丟棄結果
async function loadSourcesForMessages(sessionId: string, msgs: ChatMessage[]) {
  const assistantMsgs = msgs.filter(m => m.role === 'assistant' && m.cited_item_ids?.length)
  const userCtxMsgs = msgs.filter(m => m.role === 'user' && m.cited_item_ids?.length)
  const allIds = [...new Set([
    ...assistantMsgs.flatMap(m => m.cited_item_ids!),
    ...userCtxMsgs.flatMap(m => m.cited_item_ids!),
  ])]
  if (!allIds.length) return
  const itemResults = await Promise.allSettled(
    allIds.map(itemId => apiFetch<ChatSource>(`/items/${itemId}`))
  )
  if (activeSessionId.value !== sessionId) return
  // 填入來源前先記住是否在底部，填完若仍在底部就跟著捲到新的底部（修正「只捲一半」）
  const stick = isNearBottom()
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
  if (stick) {
    await nextTick()
    requestAnimationFrame(() => { if (activeSessionId.value === sessionId) scrollBottom(false) })
  }
}

async function renameSession(id: string, name: string) {
  // 樂觀更新：先改本地，背景送出，失敗回滾
  const s = sessions.value.find(x => x.id === id)
  const prevTitle = s?.title
  if (s) s.title = name
  const isActive = activeSession.value?.id === id
  const prevActiveTitle = isActive ? activeSession.value!.title : undefined
  if (isActive) activeSession.value!.title = name
  try {
    await apiFetch(`/chat/sessions/${id}`, { method: 'PATCH', body: { title: name } })
  } catch {
    if (s) s.title = prevTitle ?? null
    if (isActive && activeSession.value) activeSession.value.title = prevActiveTitle ?? null
  }
}

async function deleteSession(id: string) {
  // 樂觀更新：先從列表移除，失敗還原
  const idx = sessions.value.findIndex(s => s.id === id)
  if (idx === -1) return
  const removed = sessions.value[idx]
  sessions.value.splice(idx, 1)
  const wasActive = activeSessionId.value === id
  const prevActiveSession = activeSession.value
  const prevMessages = messages.value
  if (wasActive) {
    activeSessionId.value = null
    activeSession.value = null
    messages.value = []
  }
  try {
    await apiFetch(`/chat/sessions/${id}`, { method: 'DELETE' })
  } catch {
    sessions.value.splice(idx, 0, removed)
    if (wasActive) {
      activeSessionId.value = id
      activeSession.value = prevActiveSession
      messages.value = prevMessages
    }
  }
}

// ── Folder actions ────────────────────────────────────────────────────────────
function toggleFolder(id: string) {
  if (expandedFolders.value.has(id)) expandedFolders.value.delete(id)
  else expandedFolders.value.add(id)
}

function startCreateFolder() {
  creatingFolder.value = true
  newFolderName.value = ''
  nextTick(() => newFolderInput.value?.focus())
}

async function commitCreateFolder() {
  // Enter 會先關閉 input，移除時又觸發 blur → 本函式被呼叫兩次，故用 creatingFolder 當守衛避免重複建立
  if (!creatingFolder.value) return
  const name = newFolderName.value.trim()
  creatingFolder.value = false
  newFolderName.value = ''
  if (!name) return
  // 樂觀更新：先用臨時 id 插入，背景建立，回來再換成真實 folder
  const tempId = `temp-${Date.now()}`
  folders.value.push({ id: tempId, name, created_at: new Date().toISOString() } as ChatFolder)
  expandedFolders.value.add(tempId)
  try {
    const f = await apiFetch<ChatFolder>('/chat/folders', { method: 'POST', body: { name } })
    const i = folders.value.findIndex(x => x.id === tempId)
    if (i !== -1) folders.value[i] = f
    if (expandedFolders.value.delete(tempId)) expandedFolders.value.add(f.id)
    // 建立期間若有對話被拖進臨時資料夾，remap 到真實 id 並持久化
    for (const s of sessions.value) {
      if (s.folder_id === tempId) {
        s.folder_id = f.id
        apiFetch(`/chat/sessions/${s.id}`, { method: 'PATCH', body: { folder_id: f.id } }).catch(() => {})
      }
    }
  } catch {
    folders.value = folders.value.filter(x => x.id !== tempId)
    expandedFolders.value.delete(tempId)
    for (const s of sessions.value) { if (s.folder_id === tempId) s.folder_id = null }
  }
}

async function renameFolder(id: string, name: string) {
  // 樂觀更新
  const f = folders.value.find(x => x.id === id)
  if (!f) return
  const prev = f.name
  f.name = name
  try {
    await apiFetch(`/chat/folders/${id}`, { method: 'PATCH', body: { name } })
  } catch {
    f.name = prev
  }
}

async function deleteFolder(id: string) {
  // 樂觀更新：先移除資料夾並把對話移回未分類，失敗則全部還原
  const idx = folders.value.findIndex(f => f.id === id)
  if (idx === -1) return
  const removed = folders.value[idx]
  const wasExpanded = expandedFolders.value.has(id)
  folders.value.splice(idx, 1)
  expandedFolders.value.delete(id)
  const now = new Date().toISOString()
  const affected: { s: ChatSession; prevUpdated: string }[] = []
  for (const s of sessions.value) {
    if (s.folder_id === id) { affected.push({ s, prevUpdated: s.updated_at }); s.folder_id = null; s.updated_at = now }
  }
  try {
    await apiFetch(`/chat/folders/${id}`, { method: 'DELETE' })
  } catch {
    folders.value.splice(idx, 0, removed)
    if (wasExpanded) expandedFolders.value.add(id)
    for (const { s, prevUpdated } of affected) { s.folder_id = id; s.updated_at = prevUpdated }
  }
}

async function moveSession(sessionId: string, folderId: string | null) {
  const s = sessions.value.find(x => x.id === sessionId)
  if (!s || s.folder_id === folderId) return
  // 樂觀更新：先移動，失敗回滾
  const prevFolder = s.folder_id
  const prevUpdated = s.updated_at
  s.folder_id = folderId
  s.updated_at = new Date().toISOString()
  if (folderId) expandedFolders.value.add(folderId)
  // 臨時資料夾（建立中）後端尚未存在，先只改本地，待 commitCreateFolder 完成後再持久化
  if (folderId && folderId.startsWith('temp-')) return
  try {
    await apiFetch(`/chat/sessions/${sessionId}`, { method: 'PATCH', body: { folder_id: folderId } })
  } catch {
    s.folder_id = prevFolder
    s.updated_at = prevUpdated
  }
}

function onDropUncategorized(e: DragEvent) {
  const id = e.dataTransfer?.getData('text/plain')
  if (id) moveSession(id, null)
}

// ── localStorage partial-stream buffer ───────────────────────────────────────
const LS_PREFIX = 'partial_msg_'

function lsWrite(messageId: string, chunk: string) {
  try {
    const key = `${LS_PREFIX}${messageId}`
    const prev = localStorage.getItem(key)
    const data = prev ? JSON.parse(prev) : { text: '' }
    data.text += chunk
    localStorage.setItem(key, JSON.stringify(data))
  } catch { /* storage quota or private mode */ }
}

function lsClear(messageId: string) {
  try { localStorage.removeItem(`${LS_PREFIX}${messageId}`) } catch {}
}

function lsRead(messageId: string): string {
  try {
    const item = localStorage.getItem(`${LS_PREFIX}${messageId}`)
    return item ? (JSON.parse(item).text ?? '') : ''
  } catch { return '' }
}

// ── Send message ──────────────────────────────────────────────────────────────
function resetProcess() {
  liveProcess.value = { thinking: '', steps: [], sources: [] }
  streamingText.value = ''
  liveDraft.value = null
  liveTripDraft.value = null
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
  const currentSessionStreaming = loading.value && streamingSessionId.value === activeSessionId.value
  if (!inputText.value.trim() || currentSessionStreaming || !activeSessionId.value || chatQuotaFull.value) return

  const content = inputText.value.trim()
  let sessionId = activeSessionId.value
  inputText.value = ''
  resetInputHeight()
  loading.value = true
  resetProcess()

  if (sessionId.startsWith('temp-')) {
    const real = await resolveSessionId(sessionId)
    if (!real) {
      loading.value = false
      inputText.value = content
      resetInputHeight()
      return
    }
    sessionId = real
  }

  const isActive = () => activeSessionId.value === sessionId

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

  const abort = new AbortController()
  abortController.value = abort

  let messageId: string | null = null

  try {
    streamingSessionId.value = sessionId  // 在 POST 前就設定，讓 template 能立即識別 streaming session

    const itemIds = pendingItemIds.value.slice()
    pendingItemIds.value = []

    if (itemIds.length) {
      userMsg.cited_item_ids = itemIds
      const msgId = userMsg.id
      Promise.allSettled(
        itemIds.map(id => apiFetch<ChatSource>(`/items/${id}`))
      ).then(results => {
        if (!isActive()) return
        const items = results
          .filter((r): r is PromiseFulfilledResult<ChatSource> => r.status === 'fulfilled')
          .map(r => r.value)
        if (items.length) {
          userContextMap.value[msgId] = items
          openContexts.value = new Set([...openContexts.value, msgId])
        }
      })
    }

    armIdle()

    // Step 1: POST → 201 + { message_id }
    const postResp = await fetch(`${apiBase}/chat/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ content, ...(itemIds.length ? { item_ids: itemIds } : {}) }),
      signal: abort.signal,
    })
    if (!postResp.ok) throw new Error('request failed')
    const json = await postResp.json()
    messageId = json.message_id
    streamingMessageId.value = messageId

    // Step 2: connect SSE stream
    await connectAndStream(sessionId, messageId!, isActive, isFirstMessage, content)

  } catch (err: any) {
    if (err?.name === 'AbortError') {
      if (isActive()) resetProcess()
    } else if (messageId) {
      // POST 成功但串流中斷 → 顯示 partial，重連一次
      if (isActive()) streamingText.value = lsRead(messageId)
      try {
        await connectAndStream(sessionId, messageId, isActive, isFirstMessage, content, true)
      } catch {
        if (isActive()) {
          resetProcess()
          messages.value.push({
            id: crypto.randomUUID(),
            role: 'assistant',
            content: t('chat.error'),
            cited_item_ids: null,
            created_at: new Date().toISOString(),
          })
        }
      }
    } else if (isActive()) {
      resetProcess()
      messages.value.push({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: t('chat.error'),
        cited_item_ids: null,
        created_at: new Date().toISOString(),
      })
    }
  } finally {
    clearIdle()
    abortController.value = null
    loading.value = false
    streamingSessionId.value = null
    streamingMessageId.value = null
  }
}

async function connectAndStream(
  sessionId: string,
  messageId: string,
  isActive: () => boolean,
  isFirstMessage: boolean,
  content: string,
  isReconnect = false,
) {
  const apiBase = config.public.apiBase as string
  const token = session.value?.access_token

  // 重連時清空 streamingText，讓 replay 從頭重建
  if (isReconnect) streamingText.value = ''

  const resp = await fetch(`${apiBase}/chat/sessions/${sessionId}/messages/${messageId}/stream`, {
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    signal: abortController.value?.signal,
  })
  if (!resp.ok) throw new Error('stream request failed')

  const reader = resp.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let pendingSources: ChatSource[] = []

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    armIdle()
    buffer += decoder.decode(value, { stream: true })

    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''

    for (const part of parts) {
      if (!part.startsWith('event: ')) continue
      const lines = part.split('\n')
      const event = lines[0].replace('event: ', '')
      const dataLine = lines.find(l => l.startsWith('data: '))
      if (!dataLine) continue
      const data = JSON.parse(dataLine.replace('data: ', ''))

      if (event === 'thinking') {
        if (!isActive()) continue
        liveProcess.value.thinking = data.text
        await nextTick(); scrollBottom()

      } else if (event === 'tool_call') {
        if (!isActive()) continue
        liveProcess.value.steps.push({ toolCall: data, toolResult: null })
        await nextTick(); scrollBottom()

      } else if (event === 'tool_result') {
        if (!isActive()) continue
        const steps = liveProcess.value.steps
        if (steps.length) steps[steps.length - 1].toolResult = data
        await nextTick(); scrollBottom()

      } else if (event === 'report_draft') {
        if (!isActive()) continue
        liveDraft.value = data as ReportDraft
        await nextTick(); scrollBottom()

      } else if (event === 'trip_draft') {
        if (!isActive()) continue
        liveTripDraft.value = data as TripDraft
        await nextTick(); scrollBottom()

      } else if (event === 'sources') {
        pendingSources = data as ChatSource[]
        if (isActive()) liveProcess.value.sources = pendingSources

      } else if (event === 'delta') {
        lsWrite(messageId, data.text)  // 不管 isActive 都寫，切回時可還原
        if (!isActive()) continue
        streamingText.value += data.text
        await nextTick(); scrollBottom()

      } else if (event === 'done') {
        lsClear(messageId)
        if (isActive()) {
          // replay 時 done 帶有 process_log；live 時用 liveProcess
          processMap.value[messageId] = data.process_log ?? {
            thinking: liveProcess.value.thinking,
            steps: liveProcess.value.steps,
          }
          if (liveDraft.value) {
            draftMap.value[messageId] = liveDraft.value
            liveDraft.value = null
          }
          if (liveTripDraft.value) {
            tripDraftMap.value[messageId] = liveTripDraft.value
            liveTripDraft.value = null
          }
          openThinking.value.delete('live')
          openThinking.value.add(messageId)

          const assistantMsg: ChatMessage = {
            id: messageId,
            role: 'assistant',
            content: streamingText.value,
            cited_item_ids: pendingSources.map(s => s.id),
            created_at: new Date().toISOString(),
          }
          messages.value.push(assistantMsg)
          if (pendingSources.length) {
            sourcesMap.value[messageId] = pendingSources
          }

          if (isFirstMessage && !activeSession.value?.title) {
            const title = content.slice(0, 40) + (content.length > 40 ? '…' : '')
            if (activeSession.value) activeSession.value.title = title
            const idx = sessions.value.findIndex(s => s.id === sessionId)
            if (idx !== -1) sessions.value[idx].title = title
          }

          resetProcess()
          await nextTick(); scrollBottom()
        } else {
          if (isFirstMessage) {
            const title = content.slice(0, 40) + (content.length > 40 ? '…' : '')
            const idx = sessions.value.findIndex(s => s.id === sessionId)
            if (idx !== -1) sessions.value[idx].title = title
          }
        }
      }
    }
  }
}

// ── UI helpers ────────────────────────────────────────────────────────────────
function scrollBottom(smooth = true) {
  const el = messagesEl.value
  if (el) el.scrollTo({ top: el.scrollHeight, behavior: smooth ? 'smooth' : 'auto' })
}

// 使用者是否已捲到接近底部（用來判斷背景內容載入後要不要自動跟到底）
function isNearBottom(threshold = 120) {
  const el = messagesEl.value
  if (!el) return true
  return el.scrollHeight - el.scrollTop - el.clientHeight < threshold
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

// ── 推理過程：各工具的圖示／結果文字／進行中文字 ──
function stepIcon(name: string) {
  return name === 'add_trip_card' ? '📍'
    : name === 'create_trip' ? '🗺️'
    : name === 'create_report' ? '📝'
    : name === 'filter_sources' ? '🎯'
    : name === 'save_url' ? '📥'
    : '🔍'
}
function stepResultLabel(step: any): string {
  const n = step.toolCall?.name
  const r = step.toolResult || {}
  if (n === 'create_report') return `報告已建立：${r.title ?? ''}`
  if (n === 'create_trip') return `行程已建立：${r.title ?? ''}`
  if (n === 'add_trip_card') return r.ok ? `新增卡片：${r.title ?? ''}` : '卡片新增失敗'
  if (n === 'save_url') return r.ok ? `已存入「${r.title ?? ''}」` : (r.error === 'quota_exceeded' ? '存入額度已用完' : '存入失敗')
  return `找到 ${r.count ?? 0} 筆`
}
function stepPendingLabel(name: string): string {
  if (name === 'create_report' || name === 'create_trip') return '生成中'
  if (name === 'add_trip_card') return '新增中'
  if (name === 'filter_sources') return '篩選中'
  if (name === 'save_url') return '存入中'
  return '搜尋中'
}

</script>

<style scoped>
:deep(.app-footer) { display: none; }

/* streaming 游標：附在最後一個段落之後 */
:deep(.streaming-md .tiptap-root p:last-child::after) {
  content: '▍';
  display: inline;
  color: var(--accent);
  animation: blink 1s step-start infinite;
}
@keyframes blink { 50% { opacity: 0; } }
</style>
