<script setup lang="ts">
const route = useRoute()
const router = useRouter()
const id = route.params.id as string
</script>

<template>
  <ItemDetailModal :itemId="id" @close="router.back()" />
</template>
