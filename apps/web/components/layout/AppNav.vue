<template>
  <div>
    <nav class="nav">
      <button class="nav__hamburger" @click="toggleMobileMenu">
        <svg v-if="!mobileMenuOpen" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
      <NuxtLink to="/app" class="nav__logo">Garner</NuxtLink>
      <div class="nav__tabs">
        <NuxtLink
          to="/app/chat"
          class="nav__tab"
          :class="{ 'nav__tab--active': route.path.startsWith('/app/chat') }"
        >{{ t('nav.chat') }}</NuxtLink>
        <NuxtLink
          to="/app/reports"
          class="nav__tab"
          :class="{ 'nav__tab--active': route.path.startsWith('/app/reports') }"
        >{{ t('nav.reports') }}</NuxtLink>
        <NuxtLink
          to="/app/trips"
          class="nav__tab"
          :class="{ 'nav__tab--active': route.path.startsWith('/app/trips') }"
        >{{ t('nav.trips') }}</NuxtLink>
      </div>
      <div class="nav__right">
        <!-- 新增 -->
        <button class="nav__add" @click="openAdd">
          +
        </button>

        <!-- 通知鈴鐺 -->
        <div class="nav__notif" ref="notifEl">
          <button class="nav__notif-btn" @click.stop="toggleNotif">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
              <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
            </svg>
            <span v-if="notifStore.unreadCount > 0" class="nav__notif-badge">{{ notifStore.unreadCount > 9 ? '9+' : notifStore.unreadCount }}</span>
          </button>

          <Transition name="menu">
            <div v-if="notifOpen" class="nav__notif-panel">
              <div class="nav__notif-header">
                <span>{{ t('notif.title') }}</span>
                <button v-if="notifStore.unreadCount > 0" class="nav__notif-readall" @click="notifStore.markAllRead()">{{ t('notif.markAllRead') }}</button>
              </div>
              <div class="nav__notif-list">
                <div v-if="notifStore.items.length === 0" class="nav__notif-empty">{{ t('notif.empty') }}</div>
                <div
                  v-for="n in notifStore.items"
                  :key="n.id"
                  class="nav__notif-item"
                  :class="{ 'nav__notif-item--unread': !n.is_read }"
                  @click="openItemFromNotif(n)"
                >
                  <span class="nav__notif-dot" :class="{ 'nav__notif-dot--visible': !n.is_read }" />
                  <span class="nav__notif-content">
                    <span class="nav__notif-text">{{ n.title }}</span>
                    <span class="nav__notif-time">{{ formatNotifTime(n.created_at) }}</span>
                  </span>
                </div>
              </div>
            </div>
          </Transition>
        </div>

        <!-- 使用者頭像 + 下拉選單 -->
        <div class="nav__user">
          <button class="nav__avatar" @click.stop="toggleMenu">
            <img v-if="avatarUrl" :src="avatarUrl" :alt="displayName" referrerpolicy="no-referrer">
            <span v-else>{{ initials }}</span>
          </button>

          <Transition name="menu">
            <div v-if="menuOpen" class="nav__menu">

              <!-- Main panel -->
              <template v-if="menuPanel === 'main'">
                <div class="nav__menu-header">
                  <span class="nav__menu-name">{{ displayName }}</span>
                  <span class="nav__menu-email">{{ supabaseUser?.email }}</span>
                </div>
                <div class="nav__menu-divider" />
                <button class="nav__menu-item" @click="goTo('/app/archive')">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M21 8v13H3V8"/><path d="M23 3H1v5h22V3z"/><path d="M10 12h4"/></svg>
                  {{ t('nav.archive') }}
                </button>
                <div class="nav__menu-divider" />
                <button class="nav__menu-item" @click="goTo('/app/settings')">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
                  {{ t('nav.settings') }}
                </button>
                <button class="nav__menu-item" @click="goTo('/app/security')">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                  {{ t('nav.security') }}
                </button>
                <button class="nav__menu-item" @click="goTo('/app/billing')">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>
                  {{ t('nav.billing') }}
                </button>
                <div class="nav__menu-divider" />
                <button class="nav__menu-item nav__menu-item--chevron" @click="menuPanel = 'appearance'">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>
                  {{ t('nav.appearance') }}
                  <svg class="nav__menu-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M9 18l6-6-6-6"/></svg>
                </button>
                <button class="nav__menu-item nav__menu-item--chevron" @click="menuPanel = 'language'">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
                  {{ t('nav.language') }}
                  <svg class="nav__menu-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M9 18l6-6-6-6"/></svg>
                </button>
                <div class="nav__menu-divider" />
                <button class="nav__menu-item nav__menu-item--danger" @click="signOut">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></svg>
                  {{ t('nav.signOut') }}
                </button>
              </template>

              <!-- Appearance panel -->
              <template v-else-if="menuPanel === 'appearance'">
                <button class="nav__menu-back" @click="menuPanel = 'main'">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M15 18l-6-6 6-6"/></svg>
                  {{ t('nav.appearance') }}
                </button>
                <div class="nav__menu-divider" />
                <button class="nav__menu-item nav__menu-item--check" :class="{ 'nav__menu-item--checked': themeMode === 'system' }" @click="setMode('system')">
                  <svg v-if="themeMode === 'system'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" class="nav__check-icon"><polyline points="20 6 9 17 4 12"/></svg>
                  <span v-else class="nav__check-placeholder" />
                  {{ t('settings.appearance.system') }}
                </button>
                <button class="nav__menu-item nav__menu-item--check" :class="{ 'nav__menu-item--checked': themeMode === 'dark' }" @click="setMode('dark')">
                  <svg v-if="themeMode === 'dark'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" class="nav__check-icon"><polyline points="20 6 9 17 4 12"/></svg>
                  <span v-else class="nav__check-placeholder" />
                  {{ t('settings.appearance.dark') }}
                </button>
                <button class="nav__menu-item nav__menu-item--check" :class="{ 'nav__menu-item--checked': themeMode === 'light' }" @click="setMode('light')">
                  <svg v-if="themeMode === 'light'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" class="nav__check-icon"><polyline points="20 6 9 17 4 12"/></svg>
                  <span v-else class="nav__check-placeholder" />
                  {{ t('settings.appearance.light') }}
                </button>
              </template>

              <!-- Language panel -->
              <template v-else-if="menuPanel === 'language'">
                <button class="nav__menu-back" @click="menuPanel = 'main'">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M15 18l-6-6 6-6"/></svg>
                  {{ t('nav.language') }}
                </button>
                <div class="nav__menu-divider" />
                <button class="nav__menu-item nav__menu-item--check" :class="{ 'nav__menu-item--checked': locale === 'zh-TW' }" @click="setLocale('zh-TW')">
                  <svg v-if="locale === 'zh-TW'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" class="nav__check-icon"><polyline points="20 6 9 17 4 12"/></svg>
                  <span v-else class="nav__check-placeholder" />
                  繁體中文
                </button>
                <button class="nav__menu-item nav__menu-item--check" :class="{ 'nav__menu-item--checked': locale === 'en' }" @click="setLocale('en')">
                  <svg v-if="locale === 'en'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" class="nav__check-icon"><polyline points="20 6 9 17 4 12"/></svg>
                  <span v-else class="nav__check-placeholder" />
                  English
                </button>
              </template>

            </div>
          </Transition>
        </div>
      </div>
    </nav>

    <!-- 手機 drawer -->
    <Transition name="drawer">
      <div v-if="mobileMenuOpen" class="nav__drawer">
        <nav class="nav__drawer-nav">
          <NuxtLink to="/app" class="nav__drawer-item" :class="{ 'nav__drawer-item--active': route.path === '/app' }" @click="mobileMenuOpen = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M12 2a7 7 0 0 1 7 7c0 2.5-1.3 4.7-3.3 6H8.3C6.3 13.7 5 11.5 5 9a7 7 0 0 1 7-7z"/><path d="M9 21h6"/><path d="M10 18h4"/></svg>
            {{ t('nav.knowledge') }}
          </NuxtLink>
          <NuxtLink to="/app/chat" class="nav__drawer-item" :class="{ 'nav__drawer-item--active': route.path.startsWith('/app/chat') }" @click="mobileMenuOpen = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            {{ t('nav.chat') }}
          </NuxtLink>
          <NuxtLink to="/app/reports" class="nav__drawer-item" :class="{ 'nav__drawer-item--active': route.path.startsWith('/app/reports') }" @click="mobileMenuOpen = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
            {{ t('nav.reports') }}
          </NuxtLink>
          <NuxtLink to="/app/trips" class="nav__drawer-item" :class="{ 'nav__drawer-item--active': route.path.startsWith('/app/trips') }" @click="mobileMenuOpen = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/><line x1="9" y1="3" x2="9" y2="18"/><line x1="15" y1="6" x2="15" y2="21"/></svg>
            {{ t('nav.trips') }}
          </NuxtLink>
        </nav>
      </div>
    </Transition>
    <div v-if="mobileMenuOpen" class="nav__drawer-backdrop" @click="mobileMenuOpen = false" />

    <!-- Backdrops -->
    <div v-if="menuOpen" class="nav__backdrop" @click="menuOpen = false" />
    <div v-if="notifOpen" class="nav__backdrop" @click="notifOpen = false" />

    <!-- 新增 URL modal -->
    <Transition name="modal">
      <div v-if="addOpen" class="add-overlay" @click.self="closeAdd">
        <div class="add-modal">
          <template v-if="addProcessingItemId">
            <div class="add-modal__processing">
              <span class="add-modal__processing-dot"></span>
              <p class="add-modal__processing-text">{{ t('add.processing') }}</p>
            </div>
            <ol class="add-modal__steps">
              <li
                v-for="(s, i) in PIPELINE_STAGES"
                :key="s"
                class="add-modal__step"
                :class="{
                  'add-modal__step--done': i < processingStep,
                  'add-modal__step--active': i === processingStep,
                }"
              >
                <span class="add-modal__step-icon">
                  <svg v-if="i < processingStep" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="3 8 6 11 13 4"/></svg>
                  <span v-else-if="i === processingStep" class="add-modal__step-spinner"></span>
                  <span v-else class="add-modal__step-idle"></span>
                </span>
                {{ t(`pipeline.${s}`) }}
              </li>
            </ol>
            <p class="add-modal__hint">{{ t('add.processingHint') }}</p>
          </template>
          <template v-else>
            <p class="add-modal__label">{{ t('add.label') }}</p>
            <div class="add-modal__row" :class="{ 'add-modal__row--disabled': savesQuotaFull }">
              <input
                ref="addInput"
                v-model="addUrl"
                class="add-modal__input"
                :placeholder="savesQuotaFull ? t('add.error_quota_full') : t('add.placeholder')"
                :disabled="addSaving || savesQuotaFull"
                @keydown.enter="submitAdd"
                @keydown.esc="closeAdd"
              />
              <button v-if="!savesQuotaFull" class="btn btn--accent" :disabled="addSaving || !addUrl.trim()" @click="submitAdd">
                {{ addSaving ? t('add.saving') : t('add.save') }}
              </button>
            </div>
            <p v-if="addError" class="add-modal__error">{{ addError }}</p>
            <div class="add-modal__divider"><span>{{ t('add.orDivider') }}</span></div>
            <button class="add-modal__write-btn" :disabled="writingArticle" @click="handleWriteArticle">
              {{ writingArticle ? t('add.saving') : t('add.writeArticle') }}
            </button>
          </template>
        </div>
      </div>
    </Transition>

    <!-- Item detail modal (通知共用) -->
    <ItemDetailModal
      :item-id="activeItemId"
      :start-in-edit="activeItemEditMode"
      @close="closeItemModal()"
      @archived="onItemArchived"
    />
  </div>
</template>

<script setup lang="ts">
import type { UsageSummary } from '~/types/api'

const { t, te, locale, setLocale } = useI18n()
const route = useRoute()
const router = useRouter()
const { mode: themeMode, setMode } = useTheme()
const supabaseUser = useSupabaseUser()
const client = useSupabaseClient()
const authStore = useAuthStore()
const itemStore = useItemStore()
const notifStore = useNotificationStore()
const apiFetch = useApiFetch()

// 手機 drawer
const mobileMenuOpen = ref(false)
const menuOpen = ref(false)
const notifOpen = ref(false)

function toggleMobileMenu() {
  const wasOpen = mobileMenuOpen.value
  closeAllOverlays()
  mobileMenuOpen.value = !wasOpen
}

function toggleMenu() {
  const wasOpen = menuOpen.value
  closeAllOverlays()
  menuOpen.value = !wasOpen
}

function closeAllOverlays() {
  mobileMenuOpen.value = false
  menuOpen.value = false
  notifOpen.value = false
  addOpen.value = false
}

// 開啟通知面板即全部標記已讀（badge 歸零），歷史仍保留在列表
function toggleNotif() {
  const wasOpen = notifOpen.value
  closeAllOverlays()
  notifOpen.value = !wasOpen
  if (notifOpen.value && notifStore.unreadCount > 0) notifStore.markAllRead()
}

function openAdd() {
  closeAllOverlays()
  addOpen.value = true
}

function formatNotifTime(isoStr: string) {
  const diff = Date.now() - new Date(isoStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return t('notif.justNow')
  if (mins < 60) return t('notif.minutesAgo', { n: mins })
  const hours = Math.floor(mins / 60)
  if (hours < 24) return t('notif.hoursAgo', { n: hours })
  return t('notif.daysAgo', { n: Math.floor(hours / 24) })
}

const menuPanel = ref<'main' | 'appearance' | 'language'>('main')

// Item detail modal
const { activeItemId, activeItemEditMode, open: openItemModal, openInEdit: openItemInEdit, close: closeItemModal } = useItemModal()

// 新增文章（建立後直接開 modal 編輯）
const { createArticle } = useArticles()
const writingArticle = ref(false)
async function handleWriteArticle() {
  if (writingArticle.value) return
  writingArticle.value = true
  closeAdd()
  try {
    const article = await createArticle()
    openItemInEdit(article.id)
  } catch { /* ignore */ } finally {
    writingArticle.value = false
  }
}

function onItemArchived() {
  if (!activeItemId.value) return
  const idx = itemStore.items.findIndex(i => i.id === activeItemId.value)
  if (idx !== -1) itemStore.items.splice(idx, 1)
  closeItemModal()
}

function openItemFromNotif(n: { id: string; item_id?: string | null }) {
  notifStore.markRead([n.id])
  notifOpen.value = false
  if (n.item_id) openItemModal(n.item_id)
}

// 新增 modal
const addOpen = ref(false)
const addUrl = ref('')
const addSaving = ref(false)
const addError = ref('')
const addInput = ref<HTMLInputElement | null>(null)
const addProcessingItemId = ref<string | null>(null)
const processingStep = ref(0)
const PIPELINE_STAGES = ['fetch', 'assets', 'note', 'landmarks', 'embedding'] as const

const addQuota = ref<UsageSummary | null>(null)
const savesQuotaFull = computed(() => {
  const q = addQuota.value?.saves
  return !!q && q.limit !== null && q.used >= q.limit
})

function stageToStep(stage: string): number {
  const idx = PIPELINE_STAGES.indexOf(stage as typeof PIPELINE_STAGES[number])
  return idx >= 0 ? idx : 0
}

watch(addOpen, async (val) => {
  if (val) {
    nextTick(() => addInput.value?.focus())
    try { addQuota.value = await apiFetch<UsageSummary>('/quota/me') } catch {}
  } else {
    addUrl.value = ''
    addError.value = ''
    addProcessingItemId.value = null
    processingStep.value = 0
  }
})

// Drive step indicator from real SSE stage events
watch(() => addProcessingItemId.value && itemStore.processingStages.get(addProcessingItemId.value), (stage) => {
  if (stage) processingStep.value = stageToStep(stage)
})

watch(() => itemStore.recentlyProcessed, (itemId) => {
  if (itemId && itemId === addProcessingItemId.value) {
    processingStep.value = PIPELINE_STAGES.length
    notifStore.fetch()
    setTimeout(() => {
      addProcessingItemId.value = null
      addOpen.value = false
    }, 600)
  }
})

function closeAdd() {
  if (addSaving.value) return
  addOpen.value = false
}

async function submitAdd() {
  const url = addUrl.value.trim()
  if (!url || addSaving.value) return
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    addError.value = t('add.error_invalid_url')
    return
  }
  addSaving.value = true
  addError.value = ''
  try {
    const item = await itemStore.add({ url })
    addUrl.value = ''
    addProcessingItemId.value = item.id
    if (!route.path.startsWith('/app') || route.path === '/app/archive') {
      navigateTo('/app')
    }
  } catch (err: any) {
    const code = err?.errorCode as string | undefined
    const i18nKey = code ? `add.error_${code}` : null
    addError.value = (i18nKey && te(i18nKey)) ? t(i18nKey) : t('add.error')
  } finally {
    addSaving.value = false
  }
}

const avatarUrl = computed(() =>
  authStore.user?.avatar_url
  ?? supabaseUser.value?.user_metadata?.avatar_url
  ?? null
)
const displayName = computed(() =>
  authStore.user?.username
  ?? supabaseUser.value?.user_metadata?.full_name
  ?? supabaseUser.value?.user_metadata?.name
  ?? supabaseUser.value?.email?.split('@')[0]
  ?? '使用者'
)
const initials = computed(() =>
  displayName.value.slice(0, 2).toUpperCase()
)

function goTo(path: string) {
  menuOpen.value = false
  router.push(path)
}

async function signOut() {
  menuOpen.value = false
  await client.auth.signOut()
  authStore.clear()
  navigateTo('/')
}

watch(menuOpen, (val) => {
  if (!val) menuPanel.value = 'main'
})

watch(() => route.path, () => {
  menuOpen.value = false
  notifOpen.value = false
  mobileMenuOpen.value = false
  closeItemModal()
})

watch(supabaseUser, (user) => {
  if (user) notifStore.startPolling()
  else notifStore.stopPolling()
}, { immediate: true })

onUnmounted(() => notifStore.stopPolling())
</script>
