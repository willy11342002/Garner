<template>
  <div>
    <nav class="nav">
      <NuxtLink :to="isLoggedIn ? '/app' : '/'" class="nav__logo">Vela</NuxtLink>
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
        <template v-if="isLoggedIn">
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
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
              <path d="M12 5v14M5 12h14"/>
            </svg>
            <span>{{ t('nav.add') }}</span>
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
        </template>
        <template v-else>
          <button class="nav__icon-btn" :title="t('nav.toggleTheme')" @click="toggleTheme">
            <svg v-if="isDark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
              <circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>
            </svg>
          </button>
          <button class="nav__icon-btn nav__lang-btn" :title="t('nav.toggleLanguage')" @click="toggleLocale">
            {{ locale === 'zh-TW' ? '中' : 'EN' }}
          </button>
          <NuxtLink to="/login" class="nav__add"><span>{{ t('nav.login') }}</span></NuxtLink>
        </template>
      </div>
    </nav>

    <!-- 點選外部關閉選單 -->
    <div v-if="menuOpen" class="nav__backdrop" @click="menuOpen = false" />
    <!-- 點選外部關閉搜尋 -->
    <div v-if="searchOpen" class="nav__backdrop" @click="closeSearch" />
    <!-- 點選外部關閉通知 -->
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
          <!-- Processing state -->
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
          <!-- Input state -->
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

    <slot />

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
const { isDark, mode: themeMode, setMode } = useTheme()
const supabaseUser = useSupabaseUser()
const client = useSupabaseClient()
const authStore = useAuthStore()
const itemStore = useItemStore()
const notifStore = useNotificationStore()
const { searchItems } = useSearch()

// 通知
const notifOpen = ref(false)
const notifEl = ref<HTMLElement | null>(null)

function formatNotifTime(isoStr: string) {
  const diff = Date.now() - new Date(isoStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return t('notif.justNow')
  if (mins < 60) return t('notif.minutesAgo', { n: mins })
  const hours = Math.floor(mins / 60)
  if (hours < 24) return t('notif.hoursAgo', { n: hours })
  return t('notif.daysAgo', { n: Math.floor(hours / 24) })
}


const isLoggedIn = computed(() => !!supabaseUser.value)
const menuOpen = ref(false)

function toggleTheme() {
  setMode(isDark.value ? 'light' : 'dark')
}

function toggleLocale() {
  setLocale(locale.value === 'zh-TW' ? 'en' : 'zh-TW')
}
const menuPanel = ref<'main' | 'appearance' | 'language'>('main')

// 搜尋
const searchEl = ref<HTMLElement | null>(null)
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

// inline item detail modal (搜尋 + 通知共用)
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

function goToSearchItem(id: string) {
  closeSearch()
  router.push(`/app/item/${id}`)
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
const STEP_DELAYS = [2000, 5000, 8000] // ms to advance from step 0→1, 1→2, 2→3; step 3 stays until done
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
    processingStep.value = 4 // all done
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

// 路由切換時關閉選單、搜尋、通知
watch(() => route.path, () => {
  menuOpen.value = false
  notifOpen.value = false
  closeItemModal()
  closeSearch()
  mobileSearchOpen.value = false
})

// 通知輪詢
watch(supabaseUser, (user) => {
  if (user) notifStore.startPolling()
  else notifStore.stopPolling()
}, { immediate: true })

onUnmounted(() => notifStore.stopPolling())
</script>

<style>
.nav__tab-group {
  position: relative;
  display: inline-flex;
}

.nav__tab-group:hover .nav__explore-menu {
  pointer-events: auto;
}

.nav__tab-group:hover .nav__explore-menu-inner {
  opacity: 1;
  transform: translateY(0);
}

.nav__explore-menu {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  padding-top: 6px;
  width: 160px;
  z-index: 200;
  pointer-events: none;
}

.nav__explore-menu-inner {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  padding: 4px;
  opacity: 0;
  transform: translateY(-4px);
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.nav__explore-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  font-size: 13px;
  font-family: var(--font-ui);
  color: var(--text-mid);
  border-radius: 7px;
  transition: background 0.1s, color 0.1s;
}

.nav__explore-item:hover {
  background: var(--bg);
  color: var(--text);
}

.nav__explore-item--active {
  color: var(--accent);
}

.nav__explore-item svg {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.nav__user {
  position: relative;
}

.nav__avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  overflow: hidden;
  border: 1.5px solid var(--border);
  background: var(--surface);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  font-family: var(--font-mono);
  color: var(--text);
  padding: 0;
  transition: border-color 0.15s;
}

.nav__avatar:hover {
  border-color: var(--text-mid);
}

.nav__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.nav__menu {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  width: 220px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  z-index: 200;
  overflow: hidden;
  padding: 6px;
}

.nav__menu-header {
  padding: 10px 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav__menu-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nav__menu-email {
  font-size: 11px;
  color: var(--text-dim);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nav__menu-divider {
  height: 1px;
  background: var(--border);
  margin: 4px 0;
}

.nav__menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 12px;
  font-size: 13px;
  font-family: var(--font-ui);
  color: var(--text);
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  text-align: left;
  transition: background 0.12s;
}

.nav__menu-item:hover {
  background: var(--bg);
}

.nav__menu-item svg {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
  color: var(--text-mid);
}

.nav__menu-item--danger {
  color: #e85555;
}

.nav__menu-item--danger svg {
  color: #e85555;
}

.nav__menu-item--chevron {
  justify-content: flex-start;
}

.nav__menu-chevron {
  width: 14px !important;
  height: 14px !important;
  margin-left: auto;
  color: var(--text-dim) !important;
  flex-shrink: 0;
}

.nav__menu-back {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 600;
  font-family: var(--font-ui);
  color: var(--text);
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
}

.nav__menu-back svg {
  width: 15px;
  height: 15px;
  color: var(--text-mid);
  flex-shrink: 0;
}

.nav__menu-back:hover {
  color: var(--text);
}

.nav__menu-item--check {
  gap: 10px;
}

.nav__check-icon {
  width: 14px !important;
  height: 14px !important;
  color: var(--accent) !important;
  flex-shrink: 0;
}

.nav__check-placeholder {
  display: inline-block;
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.nav__menu-item--checked {
  color: var(--accent);
}

.nav__icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-mid);
  cursor: pointer;
  transition: background 0.12s, color 0.12s, border-color 0.12s;
  flex-shrink: 0;
}

.nav__icon-btn:hover {
  background: var(--surface);
  color: var(--text);
  border-color: var(--text-dim);
}

.nav__icon-btn svg {
  width: 15px;
  height: 15px;
}

.nav__lang-btn {
  font-size: 11px;
  font-weight: 600;
  font-family: var(--font-mono);
  letter-spacing: 0.02em;
}

.nav__backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
}

/* 新增 URL modal */
.add-overlay {
  position: fixed;
  inset: 0;
  z-index: 300;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.add-modal {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
  width: 100%;
  max-width: 540px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: 0 16px 48px rgba(0,0,0,0.18);
}

.add-modal__label {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 0;
}

.add-modal__row {
  display: flex;
  gap: 8px;
}

.add-modal__input {
  flex: 1;
  background: var(--bg);
  border: 1px solid var(--border2);
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 13px;
  color: var(--text);
  font-family: var(--font-ui);
  outline: none;
  transition: border-color .15s ease;
  min-width: 0;
}
.add-modal__input:focus { border-color: var(--accent-bdr); }
.add-modal__input::placeholder { color: var(--text-dim); }
.add-modal__input:disabled { opacity: 0.5; }

.add-modal__error {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 11.5px;
  color: var(--danger);
}

.add-modal__processing {
  display: flex;
  align-items: center;
  gap: 10px;
}

.add-modal__processing-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 6px var(--accent);
  flex-shrink: 0;
  animation: pulse 1.5s ease-in-out infinite;
}

.add-modal__processing-text {
  margin: 0;
  font-family: var(--font-ui);
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
}

.add-modal__hint {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 11.5px;
  color: var(--text-dim);
}

.add-modal__row--end {
  justify-content: flex-end;
}

.add-modal__steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.add-modal__step {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: var(--font-ui);
  font-size: 13px;
  color: var(--text-dim);
  transition: color 0.2s ease;
}

.add-modal__step--active {
  color: var(--text);
  font-weight: 500;
}

.add-modal__step--done {
  color: var(--text-dim);
}

.add-modal__step-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.add-modal__step-icon svg {
  width: 14px;
  height: 14px;
  stroke: var(--accent);
}

.add-modal__step-spinner {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid var(--border2);
  border-top-color: var(--accent);
  animation: spin 0.7s linear infinite;
}

.add-modal__step-idle {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--border2);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.modal-enter-active, .modal-leave-active {
  transition: opacity 0.15s ease;
}
.modal-enter-active .add-modal, .modal-leave-active .add-modal {
  transition: transform 0.15s ease, opacity 0.15s ease;
}
.modal-enter-from, .modal-leave-to {
  opacity: 0;
}
.modal-enter-from .add-modal, .modal-leave-to .add-modal {
  transform: scale(0.96);
  opacity: 0;
}

.menu-enter-active,
.menu-leave-active {
  transition: opacity 0.12s, transform 0.12s;
}

.menu-enter-from,
.menu-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* 通知鈴鐺 */
.nav__notif {
  position: relative;
}

.nav__notif-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-mid);
  cursor: pointer;
  transition: background 0.12s, color 0.12s, border-color 0.12s;
  flex-shrink: 0;
}

.nav__notif-btn:hover {
  background: var(--surface);
  color: var(--text);
  border-color: var(--text-dim);
}

.nav__notif-btn svg {
  width: 15px;
  height: 15px;
}

.nav__notif-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 16px;
  height: 16px;
  padding: 0 3px;
  border-radius: 8px;
  background: var(--accent);
  color: #fff;
  font-size: 9px;
  font-weight: 700;
  font-family: var(--font-mono);
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.nav__notif-panel {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  width: 300px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  z-index: 200;
  overflow: hidden;
}

.nav__notif-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px 8px;
  font-size: 12px;
  font-weight: 600;
  font-family: var(--font-ui);
  color: var(--text);
  border-bottom: 1px solid var(--border);
}

.nav__notif-readall {
  font-size: 11px;
  font-family: var(--font-ui);
  color: var(--accent);
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
}

.nav__notif-readall:hover {
  opacity: 0.8;
}

.nav__notif-list {
  max-height: 320px;
  overflow-y: auto;
  padding: 4px;
}

.nav__notif-empty {
  padding: 20px 14px;
  text-align: center;
  font-size: 12px;
  color: var(--text-dim);
  font-family: var(--font-ui);
}

.nav__notif-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
  transition: background 0.1s;
}

.nav__notif-item:hover {
  background: var(--bg);
}

.nav__notif-item--unread {
  background: color-mix(in srgb, var(--accent) 6%, transparent);
}

.nav__notif-item--unread:hover {
  background: color-mix(in srgb, var(--accent) 10%, transparent);
}

.nav__notif-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 4px;
  background: transparent;
}

.nav__notif-dot--visible {
  background: var(--accent);
}

.nav__notif-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.nav__notif-text {
  font-size: 12.5px;
  font-family: var(--font-ui);
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 220px;
}

.nav__notif-time {
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--text-dim);
}

@media (max-width: 720px) {
  .nav__notif-panel {
    position: fixed;
    top: 56px;
    right: 12px;
    left: auto;
    width: calc(100vw - 24px);
    max-width: 320px;
  }
}

/* 手機版搜尋 icon button */
.nav__search-btn {
  display: none;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 50%;
  color: var(--text-mid);
  cursor: pointer;
  transition: background .12s, color .12s, border-color .12s;
}
.nav__search-btn:hover { background: var(--surface); color: var(--text); border-color: var(--text-dim); }

@media (max-width: 768px) {
  .nav__search-btn { display: flex; }
}

/* 搜尋 modal 內部樣式 */
.search-modal { padding: 16px; max-width: 480px; }

.search-modal__input-row {
  position: relative;
  display: flex;
  align-items: center;
}
.search-modal__icon {
  position: absolute;
  left: 10px;
  color: var(--text-dim);
  flex-shrink: 0;
}
.search-modal__input { padding-left: 34px !important; }

.search-modal__state {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-dim);
  padding: 8px 4px;
}

.search-modal__item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px;
  border-radius: 8px;
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
  transition: background .12s ease;
}
.search-modal__item:hover { background: var(--surface2); }

.search-modal__thumb {
  width: 44px;
  height: 44px;
  border-radius: 6px;
  overflow: hidden;
  flex-shrink: 0;
  background: var(--surface2);
}
.search-modal__thumb img { width: 100%; height: 100%; object-fit: cover; }

.search-modal__info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.search-modal__title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.search-modal__meta {
  font-size: 11px;
  color: var(--text-dim);
}
</style>
