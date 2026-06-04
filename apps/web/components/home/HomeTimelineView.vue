<script setup lang="ts">
import type { Tag } from '~/types/api'

defineProps<{
  itemTagsMap: Record<string, Tag[]>
}>()
</script>

<template>
  <div class="view-placeholder">
    <span class="view-placeholder__icon">◷</span>
    <p class="view-placeholder__text">時間軸檢視開發中</p>
  </div>
</template>
