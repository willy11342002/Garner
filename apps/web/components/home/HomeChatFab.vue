<template>
  <!-- Panel -->
  <Transition name="fab-panel">
    <div
      v-if="open"
      class="fab-panel"
      :class="{ 'fab-panel--left': side === 'left' }"
      :style="panelStyle"
    >
      <HomeChatPanel @close="open = false" />
    </div>
  </Transition>

  <!-- FAB -->
  <button
    ref="fabEl"
    class="fab"
    :class="{ 'fab--open': open, 'fab--dragging': dragging }"
    :style="fabStyle"
    :title="open ? t('fab.close') : t('fab.open')"
    @pointerdown="onPointerDown"
    @click="onClick"
  >
    <Transition name="fab-icon" mode="out-in">
      <svg v-if="open" key="close" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><path d="M18 6L6 18M6 6l12 12"/></svg>
      <svg v-else key="chat" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="20" height="20"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
    </Transition>
    <span v-if="!open && chainItems.length > 0" class="fab__badge">{{ chainItems.length }}</span>
  </button>
</template>

<script setup lang="ts">
const { t } = useI18n()
const { chainItems } = useChain()
const open = ref(false)

// --- Drag state ---
const FAB_SIZE = 52
const EDGE_GAP = 28
const SNAP_GAP = 16 // gap from edge after snap

const fabEl = ref<HTMLButtonElement | null>(null)
const dragging = ref(false)
// 'right' or 'left' — persisted side after snap
const side = ref<'left' | 'right'>('right')
// bottom offset from viewport bottom (in px)
const bottomPx = ref(EDGE_GAP)

let dragStartX = 0
let dragStartY = 0
let pointerStartClientX = 0
let pointerStartClientY = 0
let moved = false

const fabStyle = computed(() => {
  if (side.value === 'right') {
    return { right: `${SNAP_GAP}px`, left: 'auto', bottom: `${bottomPx.value}px`, top: 'auto' }
  } else {
    return { left: `${SNAP_GAP}px`, right: 'auto', bottom: `${bottomPx.value}px`, top: 'auto' }
  }
})

const panelStyle = computed(() => {
  const bottom = bottomPx.value + FAB_SIZE + 12
  if (side.value === 'right') {
    return { bottom: `${bottom}px`, right: `${SNAP_GAP}px`, left: 'auto' }
  } else {
    return { bottom: `${bottom}px`, left: `${SNAP_GAP}px`, right: 'auto' }
  }
})

function onPointerDown(e: PointerEvent) {
  if (e.button !== 0) return
  moved = false
  pointerStartClientX = e.clientX
  pointerStartClientY = e.clientY
  // current fab center position
  const rect = fabEl.value!.getBoundingClientRect()
  dragStartX = rect.left
  dragStartY = rect.top

  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
}

function onPointerMove(e: PointerEvent) {
  const dx = e.clientX - pointerStartClientX
  const dy = e.clientY - pointerStartClientY
  if (!moved && Math.hypot(dx, dy) < 5) return
  moved = true
  dragging.value = true

  const vw = window.innerWidth
  const vh = window.innerHeight
  // clamp so FAB stays within viewport
  const newLeft = Math.max(0, Math.min(vw - FAB_SIZE, dragStartX + dx))
  const newTop  = Math.max(0, Math.min(vh - FAB_SIZE, dragStartY + dy))

  // update bottom from top
  bottomPx.value = vh - newTop - FAB_SIZE
  // update side hint live so panel flips
  side.value = newLeft + FAB_SIZE / 2 < vw / 2 ? 'left' : 'right'
}

function onPointerUp(e: PointerEvent) {
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  dragging.value = false

  if (!moved) return // treated as click

  // snap: keep current side, clamp bottom
  const vh = window.innerHeight
  bottomPx.value = Math.max(SNAP_GAP, Math.min(vh - FAB_SIZE - SNAP_GAP, bottomPx.value))
}

function onClick() {
  if (moved) return // was a drag, not a click
  open.value = !open.value
}
</script>

<style scoped>
/* FAB */
.fab {
  position: fixed;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  border: none;
  background: var(--accent);
  color: var(--accent-fg);
  cursor: grab;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  box-shadow: 0 4px 20px rgba(0,0,0,0.35);
  transition: background .2s, transform .2s, box-shadow .2s;
  touch-action: none;
  user-select: none;
}
.fab:hover {
  transform: scale(1.07);
  box-shadow: 0 6px 28px rgba(0,0,0,0.45);
}
.fab--open {
  background: var(--surface3);
  color: var(--text);
}
.fab--dragging {
  cursor: grabbing;
  transform: scale(1.1);
  box-shadow: 0 8px 32px rgba(0,0,0,0.5);
  transition: transform .05s, box-shadow .05s;
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
    bottom: 0 !important;
    right: 0 !important;
    left: 0 !important;
    width: 100vw;
    height: 70vh;
    border-radius: 16px 16px 0 0;
  }
}
</style>
