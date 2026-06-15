<template>
  <div
    class="folder-row"
    :class="{ 'folder-row--droppable': dragging, 'folder-row--drop': dragOver }"
    @click="!editing && emit('toggle')"
    @dragover.prevent="onDragOver"
    @dragleave="dragOver = false"
    @drop="onDrop"
  >
    <svg
      class="folder-row__chevron"
      :class="{ 'folder-row__chevron--open': expanded }"
      viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"
    ><path d="M9 18l6-6-6-6"/></svg>

    <svg class="folder-row__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>

    <!-- 改名模式 -->
    <input
      v-if="editing"
      ref="inputEl"
      v-model="editName"
      class="folder-row__input"
      :placeholder="t('chat.folder_name_placeholder')"
      @keydown.enter.prevent="commitRename"
      @keydown.escape.prevent="cancelRename"
      @blur="commitRename"
      @click.stop
    >

    <!-- 正常模式 -->
    <template v-else>
      <span class="folder-row__name">{{ folder.name }}</span>
      <span class="folder-row__count">{{ count }}</span>
      <div class="folder-row__actions">
        <button class="folder-row__btn" :title="t('chat.rename')" @click.stop="startRename">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
        </button>
        <button class="folder-row__btn folder-row__btn--del" :title="t('chat.delete_folder')" @click.stop="emit('delete')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/></svg>
        </button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import type { ChatFolder } from '~/types/api'

const props = defineProps<{
  folder: ChatFolder
  count: number
  expanded?: boolean
  dragging?: boolean
}>()

const emit = defineEmits<{
  toggle: []
  rename: [id: string, name: string]
  delete: []
  dropSession: [sessionId: string]
}>()

const { t } = useI18n()

const editing = ref(false)
const editName = ref('')
const dragOver = ref(false)
const inputEl = ref<HTMLInputElement | null>(null)

function startRename() {
  editName.value = props.folder.name
  editing.value = true
  nextTick(() => inputEl.value?.select())
}

function commitRename() {
  const name = editName.value.trim()
  if (name && name !== props.folder.name) emit('rename', props.folder.id, name)
  editing.value = false
}

function cancelRename() {
  editing.value = false
}

function onDragOver() {
  if (props.dragging) dragOver.value = true
}

function onDrop(e: DragEvent) {
  dragOver.value = false
  const id = e.dataTransfer?.getData('text/plain')
  if (id) emit('dropSession', id)
}
</script>

<style scoped>
.folder-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background .1s ease;
  height: 36px;
  border: 1px solid transparent;
}
.folder-row:hover { background: var(--surface2); }
.folder-row--droppable { border-color: color-mix(in oklab, var(--accent) 30%, transparent); border-style: dashed; }
.folder-row--drop { background: var(--accent-dim); border-color: var(--accent-bdr); border-style: solid; }

.folder-row__chevron { color: var(--text-dim); flex-shrink: 0; transition: transform .15s ease; }
.folder-row__chevron--open { transform: rotate(90deg); }
.folder-row__icon { color: var(--text-mid); flex-shrink: 0; }

.folder-row__name {
  flex: 1;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--text-mid);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.folder-row__count {
  flex-shrink: 0;
  min-width: 18px;
  text-align: center;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-dim);
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 1px 6px;
}
.folder-row:hover .folder-row__count { display: none; }

.folder-row__actions { display: none; gap: 2px; flex-shrink: 0; }
.folder-row:hover .folder-row__actions { display: flex; }

.folder-row__btn {
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
.folder-row__btn:hover { background: var(--surface); color: var(--text); }
.folder-row__btn--del:hover { color: #e85555; }

.folder-row__input {
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
