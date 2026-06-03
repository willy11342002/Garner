<script setup lang="ts">
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import GlobalDragHandle from 'tiptap-extension-global-drag-handle'

const props = defineProps<{
  modelValue: Record<string, unknown> | null | undefined
  readonly?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: Record<string, unknown>]
}>()

const editor = useEditor({
  extensions: [
    StarterKit,
    GlobalDragHandle.configure({ dragHandleWidth: 24 }),
  ],
  editable: !props.readonly,
  content: props.modelValue ?? { type: 'doc', content: [] },
  onUpdate({ editor }) {
    if (!props.readonly) {
      emit('update:modelValue', editor.getJSON() as Record<string, unknown>)
    }
  },
})

watch(() => props.modelValue, (val) => {
  if (!editor.value) return
  const current = JSON.stringify(editor.value.getJSON())
  const next = JSON.stringify(val ?? { type: 'doc', content: [] })
  if (current !== next) {
    editor.value.commands.setContent(val ?? { type: 'doc', content: [] }, false)
  }
})

watch(() => props.readonly, (val) => {
  editor.value?.setEditable(!val)
})

// ── Insert button & block tracking ──
const insertVisible = ref(false)
const insertX = ref(0)
const insertY = ref(0)
let editorEl: HTMLElement | null = null

function getTopLevelBlock(target: HTMLElement): HTMLElement | null {
  if (!editorEl) return null
  let el: HTMLElement | null = target
  while (el && el.parentElement !== editorEl) {
    el = el.parentElement as HTMLElement | null
  }
  return el && el !== editorEl ? el : null
}

function onEditorMouseMove(e: MouseEvent) {
  if (props.readonly) return
  const block = getTopLevelBlock(e.target as HTMLElement)
  if (!block) { insertVisible.value = false; return }
  const rect = block.getBoundingClientRect()
  insertVisible.value = true
  // 垂直置中於 block 第一行
  const lineH = 28
  insertY.value = rect.top + Math.min(rect.height / 2, lineH / 2) - lineH / 2
  // handle 在 block 左邊，insert 再往左 28px
  insertX.value = rect.left - 56
}

function onEditorMouseLeave() {
  insertVisible.value = false
}

// ── Block menu (handle click) ──
const menuVisible = ref(false)
const menuX = ref(0)
const menuY = ref(0)

function openMenu(e: MouseEvent) {
  e.preventDefault()
  e.stopPropagation()
  menuVisible.value = true
  menuX.value = e.clientX + 8
  menuY.value = e.clientY - 4
}

function closeMenu() { menuVisible.value = false }

function insertBlockBelow() {
  editor.value?.chain().focus().createParagraphNear().run()
  closeMenu()
}

function convertToBlockquote() {
  editor.value?.chain().focus().setBlockquote().run()
  closeMenu()
}

function onInsertClick() {
  editor.value?.chain().focus().createParagraphNear().run()
  insertVisible.value = false
}

function onDocClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (target.classList.contains('drag-handle')) {
    openMenu(e)
    return
  }
  if (!target.closest('.tiptap-block-menu')) {
    closeMenu()
  }
}

const wrapRef = ref<HTMLElement | null>(null)

onMounted(() => {
  document.addEventListener('click', onDocClick, true)
  // 找到 ProseMirror 元素
  nextTick(() => {
    editorEl = wrapRef.value?.querySelector('.ProseMirror') ?? null
  })
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick, true)
  editor.value?.destroy()
})

defineExpose({ editor })
</script>

<template>
  <div
    ref="wrapRef"
    class="tiptap-root"
    @mousemove="onEditorMouseMove"
    @mouseleave="onEditorMouseLeave"
  >
    <EditorContent
      :editor="editor"
      class="tiptap-wrap"
      :class="{ 'tiptap-wrap--readonly': readonly, 'tiptap-wrap--edit': !readonly }"
    />

    <Teleport to="body">
      <!-- Insert button -->
      <button
        v-if="insertVisible && !readonly"
        class="tiptap-insert-btn"
        :style="{ top: `${insertY}px`, left: `${insertX}px` }"
        title="在下方插入區塊"
        @click="onInsertClick"
        @mouseenter="insertVisible = true"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
      </button>

      <!-- Block menu -->
      <div
        v-if="menuVisible && !readonly"
        class="tiptap-block-menu"
        :style="{ top: `${menuY}px`, left: `${menuX}px` }"
      >
        <button class="tiptap-block-menu__item" @click="insertBlockBelow">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          在下方插入區塊
        </button>
        <button class="tiptap-block-menu__item" @click="convertToBlockquote">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z"/><path d="M15 21c3 0 7-1 7-8V5c0-1.25-.757-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2h.75c0 2.25.25 4-2.75 4v3c0 1 0 1 1 1z"/></svg>
          引用區塊
        </button>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.tiptap-root { position: relative; }

.tiptap-wrap {
  color: var(--text);
  font-family: var(--font-ui);
  font-size: 0.9rem;
  line-height: 1.75;
}

.tiptap-wrap :deep(.ProseMirror) { outline: none; }

.tiptap-wrap :deep(h2) {
  font-family: var(--font-brand);
  font-size: 1rem;
  font-weight: 600;
  color: var(--accent);
  margin: 1.4em 0 0.4em;
  letter-spacing: 0.01em;
}

.tiptap-wrap :deep(h3) {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--text);
  margin: 1.1em 0 0.3em;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  opacity: 0.7;
}

.tiptap-wrap :deep(p) {
  margin: 0 0 0.6em;
  color: var(--text);
  opacity: 0.9;
}

.tiptap-wrap :deep(ul) {
  padding-left: 1.2em;
  margin: 0.3em 0 0.8em;
}

.tiptap-wrap :deep(li) {
  margin: 0.2em 0;
  color: var(--text);
  opacity: 0.9;
}

.tiptap-wrap :deep(li::marker) {
  color: var(--accent);
  opacity: 0.6;
}

.tiptap-wrap--edit :deep(.ProseMirror) {
  border: 1px solid var(--border2);
  border-radius: 8px;
  padding: 0.75rem 1rem;
  min-height: 200px;
  transition: border-color 0.15s;
}

.tiptap-wrap--edit :deep(.ProseMirror:focus) {
  border-color: var(--accent-bdr);
}

/* Drag handle – 讓 extension JS 控制 opacity */
.tiptap-wrap :deep(.drag-handle) {
  position: fixed;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 4px;
  cursor: grab;
  transition: background 0.12s;
}

.tiptap-wrap :deep(.drag-handle:hover) {
  background: var(--surface3);
}

.tiptap-wrap :deep(.drag-handle:active) {
  cursor: grabbing;
  background: var(--surface3);
}

.tiptap-wrap :deep(.drag-handle::after) {
  content: '⠿';
  font-size: 15px;
  color: var(--text-mid);
  line-height: 1;
  display: block;
  pointer-events: none;
}
</style>

<style>
/* Insert button（global，Teleport 到 body）*/
.tiptap-insert-btn {
  position: fixed;
  z-index: 9998;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  border: none;
  background: transparent;
  color: var(--text-mid);
  cursor: pointer;
  transition: background 0.12s, color 0.12s;
}
.tiptap-insert-btn:hover {
  background: var(--surface3);
  color: var(--text);
}

/* Block menu（global，Teleport 到 body）*/
.tiptap-block-menu {
  position: fixed;
  z-index: 9999;
  background: var(--surface);
  border: 1px solid var(--border2);
  border-radius: 8px;
  box-shadow: 0 8px 24px var(--shadow);
  padding: 4px;
  min-width: 168px;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.tiptap-block-menu__item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 10px;
  background: none;
  border: none;
  border-radius: 5px;
  font-size: 13px;
  color: var(--text);
  cursor: pointer;
  text-align: left;
  transition: background 0.1s;
}

.tiptap-block-menu__item:hover {
  background: var(--surface2);
}

.tiptap-block-menu__item svg {
  color: var(--text-mid);
  flex-shrink: 0;
}
</style>
