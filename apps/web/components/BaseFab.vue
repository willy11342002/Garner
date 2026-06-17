<template>
  <!-- Panel -->
  <Transition name="bfab-panel">
    <div
      v-if="open"
      class="bfab-panel"
      :class="{ 'bfab-panel--left': side === 'left' }"
      :style="panelStyleWithSize"
    >
      <slot name="panel" :close="() => (open = false)" />
    </div>
  </Transition>

  <!-- FAB button -->
  <button
    ref="fabEl"
    class="bfab"
    :class="{ 'bfab--open': open, 'bfab--dragging': dragging }"
    :style="fabStyle"
    :title="open ? closeTitle : openTitle"
    @pointerdown="onPointerDown"
    @click="onClick"
  >
    <Transition name="bfab-icon" mode="out-in">
      <span v-if="open" key="open" class="bfab-icon-wrap">
        <slot name="icon-open">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><path d="M18 6L6 18M6 6l12 12"/></svg>
        </slot>
      </span>
      <span v-else key="closed" class="bfab-icon-wrap">
        <slot name="icon-closed">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="20" height="20"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        </slot>
      </span>
    </Transition>
    <slot name="badge" />
  </button>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  openTitle?: string
  closeTitle?: string
  panelWidth?: number
  panelHeight?: number
}>(), {
  openTitle: '開啟',
  closeTitle: '關閉',
  panelWidth: 380,
  panelHeight: 520,
})

const FAB_SIZE = 52
const SNAP_GAP = 16
const EDGE_GAP = 28

const fabEl = ref<HTMLButtonElement | null>(null)
const open = ref(false)
const dragging = ref(false)
const side = ref<'left' | 'right'>('right')
const bottomPx = ref(EDGE_GAP)

let dragStartX = 0
let dragStartY = 0
let pointerStartClientX = 0
let pointerStartClientY = 0
let moved = false

const fabStyle = computed(() =>
  side.value === 'right'
    ? { right: `${SNAP_GAP}px`, left: 'auto', bottom: `${bottomPx.value}px`, top: 'auto' }
    : { left: `${SNAP_GAP}px`, right: 'auto', bottom: `${bottomPx.value}px`, top: 'auto' }
)

const panelStyleWithSize = computed(() => {
  const bottom = bottomPx.value + FAB_SIZE + 12
  return side.value === 'right'
    ? { bottom: `${bottom}px`, right: `${SNAP_GAP}px`, left: 'auto', width: `${props.panelWidth}px`, height: `${props.panelHeight}px` }
    : { bottom: `${bottom}px`, left: `${SNAP_GAP}px`, right: 'auto', width: `${props.panelWidth}px`, height: `${props.panelHeight}px` }
})

function onPointerDown(e: PointerEvent) {
  if (e.button !== 0) return
  moved = false
  pointerStartClientX = e.clientX
  pointerStartClientY = e.clientY
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
  const newLeft = Math.max(0, Math.min(vw - FAB_SIZE, dragStartX + dx))
  const newTop = Math.max(0, Math.min(vh - FAB_SIZE, dragStartY + dy))
  bottomPx.value = vh - newTop - FAB_SIZE
  side.value = newLeft + FAB_SIZE / 2 < vw / 2 ? 'left' : 'right'
}

function onPointerUp() {
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  dragging.value = false
  if (!moved) return
  const vh = window.innerHeight
  bottomPx.value = Math.max(SNAP_GAP, Math.min(vh - FAB_SIZE - SNAP_GAP, bottomPx.value))
}

function onClick() {
  if (moved) return
  open.value = !open.value
}

defineExpose({ open })
</script>

<style scoped>
.bfab {
  position: fixed;
  width: 52px; height: 52px; border-radius: 50%;
  border: none; background: var(--accent); color: var(--accent-fg, #fff);
  cursor: grab; display: flex; align-items: center; justify-content: center;
  z-index: 1000; box-shadow: 0 4px 20px rgba(0,0,0,0.35);
  transition: background .2s, transform .2s, box-shadow .2s; touch-action: none; user-select: none;
}
.bfab:hover { transform: scale(1.07); box-shadow: 0 6px 28px rgba(0,0,0,0.45); }
.bfab--open { background: var(--surface3, var(--surface2)); color: var(--text); }
.bfab--dragging { cursor: grabbing; transform: scale(1.1); box-shadow: 0 8px 32px rgba(0,0,0,0.5); transition: transform .05s, box-shadow .05s; }

.bfab-icon-wrap { display: contents; }

.bfab-panel {
  position: fixed;
  max-height: calc(100vh - 120px);
  background: var(--bg); border: 1px solid var(--border2); border-radius: 16px;
  box-shadow: 0 12px 48px rgba(0,0,0,0.45); z-index: 999; overflow: hidden;
  display: flex; flex-direction: column;
}

.bfab-panel-enter-active { animation: bfab-panel-in .22s cubic-bezier(.2,.8,.4,1); }
.bfab-panel-leave-active { animation: bfab-panel-in .18s cubic-bezier(.4,0,.8,.2) reverse; }
@keyframes bfab-panel-in { from { opacity: 0; transform: translateY(16px) scale(0.97); } to { opacity: 1; transform: translateY(0) scale(1); } }

.bfab-icon-enter-active, .bfab-icon-leave-active { transition: opacity .15s, transform .15s; }
.bfab-icon-enter-from { opacity: 0; transform: rotate(-45deg) scale(0.7); }
.bfab-icon-leave-to { opacity: 0; transform: rotate(45deg) scale(0.7); }

@media (max-width: 640px) {
  .bfab-panel {
    bottom: 0 !important; right: 0 !important; left: 0 !important;
    width: 100vw !important; height: 72vh !important; max-height: 72vh;
    border-radius: 16px 16px 0 0;
  }
}
</style>
