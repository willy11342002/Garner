<template>
  <BaseFab
    :open-title="t('fab.close')"
    :close-title="t('fab.open')"
    :panel-width="400"
    :panel-height="560"
  >
    <template #badge>
      <span v-if="chainItems.length > 0" class="hcf-badge">{{ chainItems.length }}</span>
    </template>
    <template #panel="{ close }">
      <HomeChatPanel @close="close" />
    </template>
  </BaseFab>
</template>

<script setup lang="ts">
const { t } = useI18n()
const { chainItems } = useChain()
</script>

<style scoped>
.hcf-badge {
  position: absolute;
  top: -4px; right: -4px;
  min-width: 18px; height: 18px; border-radius: 9px;
  background: var(--danger); color: #fff;
  font-family: var(--font-mono); font-size: 10px; font-weight: 600;
  display: flex; align-items: center; justify-content: center;
  padding: 0 4px; border: 2px solid var(--bg);
}
</style>
