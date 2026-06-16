<template>
  <div class="chat-trip-card">
    <div class="chat-trip-card__icon">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 10c0 7-9 12-9 12s-9-5-9-12a9 9 0 0 1 18 0z"/>
        <circle cx="12" cy="10" r="3"/>
      </svg>
    </div>
    <div class="chat-trip-card__body">
      <span class="chat-trip-card__eyebrow">AI 行程</span>
      <span class="chat-trip-card__title">{{ draft.title }}</span>
      <p v-if="draft.summary" class="chat-trip-card__summary">{{ draft.summary }}</p>
      <span v-if="draft.item_count" class="chat-trip-card__meta">{{ draft.item_count }} 個行程點</span>
    </div>
    <div class="chat-trip-card__actions">
      <button class="btn btn--accent chat-trip-card__btn" @click="openTrip">開啟行程</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { TripDraft } from '~/types/api'

const props = defineProps<{ draft: TripDraft }>()

function openTrip() {
  navigateTo(`/app/trips?open=${props.draft.id}`)
}
</script>

<style scoped>
.chat-trip-card {
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
  .chat-trip-card { width: 92%; max-width: 92%; }
}

.chat-trip-card__icon {
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
.chat-trip-card__icon svg { width: 16px; height: 16px; }

.chat-trip-card__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.chat-trip-card__eyebrow {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--accent);
  letter-spacing: .06em;
  text-transform: uppercase;
}

.chat-trip-card__title {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chat-trip-card__summary {
  font-size: 12px;
  color: var(--text-dim);
  line-height: 1.5;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.chat-trip-card__meta {
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--text-dim);
}

.chat-trip-card__actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-shrink: 0;
}

.chat-trip-card__btn {
  font-size: 12px;
  padding: 5px 12px;
  height: auto;
  white-space: nowrap;
}
</style>
