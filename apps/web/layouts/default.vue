<template>
  <div>
    <nav class="nav">
      <NuxtLink :to="isLoggedIn ? '/app' : '/'" class="nav__logo">Vela</NuxtLink>
      <div class="nav__tabs">
        <NuxtLink
          to="/app/explore"
          class="nav__tab"
          :class="{ 'nav__tab--active': route.path.startsWith('/app/explore') }"
        >{{ t('nav.explore') }}</NuxtLink>
        <template v-if="isLoggedIn">
          <NuxtLink
            to="/app/archive"
            class="nav__tab"
            :class="{ 'nav__tab--active': route.path.startsWith('/app/archive') }"
          >{{ t('nav.archive') }}</NuxtLink>
        </template>
      </div>
      <div class="nav__right">
        <template v-if="isLoggedIn">
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
                    @click="goToSearchItem(item.id)"
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
        </template>
        <button class="nav__theme" @click="toggle" aria-label="Toggle theme">
          <svg viewBox="0 0 24 24">
            <template v-if="!isDark">
              <circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" stroke-width="1.6"/>
              <path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
            </template>
            <template v-else>
              <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
            </template>
          </svg>
        </button>
        <template v-if="isLoggedIn">
          <button class="nav__add" @click="addOpen = true">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
              <path d="M12 5v14M5 12h14"/>
            </svg>
            <span>{{ t('nav.add') }}</span>
          </button>

          <!-- 使用者頭像 + 下拉選單 -->
          <div class="nav__user">
            <button class="nav__avatar" @click.stop="menuOpen = !menuOpen">
              <img v-if="avatarUrl" :src="avatarUrl" :alt="displayName" referrerpolicy="no-referrer">
              <span v-else>{{ initials }}</span>
            </button>

            <Transition name="menu">
              <div v-if="menuOpen" class="nav__menu">
                <div class="nav__menu-header">
                  <span class="nav__menu-name">{{ displayName }}</span>
                  <span class="nav__menu-email">{{ supabaseUser?.email }}</span>
                </div>
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
                <button class="nav__menu-item nav__menu-item--danger" @click="signOut">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></svg>
                  {{ t('nav.signOut') }}
                </button>
              </div>
            </Transition>
          </div>
        </template>
        <template v-else>
          <NuxtLink to="/login" class="nav__add"><span>{{ t('nav.login') }}</span></NuxtLink>
        </template>
      </div>
    </nav>

    <!-- 點選外部關閉選單 -->
    <div v-if="menuOpen" class="nav__backdrop" @click="menuOpen = false" />
    <!-- 點選外部關閉搜尋 -->
    <div v-if="searchOpen" class="nav__backdrop" @click="closeSearch" />

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
            <p class="add-modal__hint">{{ t('add.processingHint') }}</p>
            <div class="add-modal__row add-modal__row--end">
              <button class="btn btn--ghost" @click="closeAdd">{{ t('add.close') }}</button>
            </div>
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
  </div>
</template>

<script setup lang="ts">
import type { Item } from '~/types/api'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { isDark, toggle } = useTheme()
const supabaseUser = useSupabaseUser()
const client = useSupabaseClient()
const authStore = useAuthStore()
const itemStore = useItemStore()
const { searchItems } = useSearch()

const isLoggedIn = computed(() => !!supabaseUser.value)
const menuOpen = ref(false)

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

watch(addOpen, (val) => {
  if (val) nextTick(() => addInput.value?.focus())
  else {
    addUrl.value = ''
    addError.value = ''
    addProcessingItemId.value = null
  }
})

watch(() => itemStore.recentlyProcessed, (itemId) => {
  if (itemId && itemId === addProcessingItemId.value) {
    addProcessingItemId.value = null
    addOpen.value = false
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
  supabaseUser.value?.user_metadata?.full_name
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

// 路由切換時關閉選單與搜尋
watch(() => route.path, () => {
  menuOpen.value = false
  closeSearch()
})
</script>

<style>
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
</style>
