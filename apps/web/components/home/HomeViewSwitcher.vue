<script setup lang="ts">
const route = useRoute()
const router = useRouter()

const VIEWS = [
  { key: 'tags', label: '標籤' },
  { key: 'timeline', label: '時間軸' },
  { key: 'map', label: '地圖' },
]

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
