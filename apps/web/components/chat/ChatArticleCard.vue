<template>
  <div class="chat-article-card">
    <div class="chat-article-card__icon">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="16" y1="13" x2="8" y2="13"/>
        <line x1="16" y1="17" x2="8" y2="17"/>
      </svg>
    </div>
    <div class="chat-article-card__body">
      <span class="chat-article-card__eyebrow">草稿文章</span>
      <span class="chat-article-card__title">{{ draft.title }}</span>
      <p class="chat-article-card__summary">{{ draft.summary }}</p>
    </div>
    <div class="chat-article-card__actions">
      <button class="btn chat-article-card__btn" @click="$emit('preview')">預覽</button>
      <button class="btn btn--accent chat-article-card__btn" @click="openInEditor">在編輯器開啟</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ArticleDraft } from '~/types/api'

const props = defineProps<{ draft: ArticleDraft }>()
defineEmits<{ preview: [] }>()

const router = useRouter()

function openInEditor() {
  router.push(`/app/write/${props.draft.id}`)
}
</script>

<style>
.chat-article-card {
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
  .chat-article-card { width: 92%; max-width: 92%; }
}

.chat-article-card__icon {
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
.chat-article-card__icon svg { width: 16px; height: 16px; }

.chat-article-card__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.chat-article-card__eyebrow {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--accent);
  letter-spacing: .06em;
  text-transform: uppercase;
}

.chat-article-card__title {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chat-article-card__summary {
  font-size: 12px;
  color: var(--text-dim);
  line-height: 1.5;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.chat-article-card__actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-shrink: 0;
}

.chat-article-card__btn {
  font-size: 12px;
  padding: 5px 12px;
  height: auto;
  white-space: nowrap;
}
</style>
