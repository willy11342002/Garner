<script setup lang="ts">
definePageMeta({
  middleware: [
    function (to) {
      return navigateTo({ path: '/app', query: { item: to.params.slug as string } }, { replace: true })
    }
  ]
})
</script>

<template></template>
