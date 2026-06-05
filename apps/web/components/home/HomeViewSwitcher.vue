<script setup lang="ts">
const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const VIEWS = computed(() => [
  { key: 'tags', label: t('home.view_tags') },
  { key: 'map', label: t('home.view_map') },
])

const currentView = computed(() => (route.query.view as string) || 'tags')

function setView(view: string) {
  router.replace({ query: { ...route.query, view } })
}
</script>

<template>
  <nav class="view-switcher">
    <button
      v-for="v in VIEWS"
      :key="v.key"
      class="view-tab"
      :class="{ 'view-tab--active': currentView === v.key }"
      @click="setView(v.key)"
    >{{ v.label }}</button>
  </nav>
</template>
