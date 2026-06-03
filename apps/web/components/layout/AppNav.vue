<template>
  <div>
    <nav class="nav">
      <NuxtLink to="/app" class="nav__logo">Vela</NuxtLink>
      <div class="nav__tabs">
        <div class="nav__tab-group">
          <span
            class="nav__tab"
            :class="{ 'nav__tab--active': route.path.startsWith('/app/explore') }"
          >{{ t('nav.explore') }}</span>
          <div class="nav__explore-menu">
            <div class="nav__explore-menu-inner">
              <NuxtLink to="/app/explore/surprise" class="nav__explore-item" active-class="nav__explore-item--active">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
                {{ t('explore.tab_surprise') }}
              </NuxtLink>
              <NuxtLink to="/app/explore/browse" class="nav__explore-item" active-class="nav__explore-item--active">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
                {{ t('explore.tab_browse') }}
              </NuxtLink>
            </div>
          </div>
        </div>
        <NuxtLink
          to="/app/chat"
          class="nav__tab"
          :class="{ 'nav__tab--active': route.path.startsWith('/app/chat') }"
        >{{ t('nav.chat') }}</NuxtLink>
      </div>
      <div class="nav__right">
        <!-- 桌機搜尋 input -->
        <div class="nav__search" ref="searchEl">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="7"/>
            <path d="m20 20-3.5-3.5"/>
          </svg>
          <input
            type="text"
            v-model="searchQuery"
            :placeholder="t('nav.searchPlaceholder')"
            @keydown.esc="closeSearch"
          >
          <Transition name="search-drop">
            <div v-if="searchOpen" class="search-drop">
              <div v-if="searchLoading" class="search-drop__state">
                <span class="search-drop__spinner"></span>
                {{ t('nav.searchLoading') }}
              </div>
              <template v-else-if="searchResults.length > 0">
                <button
                  v-for="item in searchResults.slice(0, 8)"
                  :key="item.id"
                  class="search-drop__item"
                  @click="closeSearch(); openItemModal(item.id)"
                >
                  <div class="search-drop__thumb">
                    <img v-if="item.thumbnail_url" :src="item.thumbnail_url" alt="">
                    <div v-else class="placeholder placeholder--b">
                      <div class="placeholder__stripes"></div>
                    </div>
                  </div>
                  <div class="search-drop__info">
                    <span class="search-drop__title">{{ item.title || item.url }}</span>
                    <span class="search-drop__meta mono">{{ searchSourceLabel(item.url) }}</span>
                  </div>
                </button>
              </template>
              <div v-else-if="searchDone" class="search-drop__state">
                {{ t('nav.searchEmpty') }}
              </div>
            </div>
          </Transition>
        </div>

        <!-- 手機版搜尋 icon -->
        <button class="nav__search-btn" @click="mobileSearchOpen = true">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="7"/>
            <path d="m20 20-3.5-3.5"/>
          </svg>
        </button>

        <!-- 新增 -->
        <button class="nav__add" @click="addOpen = true">
          +
        </button>

        <!-- 通知鈴鐺 -->
        <div class="nav__notif" ref="notifEl">
          <button class="nav__notif-btn" @click.stop="notifOpen = !notifOpen">
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
          <button class="nav__avatar" @click.stop="menuOpen = !menuOpen">
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
                <button class="nav__menu-item" @click="goTo('/app/collections')">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>
                  {{ t('nav.collections') }}
                </button>
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

    <!-- Backdrops -->
    <div v-if="menuOpen" class="nav__backdrop" @click="menuOpen = false" />
    <div v-if="searchOpen" class="nav__backdrop" @click="closeSearch" />
    <div v-if="notifOpen" class="nav__backdrop" @click="notifOpen = false" />

    <!-- 手機版搜尋 modal -->
    <Transition name="modal">
      <div v-if="mobileSearchOpen" class="add-overlay" @click.self="closeMobileSearch">
        <div class="add-modal search-modal">
          <div class="search-modal__input-row">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="search-modal__icon">
              <circle cx="11" cy="11" r="7"/>
              <path d="m20 20-3.5-3.5"/>
            </svg>
            <input
              ref="mobileSearchInput"
              v-model="searchQuery"
              class="add-modal__input search-modal__input"
              :placeholder="t('nav.searchPlaceholder')"
              @keydown.esc="closeMobileSearch"
            />
          </div>
          <div v-if="searchLoading" class="search-modal__state">
            <span class="add-modal__step-spinner"></span>
            {{ t('nav.searchLoading') }}
          </div>
          <template v-else-if="searchResults.length > 0">
            <button
              v-for="item in searchResults.slice(0, 8)"
              :key="item.id"
              class="search-modal__item"
              @click="closeMobileSearch(); openItemModal(item.id)"
            >
              <div class="search-modal__thumb">
                <img v-if="item.thumbnail_url" :src="item.thumbnail_url" alt="">
                <div v-else class="placeholder placeholder--b"><div class="placeholder__stripes"></div></div>
              </div>
              <div class="search-modal__info">
                <span class="search-modal__title">{{ item.title || item.url }}</span>
                <span class="search-modal__meta mono">{{ searchSourceLabel(item.url) }}</span>
              </div>
            </button>
          </template>
          <div v-else-if="searchDone" class="search-modal__state">
            {{ t('nav.searchEmpty') }}
          </div>
        </div>
      </div>
    </Transition>

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
                v-for="(key, i) in ['step1','step2','step3','step4']"
                :key="key"
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
                {{ t(`add.${key}`) }}
              </li>
            </ol>
            <p class="add-modal__hint">{{ t('add.processingHint') }}</p>
          </template>
          <template v-else>
            <p class="add-modal__label">{{ t('add.label') }}</p>
            <div class="add-modal__row">
              <input
                ref="addInput"
                v-model="addUrl"
                class="add-modal__input"
                :placeholder="t('add.placeholder')"
                :disabled="addSaving"
                @keydown.enter="submitAdd"
                @keydown.esc="closeAdd"
              />
              <button class="btn btn--accent" :disabled="addSaving || !addUrl.trim()" @click="submitAdd">
                {{ addSaving ? t('add.saving') : t('add.save') }}
              </button>
            </div>
            <p v-if="addError" class="add-modal__error">{{ addError }}</p>
          </template>
        </div>
      </div>
    </Transition>

    <!-- Item detail modal (搜尋 + 通知共用) -->
    <ItemDetailModal
      :item-id="activeItemId"
      @close="closeItemModal()"
      @archived="onItemArchived"
    />
  </div>
</template>

<script setup lang="ts">
import type { Item } from '~/types/api'

const { t, locale, setLocale } = useI18n()
const route = useRoute()
const router = useRouter()
const { mode: themeMode, setMode } = useTheme()
const supabaseUser = useSupabaseUser()
const client = useSupabaseClient()
const authStore = useAuthStore()
const itemStore = useItemStore()
const notifStore = useNotificationStore()
const { searchItems } = useSearch()

// 通知
const notifOpen = ref(false)

function formatNotifTime(isoStr: string) {
  const diff = Date.now() - new Date(isoStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return t('notif.justNow')
  if (mins < 60) return t('notif.minutesAgo', { n: mins })
  const hours = Math.floor(mins / 60)
  if (hours < 24) return t('notif.hoursAgo', { n: hours })
  return t('notif.daysAgo', { n: Math.floor(hours / 24) })
}

const menuOpen = ref(false)
const menuPanel = ref<'main' | 'appearance' | 'language'>('main')

// 搜尋
const searchQuery = ref('')
const searchResults = ref<Item[]>([])
const searchLoading = ref(false)
const searchDone = ref(false)
let searchTimer: ReturnType<typeof setTimeout> | null = null

const searchOpen = computed(() => searchQuery.value.trim().length > 0)

watch(searchQuery, (q) => {
  if (searchTimer) clearTimeout(searchTimer)
  if (!q.trim()) {
    searchResults.value = []
    searchLoading.value = false
    searchDone.value = false
    return
  }
  searchLoading.value = true
  searchDone.value = false
  searchTimer = setTimeout(async () => {
    try {
      searchResults.value = await searchItems(q)
    } finally {
      searchLoading.value = false
      searchDone.value = true
    }
  }, 400)
})

function closeSearch() {
  searchQuery.value = ''
  searchResults.value = []
  searchDone.value = false
  searchLoading.value = false
}

// 手機版搜尋 modal
const mobileSearchOpen = ref(false)
const mobileSearchInput = ref<HTMLInputElement | null>(null)

function closeMobileSearch() {
  mobileSearchOpen.value = false
  closeSearch()
}

watch(mobileSearchOpen, (val) => {
  if (val) nextTick(() => mobileSearchInput.value?.focus())
})

// Item detail modal
const { activeItemId, open: openItemModal, close: closeItemModal } = useItemModal()

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

function searchSourceLabel(url: string) {
  if (/youtu/.test(url)) return 'YouTube'
  if (/instagram\.com/.test(url)) return 'Instagram'
  return 'Article'
}

// 新增 modal
const addOpen = ref(false)
const addUrl = ref('')
const addSaving = ref(false)
const addError = ref('')
const addInput = ref<HTMLInputElement | null>(null)
const addProcessingItemId = ref<string | null>(null)
const processingStep = ref(0)
const STEP_DELAYS = [2000, 5000, 8000]
let stepTimer: ReturnType<typeof setTimeout> | null = null

function startStepTimer() {
  processingStep.value = 0
  let idx = 0
  const advance = () => {
    if (idx < STEP_DELAYS.length) {
      stepTimer = setTimeout(() => {
        processingStep.value = idx + 1
        idx++
        advance()
      }, STEP_DELAYS[idx])
    }
  }
  advance()
}

function clearStepTimer() {
  if (stepTimer) { clearTimeout(stepTimer); stepTimer = null }
}

watch(addOpen, (val) => {
  if (val) nextTick(() => addInput.value?.focus())
  else {
    addUrl.value = ''
    addError.value = ''
    addProcessingItemId.value = null
    clearStepTimer()
    processingStep.value = 0
  }
})

watch(() => itemStore.recentlyProcessed, (itemId) => {
  if (itemId && itemId === addProcessingItemId.value) {
    processingStep.value = 4
    clearStepTimer()
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
  addSaving.value = true
  addError.value = ''
  try {
    const item = await itemStore.add({ url })
    addUrl.value = ''
    addProcessingItemId.value = item.id
    startStepTimer()
    if (!route.path.startsWith('/app') || route.path === '/app/archive') {
      navigateTo('/app')
    }
  } catch {
    addError.value = t('add.error')
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
  closeItemModal()
  closeSearch()
  mobileSearchOpen.value = false
})

watch(supabaseUser, (user) => {
  if (user) notifStore.startPolling()
  else notifStore.stopPolling()
}, { immediate: true })

onUnmounted(() => notifStore.stopPolling())
</script>
