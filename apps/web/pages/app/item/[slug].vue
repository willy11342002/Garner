<script setup lang="ts">
const route = useRoute()
const router = useRouter()
const slug = route.params.slug as string

const itemStore = useItemStore()
useHead(computed(() => {
  const item = itemStore.items.find(i => i.id === slug)
  return { title: item?.title ? `Vela — ${item.title}` : 'Vela' }
}))

function handleClose() {
  if (window.history.length > 1) router.back()
  else router.push('/app')
}
</script>

<template>
  <div>
    <div class="item-page-topbar">
      <button class="item-page-back" @click="handleClose">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M19 12H5M12 5l-7 7 7 7"/>
        </svg>
        返回
      </button>
    </div>
    <ItemDetailModal :itemId="slug" :page="true" @close="handleClose" @archived="handleClose" />
  </div>
</template>

<style scoped>
.item-page-topbar {
  max-width: 960px;
  margin: 0 auto;
  padding: 20px 24px 0;
}

.item-page-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: 1px solid var(--border2);
  border-radius: 8px;
  color: var(--text-mid);
  font-size: 13px;
  padding: 6px 12px;
  cursor: pointer;
  transition: color .15s, border-color .15s;
}
.item-page-back:hover {
  color: var(--text);
  border-color: var(--border);
}
</style>
