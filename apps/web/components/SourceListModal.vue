<template>
  <Transition name="slm-fade">
    <div v-if="open" class="slm-overlay" @click.self="emit('close')">
      <div class="slm">
        <div class="slm__head">
          <h3 class="slm__title">{{ title }}</h3>
          <button class="slm__close" @click="emit('close')">✕</button>
        </div>
        <div class="slm__list">
          <button
            v-for="s in sources"
            :key="s.id"
            class="slm__item"
            @click="emit('select', s.id)"
          >
            <img v-if="s.thumbnail_url" :src="s.thumbnail_url" :alt="s.title || ''" class="slm__thumb">
            <span v-else class="slm__thumb slm__thumb--ph">{{ sourceEmoji(s.source_type) }}</span>
            <span class="slm__name">{{ s.title || s.url || '來源' }}</span>
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
interface SourceLike {
  id: string
  title: string | null
  thumbnail_url: string | null
  source_type: string | null
  url?: string | null
}

defineProps<{
  open: boolean
  sources: SourceLike[]
  title: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'select', id: string): void
}>()

function sourceEmoji(t: string | null) {
  if (t === 'youtube') return '▶️'
  if (t === 'ig') return '📸'
  if (t === 'note') return '📝'
  return '🔗'
}
function sourceLabel(t: string | null) {
  if (t === 'youtube') return 'YouTube'
  if (t === 'ig') return 'IG'
  if (t === 'note') return 'Note'
  return 'Article'
}
</script>

<style scoped>
.slm-overlay {
  position: fixed; inset: 0; z-index: 220;
  background: rgba(0, 0, 0, .46);
  display: flex; align-items: center; justify-content: center; padding: 24px;
}
.slm {
  width: clamp(320px, 92vw, 460px);
  max-height: 76vh;
  background: var(--bg);
  border: 1px solid var(--border2);
  border-radius: 16px;
  box-shadow: 0 24px 64px -16px rgba(0, 0, 0, .5);
  display: flex; flex-direction: column; overflow: hidden;
}
.slm__head {
  display: flex; align-items: center; gap: 10px;
  padding: 16px 18px 14px; border-bottom: 1px solid var(--border); flex-shrink: 0;
}
.slm__title { flex: 1; font-size: 14px; font-weight: 600; color: var(--text); margin: 0; }
.slm__close {
  color: var(--text-dim); font-size: 15px; background: none; border: none; cursor: pointer;
  padding: 4px 8px; border-radius: 6px; line-height: 1;
}
.slm__close:hover { background: var(--surface2); color: var(--text); }

.slm__list { flex: 1 1 auto; overflow-y: auto; padding: 8px; display: flex; flex-direction: column; gap: 4px; }
.slm__item {
  display: flex; align-items: center; gap: 10px; width: 100%; text-align: left;
  padding: 9px 10px; border-radius: 10px; border: 1px solid transparent;
  background: transparent; cursor: pointer; color: inherit; transition: background .14s ease, border-color .14s ease;
}
.slm__item:hover { background: var(--surface2); border-color: var(--border2); }
.slm__thumb {
  flex: 0 0 auto; width: 32px; height: 32px; border-radius: 8px; object-fit: cover;
  background: var(--surface3);
}
.slm__thumb--ph { display: inline-flex; align-items: center; justify-content: center; font-size: 14px; }
.slm__name {
  flex: 1; min-width: 0; font-size: 13px; color: var(--text);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}


.slm-fade-enter-active, .slm-fade-leave-active { transition: opacity .18s ease; }
.slm-fade-enter-from, .slm-fade-leave-to { opacity: 0; }
.slm-fade-enter-active .slm, .slm-fade-leave-active .slm { transition: transform .18s ease, opacity .18s ease; }
.slm-fade-enter-from .slm, .slm-fade-leave-to .slm { transform: scale(0.96); opacity: 0; }
</style>
