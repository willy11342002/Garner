<template>
  <Teleport to="body">
    <div class="toast-stack">
      <TransitionGroup name="toast">
        <div
          v-for="t in toasts"
          :key="t.id"
          class="toast"
          :class="`toast--${t.type}`"
        >
          {{ t.message }}
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
const { toasts } = useToast()
</script>

<style scoped>
.toast-stack {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}
.toast {
  pointer-events: auto;
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
  color: #fff;
  box-shadow: 0 8px 24px -6px rgba(0,0,0,.35);
  max-width: 320px;
  word-break: break-word;
}
.toast--success { background: #2a9d3f; }
.toast--error   { background: #e85555; }
.toast--info    { background: #3b82f6; }

.toast-enter-active, .toast-leave-active { transition: all .25s ease; }
.toast-enter-from { opacity: 0; transform: translateX(20px); }
.toast-leave-to   { opacity: 0; transform: translateX(20px); }
</style>
