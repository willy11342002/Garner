<template>
  <div>
    <nav class="nav">
      <NuxtLink :to="isLoggedIn ? '/app' : '/'" class="nav__logo">Vela</NuxtLink>
      <div class="nav__tabs">
        <NuxtLink
          to="/app/explore"
          class="nav__tab"
          :class="{ 'nav__tab--active': route.path.startsWith('/app/explore') }"
        >探索</NuxtLink>
        <template v-if="isLoggedIn">
          <NuxtLink
            to="/app/archive"
            class="nav__tab"
            :class="{ 'nav__tab--active': route.path.startsWith('/app/archive') }"
          >封存</NuxtLink>
        </template>
      </div>
      <div class="nav__right">
        <template v-if="isLoggedIn">
          <div class="nav__search">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="11" cy="11" r="7"/>
              <path d="m20 20-3.5-3.5"/>
            </svg>
            <input type="text" placeholder="搜尋你的知識庫...">
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
          <NuxtLink to="/app/share" class="nav__add">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
              <path d="M12 5v14M5 12h14"/>
            </svg>
            <span>新增</span>
          </NuxtLink>

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
                  設置
                </button>
                <button class="nav__menu-item" @click="goTo('/app/security')">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                  安全性
                </button>
                <div class="nav__menu-divider" />
                <button class="nav__menu-item nav__menu-item--danger" @click="signOut">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></svg>
                  登出
                </button>
              </div>
            </Transition>
          </div>
        </template>
        <template v-else>
          <NuxtLink to="/login" class="nav__add"><span>登入 / 免費試用</span></NuxtLink>
        </template>
      </div>
    </nav>

    <!-- 點選外部關閉選單 -->
    <div v-if="menuOpen" class="nav__backdrop" @click="menuOpen = false" />

    <slot />
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const router = useRouter()
const { isDark, toggle } = useTheme()
const supabaseUser = useSupabaseUser()
const client = useSupabaseClient()
const authStore = useAuthStore()

const isLoggedIn = computed(() => !!supabaseUser.value)
const menuOpen = ref(false)

const avatarUrl = computed(() => supabaseUser.value?.user_metadata?.avatar_url ?? null)
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

// 路由切換時關閉選單
watch(() => route.path, () => { menuOpen.value = false })
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
