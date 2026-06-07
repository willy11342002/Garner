<script setup lang="ts">
const props = defineProps<{ searchEnabled: boolean }>()

const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const VIEWS = computed(() => [
  { key: 'tags', label: t('home.view_tags') },
  { key: 'map', label: t('home.view_map') },
  { key: 'semantic', label: t('home.view_semantic'), badge: !props.searchEnabled ? 'PRO' : undefined, locked: !props.searchEnabled },
])

const currentView = computed(() => (route.query.view as string) || 'tags')

function handleTabClick(view: { key: string; locked?: boolean }) {
  if (view.locked) {
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
        'view-tab--locked': v.locked,
      }"
      @click="handleTabClick(v)"
    >
      {{ v.label }}
      <span v-if="v.badge" class="view-tab__badge">{{ v.badge }}</span>
    </button>
  </nav>
</template>
