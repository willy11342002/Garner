<template>
  <div>
    <nav class="nav">
      <NuxtLink to="/app" class="nav__logo">Vela</NuxtLink>
      <div class="nav__tabs">
        <NuxtLink
          to="/app/explore"
          class="nav__tab"
          :class="{ 'nav__tab--active': route.path.startsWith('/app/explore') }"
        >探索</NuxtLink>
        <NuxtLink
          to="/app/archive"
          class="nav__tab"
          :class="{ 'nav__tab--active': route.path.startsWith('/app/archive') }"
        >封存</NuxtLink>
      </div>
      <div class="nav__right">
        <div class="nav__search">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="7"/>
            <path d="m20 20-3.5-3.5"/>
          </svg>
          <input type="text" :placeholder="isPublicPage ? '搜尋公開集合...' : '搜尋你的知識庫...'">
        </div>
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
        <template v-if="isPublicPage">
          <NuxtLink to="/" class="nav__add"><span>登入 / 免費試用</span></NuxtLink>
        </template>
        <template v-else>
          <NuxtLink to="/app/share" class="nav__add">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
              <path d="M12 5v14M5 12h14"/>
            </svg>
            <span>新增</span>
          </NuxtLink>
          <button class="nav__avatar" title="使用者">CL</button>
        </template>
      </div>
    </nav>
    <slot />
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const { isDark, toggle } = useTheme()

const isPublicPage = computed(() =>
  route.path.startsWith('/share/') || route.path === '/pricing'
)
</script>
