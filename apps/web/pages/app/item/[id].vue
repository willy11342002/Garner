<script setup lang="ts">
const route = useRoute()
const router = useRouter()
const id = route.params.id as string

const itemStore = useItemStore()
useHead(computed(() => {
  const item = itemStore.items.find(i => i.id === id)
  return { title: item?.title ? `Vela — ${item.title}` : 'Vela' }
}))
</script>

<template>
  <ItemDetailModal :itemId="id" @close="router.back()" />
</template>
