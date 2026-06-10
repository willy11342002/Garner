<template>
  <!-- Panel -->
  <Transition name="fab-panel">
    <div v-if="open" class="fab-panel">
      <HomeChatPanel @close="open = false" />
    </div>
  </Transition>

  <!-- FAB -->
  <button
    class="fab"
    :class="{ 'fab--open': open, 'fab--has-items': chainItems.length > 0 }"
    :title="open ? '關閉對話' : 'AI 對話'"
    @click="open = !open"
  >
    <Transition name="fab-icon" mode="out-in">
      <svg v-if="open" key="close" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><path d="M18 6L6 18M6 6l12 12"/></svg>
      <svg v-else key="chat" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="20" height="20"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
    </Transition>
    <span v-if="!open && chainItems.length > 0" class="fab__badge">{{ chainItems.length }}</span>
  </button>
</template>

<script setup lang="ts">
const { chainItems } = useChain()
const open = ref(false)
</script>

<style scoped>
/* FAB */
.fab {
  position: fixed;
  bottom: 28px;
  right: 28px;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  border: none;
  background: var(--accent);
  color: var(--accent-fg);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  box-shadow: 0 4px 20px rgba(0,0,0,0.35);
  transition: background .2s, transform .2s, box-shadow .2s;
}
.fab:hover {
  transform: scale(1.07);
  box-shadow: 0 6px 28px rgba(0,0,0,0.45);
}
.fab--open {
  background: var(--surface3);
  color: var(--text);
}
.fab__badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 18px;
  height: 18px;
  border-radius: 9px;
  background: var(--danger);
  color: #fff;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 4px;
  border: 2px solid var(--bg);
}

/* Panel */
.fab-panel {
  position: fixed;
  bottom: 92px;
  right: 28px;
  width: 400px;
  height: 560px;
  background: var(--bg);
  border: 1px solid var(--border2);
  border-radius: 16px;
  box-shadow: 0 12px 48px rgba(0,0,0,0.45);
  z-index: 999;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* Transitions */
.fab-panel-enter-active { animation: panel-in .22s cubic-bezier(.2,.8,.4,1); }
.fab-panel-leave-active { animation: panel-in .18s cubic-bezier(.4,0,.8,.2) reverse; }
@keyframes panel-in {
  from { opacity: 0; transform: translateY(16px) scale(0.97); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}

.fab-icon-enter-active,
.fab-icon-leave-active { transition: opacity .15s, transform .15s; }
.fab-icon-enter-from { opacity: 0; transform: rotate(-45deg) scale(0.7); }
.fab-icon-leave-to   { opacity: 0; transform: rotate(45deg) scale(0.7); }

@media (max-width: 640px) {
  .fab-panel {
    bottom: 0;
    right: 0;
    width: 100vw;
    height: 70vh;
    border-radius: 16px 16px 0 0;
  }
  .fab {
    bottom: 16px;
    right: 16px;
  }
}
</style>
