<script setup lang="ts">
const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const authStore = useAuthStore()

const isPro = computed(() => authStore.user?.plan === 'pro')

const VIEWS = computed(() => [
  { key: 'tags', label: t('home.view_tags') },
  { key: 'map', label: t('home.view_map') },
  { key: 'semantic', label: t('home.view_semantic'), badge: 'PRO', proOnly: true },
])

const currentView = computed(() => (route.query.view as string) || 'tags')

function handleTabClick(view: { key: string; proOnly?: boolean }) {
  if (view.proOnly && !isPro.value) {
    router.push('/pricing')
    return
  }
  router.replace({ query: { ...route.query, view: view.key } })
}
</script>

<template>
  <nav class="view-switcher">
    <button
      v-for="v in VIEWS"
      :key="v.key"
      class="view-tab"
      :class="{
        'view-tab--active': currentView === v.key,
        'view-tab--locked': v.proOnly && !isPro,
      }"
      @click="handleTabClick(v)"
    >
      {{ v.label }}
      <span v-if="v.badge" class="view-tab__badge">{{ v.badge }}</span>
    </button>
  </nav>
</template>
