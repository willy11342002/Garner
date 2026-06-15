<template>
  <div
    class="session-row"
    :class="{ 'session-row--active': active, 'session-row--indent': indent, 'session-row--editing': editing, 'session-row--disabled': disabled, 'session-row--dragging': dragging }"
    :draggable="!editing"
    @click="!editing && !disabled && !active && emit('click')"
    @dragstart="onDragStart"
    @dragend="onDragEnd"
  >
    <!-- 改名模式 -->
    <input
      v-if="editing"
      ref="inputEl"
      v-model="editName"
      class="session-row__input"
      :placeholder="t('chat.rename_placeholder')"
      @keydown.enter.prevent="commitRename"
      @keydown.escape.prevent="cancelRename"
      @blur="commitRename"
      @click.stop
    >

    <!-- 正常模式 -->
    <template v-else>
      <span class="session-row__title">{{ session.title || t('chat.untitled') }}</span>
      <div class="session-row__actions">
        <button class="session-row__btn" :title="t('chat.rename')" @click.stop="startRename">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
        </button>
        <button class="session-row__btn session-row__btn--del" :title="t('chat.delete')" @click.stop="emit('delete')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/></svg>
        </button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import type { ChatSession } from '~/types/api'

const props = defineProps<{
  session: ChatSession
  active?: boolean
  indent?: boolean
  disabled?: boolean
}>()

const emit = defineEmits<{
  click: []
  rename: [id: string, name: string]
  delete: []
  dragstart: [id: string]
  dragend: []
}>()

const { t } = useI18n()

const editing = ref(false)
const editName = ref('')
const dragging = ref(false)
const inputEl = ref<HTMLInputElement | null>(null)

function onDragStart(e: DragEvent) {
  if (editing.value) return
  dragging.value = true
  e.dataTransfer?.setData('text/plain', props.session.id)
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move'
  emit('dragstart', props.session.id)
}

function onDragEnd() {
  dragging.value = false
  emit('dragend')
}

function startRename() {
  editName.value = props.session.title || ''
  editing.value = true
  nextTick(() => {
    inputEl.value?.select()
  })
}

function commitRename() {
  const name = editName.value.trim()
  if (name && name !== props.session.title) {
    emit('rename', props.session.id, name)
  }
  editing.value = false
}

function cancelRename() {
  editing.value = false
}
</script>

<style scoped>
.session-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background .1s ease;
  height: 36px;
}
.session-row:hover { background: var(--surface2); }
.session-row--active { background: var(--accent-dim); cursor: default; }
.session-row--indent { padding-left: 24px; }
.session-row--editing { cursor: default; background: var(--surface2); }
.session-row--disabled { cursor: default; pointer-events: none; }
.session-row--disabled:not(.session-row--active) { opacity: 0.5; }
.session-row--dragging { opacity: 0.4; }

.session-row__title {
  flex: 1;
  font-size: 12.5px;
  color: var(--text-mid);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.session-row--active .session-row__title { color: var(--accent); }

.session-row__actions {
  display: none;
  gap: 2px;
  flex-shrink: 0;
}
.session-row:hover .session-row__actions { display: flex; }

.session-row__btn {
  width: 22px;
  height: 22px;
  border-radius: 5px;
  background: transparent;
  border: none;
  color: var(--text-dim);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all .1s ease;
}
.session-row__btn:hover { background: var(--surface); color: var(--text); }
.session-row__btn--del:hover { color: #e85555; }

.session-row__input {
  flex: 1;
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--accent-bdr);
  outline: none;
  font-size: 12.5px;
  color: var(--text);
  padding: 0 2px;
  font-family: var(--font-ui);
}
</style>
