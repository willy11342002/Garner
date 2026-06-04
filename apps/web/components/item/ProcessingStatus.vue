<template>
  <div class="proc-panel">
    <div class="proc-panel__header">
      <span class="proc-panel__dot proc-panel__dot--pulse"></span>
      AI 正在處理...
    </div>
    <ul class="proc-panel__steps">
      <li
        v-for="step in steps"
        :key="step.stage"
        class="proc-step"
        :class="{
          'proc-step--done':    stepState(step.stage) === 'done',
          'proc-step--active':  stepState(step.stage) === 'active',
          'proc-step--pending': stepState(step.stage) === 'pending',
        }"
      >
        <span class="proc-step__icon">
          <span v-if="stepState(step.stage) === 'done'">✓</span>
          <span v-else-if="stepState(step.stage) === 'active'" class="proc-spinner"></span>
          <span v-else>·</span>
        </span>
        <span class="proc-step__label">{{ step.label }}</span>
      </li>
    </ul>
    <p class="proc-panel__footer">處理完成後頁面會自動更新</p>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  itemId: string
  sourceType: string | null | undefined
}>()

const itemStore = useItemStore()

const STEPS: Record<string, Array<{ stage: string; label: string }>> = {
  youtube: [
    { stage: 'fetching_info',    label: '獲取影片資訊' },
    { stage: 'fetching_content', label: '讀取內容（字幕／語音辨識）' },
    { stage: 'analyzing',        label: 'AI 分析摘要與標籤' },
    { stage: 'embedding',        label: '建立語意索引' },
  ],
  default: [
    { stage: 'analyzing', label: 'AI 分析摘要與標籤' },
    { stage: 'embedding', label: '建立語意索引' },
  ],
}

const steps = computed(() =>
  STEPS[props.sourceType ?? ''] ?? STEPS.default
)

const ORDER = ['fetching_info', 'fetching_content', 'analyzing', 'embedding']

function stepState(stage: string): 'done' | 'active' | 'pending' {
  const current = itemStore.processingStages.get(props.itemId) ?? ''
  const currentIdx = ORDER.indexOf(current)
  const stageIdx = ORDER.indexOf(stage)
  if (stageIdx < 0 || currentIdx < 0) return stage === current ? 'active' : 'pending'
  if (stageIdx < currentIdx) return 'done'
  if (stageIdx === currentIdx) return 'active'
  return 'pending'
}
</script>

<style scoped>
.proc-panel {
  background: var(--surface2, #1e1e2e);
  border: 1px solid var(--border, #333);
  border-radius: 10px;
  padding: 12px 14px;
  min-width: 200px;
  font-size: 13px;
  color: var(--text, #e0e0e0);
}

.proc-panel__header {
  display: flex;
  align-items: center;
  gap: 7px;
  font-weight: 600;
  margin-bottom: 10px;
}

.proc-panel__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent, #6ee7b7);
  flex-shrink: 0;
}

.proc-panel__dot--pulse {
  animation: pulse 1.6s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.4; }
}

.proc-panel__steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.proc-step {
  display: flex;
  align-items: center;
  gap: 8px;
}

.proc-step__icon {
  width: 16px;
  text-align: center;
  flex-shrink: 0;
  font-size: 13px;
}

.proc-step--done   .proc-step__icon { color: var(--accent, #6ee7b7); }
.proc-step--active .proc-step__icon { color: var(--text, #e0e0e0); }
.proc-step--pending .proc-step__label { color: var(--text3, #666); }

.proc-spinner {
  display: inline-block;
  width: 11px;
  height: 11px;
  border: 2px solid var(--border, #444);
  border-top-color: var(--text, #e0e0e0);
  border-radius: 50%;
  animation: spin 0.75s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.proc-panel__footer {
  margin: 10px 0 0;
  font-size: 11px;
  color: var(--text3, #666);
}
</style>
