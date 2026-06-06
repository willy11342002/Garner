<script setup lang="ts">
const props = defineProps<{ itemId: string; sourceType: string }>()

const itemStore = useItemStore()
const stage = computed(() => itemStore.processingStages.get(props.itemId) ?? 'fetching')

const LABELS: Record<string, string> = {
  fetching:          '準備中...',
  fetching_info:     '獲取影片資訊',
  fetching_content:  '讀取內容',
  analyzing:         'AI 分析中',
  embedding:         '建立語意索引',
  failed:            '處理失敗',
  timeout:           '處理逾時',
  error:             '發生錯誤',
}

const label = computed(() => LABELS[stage.value] ?? stage.value)
const isFailed = computed(() => ['failed', 'timeout', 'error'].includes(stage.value))
</script>

<template>
  <div class="proc-panel">
    <span class="proc-panel__dot" :class="{ 'proc-panel__dot--err': isFailed }" />
    <span class="proc-panel__text">{{ label }}</span>
  </div>
</template>

<style scoped>
.proc-panel {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--surface);
  border: 1px solid var(--bdr);
  border-radius: 8px;
  padding: 6px 10px;
  white-space: nowrap;
  font-size: 11px;
  color: var(--text-2);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}
.proc-panel__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
  animation: proc-pulse 1.5s ease-in-out infinite;
  flex-shrink: 0;
}
.proc-panel__dot--err {
  background: var(--danger, #e55);
  animation: none;
}
@keyframes proc-pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.35; }
}
</style>
