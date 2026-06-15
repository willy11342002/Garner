<template>
  <div class="chat-report-card">
    <div class="chat-report-card__icon">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="16" y1="13" x2="8" y2="13"/>
        <line x1="16" y1="17" x2="8" y2="17"/>
      </svg>
    </div>
    <div class="chat-report-card__body">
      <span class="chat-report-card__eyebrow">AI 報告</span>
      <span class="chat-report-card__title">{{ draft.title }}</span>
      <p v-if="draft.summary" class="chat-report-card__summary">{{ draft.summary }}</p>
    </div>
    <div class="chat-report-card__actions">
      <button class="btn btn--accent chat-report-card__btn" @click="openReport">開啟報告</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ReportDraft } from '~/types/api'

const props = defineProps<{ draft: ReportDraft }>()

function openReport() {
  navigateTo(`/app/reports?open=${props.draft.id}`)
}
</script>

<style scoped>
.chat-report-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-top: 10px;
  padding: 14px 16px;
  background: var(--surface2);
  border: 1px solid var(--border2);
  border-left: 3px solid var(--accent);
  border-radius: 10px;
  width: 480px;
  max-width: 480px;
}

@media (max-width: 768px) {
  .chat-report-card { width: 92%; max-width: 92%; }
}

.chat-report-card__icon {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--accent-dim);
  border: 1px solid var(--accent-bdr);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent);
}
.chat-report-card__icon svg { width: 16px; height: 16px; }

.chat-report-card__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.chat-report-card__eyebrow {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--accent);
  letter-spacing: .06em;
  text-transform: uppercase;
}

.chat-report-card__title {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chat-report-card__summary {
  font-size: 12px;
  color: var(--text-dim);
  line-height: 1.5;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.chat-report-card__actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-shrink: 0;
}

.chat-report-card__btn {
  font-size: 12px;
  padding: 5px 12px;
  height: auto;
  white-space: nowrap;
}
</style>
