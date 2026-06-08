<script setup lang="ts">
import { useEditor, EditorContent, VueNodeViewRenderer } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import GlobalDragHandle from 'tiptap-extension-global-drag-handle'
import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight'
import { createLowlight, common } from 'lowlight'
import Underline from '@tiptap/extension-underline'
import { TextStyle, Color } from '@tiptap/extension-text-style'
import Link from '@tiptap/extension-link'
import { Markdown } from '@tiptap/markdown'
import CodeBlockView from './CodeBlockView.vue'
import BubbleMenuBar from './BubbleMenuBar.vue'

const lowlight = createLowlight(common)

const props = defineProps<{
  modelValue: string | null | undefined
  readonly?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const editor = useEditor({
  extensions: [
    StarterKit.configure({ codeBlock: false }),
    CodeBlockLowlight.configure({ lowlight }).extend({
      addNodeView() { return VueNodeViewRenderer(CodeBlockView) },
    }),
    Underline,
    TextStyle,
    Color,
    Link.configure({ openOnClick: false }),
    GlobalDragHandle.configure({ dragHandleWidth: 24 }),
    Markdown.configure({ html: false }),
  ],
  editable: !props.readonly,
  content: '',
  onUpdate({ editor }) {
    if (!props.readonly) {
      emit('update:modelValue', (editor as any).getMarkdown())
    }
  },
})

function setMarkdown(val: string | null | undefined) {
  if (!editor.value) return
  const parsed = (editor.value as any).markdown.parse(val ?? '')
  editor.value.commands.setContent(parsed, false)
}

watch(() => props.modelValue, setMarkdown)

watch(() => props.readonly, (val) => {
  editor.value?.setEditable(!val)
})

// ── Insert button ──
const insertVisible = ref(false)
const insertX = ref(0)
const insertY = ref(0)
let dragHandleEl: HTMLElement | null = null

// Document-level mousemove fires AFTER the ProseMirror extension has processed the
// event (set style.left/top and called showDragHandle), so we read the final state here.
function onDocMouseMove() {
  if (props.readonly) return
  if (!dragHandleEl) dragHandleEl = document.querySelector('.drag-handle')
  if (!dragHandleEl || dragHandleEl.classList.contains('hide') || !dragHandleEl.style.left) {
    insertVisible.value = false
    return
  }
  const left = parseInt(dragHandleEl.style.left, 10)
  const top  = parseInt(dragHandleEl.style.top,  10)
  if (isNaN(left) || isNaN(top)) { insertVisible.value = false; return }
  insertVisible.value = true
  insertX.value = left - 28
  insertY.value = top
}

// ── Block menu (handle click) ──
const menuVisible = ref(false)
const menuX = ref(0)
const menuY = ref(0)
let menuBlockPos: number | null = null

function resolveHandleBlockPos(): number | null {
  if (!editor.value || !dragHandleEl?.style.left) return null
  const left = parseInt(dragHandleEl.style.left, 10)
  const top  = parseInt(dragHandleEl.style.top,  10)
  if (isNaN(left) || isNaN(top)) return null
  const posData = editor.value.view.posAtCoords({ left: left + 34, top: top + 12 })
  if (!posData) return null
  const $pos = editor.value.state.doc.resolve(posData.pos)
  return $pos.depth >= 1 ? $pos.before(1) : null
}

async function openMenu(e: MouseEvent) {
  e.preventDefault()
  e.stopPropagation()
  menuBlockPos = resolveHandleBlockPos()
  menuX.value = e.clientX + 8
  menuY.value = e.clientY - 4
  menuVisible.value = true

  // After render, clamp menu inside viewport
  await nextTick()
  const menuEl = document.querySelector('.tiptap-block-menu') as HTMLElement | null
  if (menuEl) {
    const rect = menuEl.getBoundingClientRect()
    if (rect.bottom > window.innerHeight - 8) {
      menuY.value = e.clientY - rect.height - 4
    }
    if (rect.right > window.innerWidth - 8) {
      menuX.value = e.clientX - rect.width - 8
    }
  }
}

function closeMenu() { menuVisible.value = false }

function applyBlockType(command: () => void) {
  if (!editor.value) return
  if (menuBlockPos !== null) {
    editor.value.chain().focus().setNodeSelection(menuBlockPos).run()
  } else {
    editor.value.commands.focus()
  }
  command()
  closeMenu()
}

function deleteMenuBlock() {
  if (!editor.value || menuBlockPos === null) return
  editor.value.chain().focus().setNodeSelection(menuBlockPos).deleteSelection().run()
  closeMenu()
}

function onInsertClick() {
  if (!editor.value || !dragHandleEl) return

  const handleLeft = parseInt(dragHandleEl.style.left, 10)
  const handleTop  = parseInt(dragHandleEl.style.top,  10)
  if (isNaN(handleLeft) || isNaN(handleTop)) return

  // Sample a point inside the block content (handle sits at blockLeft - 24)
  const posData = editor.value.view.posAtCoords({
    left: handleLeft + 34,
    top: handleTop + 12,
  })
  if (!posData) return

  const $pos = editor.value.state.doc.resolve(posData.pos)
  if ($pos.depth < 1) return

  // Insert a new paragraph right after the top-level block
  const insertAt = $pos.after(1)
  editor.value
    .chain()
    .focus()
    .insertContentAt(insertAt, { type: 'paragraph' })
    .setTextSelection(insertAt + 1)
    .run()

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
  document.addEventListener('mousemove', onDocMouseMove)
  setMarkdown(props.modelValue)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick, true)
  document.removeEventListener('mousemove', onDocMouseMove)
  editor.value?.destroy()
})

defineExpose({ editor })
</script>

<template>
  <div
    ref="wrapRef"
    class="tiptap-root"
  >
    <EditorContent
      :editor="editor"
      class="tiptap-wrap"
      :class="{ 'tiptap-wrap--readonly': readonly, 'tiptap-wrap--edit': !readonly }"
    />
    <BubbleMenuBar v-if="editor && !readonly" :editor="editor" />

    <Teleport to="body">
      <!-- Insert button -->
      <button
        v-if="insertVisible && !readonly"
        class="tiptap-insert-btn"
        :style="{ top: `${insertY}px`, left: `${insertX}px` }"
        title="在下方插入區塊"
        @mousedown.prevent
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
        <div class="tiptap-block-menu__section-label">轉換為</div>

        <button class="tiptap-block-menu__item" @mousedown.prevent @click="applyBlockType(() => editor?.chain().setParagraph().run())">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="15" y2="12"/><line x1="3" y1="18" x2="18" y2="18"/></svg>
          正文
        </button>
        <button class="tiptap-block-menu__item" @mousedown.prevent @click="applyBlockType(() => editor?.chain().setHeading({ level: 1 }).run())">
          <span class="tiptap-block-menu__badge">H1</span>
          標題 1
        </button>
        <button class="tiptap-block-menu__item" @mousedown.prevent @click="applyBlockType(() => editor?.chain().setHeading({ level: 2 }).run())">
          <span class="tiptap-block-menu__badge">H2</span>
          標題 2
        </button>
        <button class="tiptap-block-menu__item" @mousedown.prevent @click="applyBlockType(() => editor?.chain().setHeading({ level: 3 }).run())">
          <span class="tiptap-block-menu__badge">H3</span>
          標題 3
        </button>
        <button class="tiptap-block-menu__item" @mousedown.prevent @click="applyBlockType(() => editor?.chain().setHeading({ level: 4 }).run())">
          <span class="tiptap-block-menu__badge">H4</span>
          標題 4
        </button>

        <div class="tiptap-block-menu__separator"/>

        <button class="tiptap-block-menu__item" @mousedown.prevent @click="applyBlockType(() => editor?.chain().toggleBulletList().run())">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="9" y1="6" x2="20" y2="6"/><line x1="9" y1="12" x2="20" y2="12"/><line x1="9" y1="18" x2="20" y2="18"/><circle cx="4" cy="6" r="1.5" fill="currentColor" stroke="none"/><circle cx="4" cy="12" r="1.5" fill="currentColor" stroke="none"/><circle cx="4" cy="18" r="1.5" fill="currentColor" stroke="none"/></svg>
          項目清單
        </button>
        <button class="tiptap-block-menu__item" @mousedown.prevent @click="applyBlockType(() => editor?.chain().toggleOrderedList().run())">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="10" y1="6" x2="21" y2="6"/><line x1="10" y1="12" x2="21" y2="12"/><line x1="10" y1="18" x2="21" y2="18"/><path d="M4 6h1v4" stroke-linejoin="round"/><path d="M4 10h2"/><path d="M6 18H4c0-1 2-2 2-3s-1-1.5-2-1"/></svg>
          編號清單
        </button>
        <button class="tiptap-block-menu__item" @mousedown.prevent @click="applyBlockType(() => editor?.chain().setBlockquote().run())">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z"/><path d="M15 21c3 0 7-1 7-8V5c0-1.25-.757-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2h.75c0 2.25.25 4-2.75 4v3c0 1 0 1 1 1z"/></svg>
          引用
        </button>
        <button class="tiptap-block-menu__item" @mousedown.prevent @click="applyBlockType(() => editor?.chain().setCodeBlock().run())">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
          程式碼區塊
        </button>

        <div class="tiptap-block-menu__separator"/>

        <button class="tiptap-block-menu__item tiptap-block-menu__item--danger" @mousedown.prevent @click="deleteMenuBlock">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
          刪除區塊
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

.tiptap-wrap :deep(u) { text-decoration: underline; }

.tiptap-wrap :deep(a) {
  color: var(--accent);
  text-decoration: underline;
  text-underline-offset: 2px;
  cursor: pointer;
}

.tiptap-wrap :deep(code) {
  background: var(--surface2);
  border: 1px solid var(--border2);
  border-radius: 3px;
  padding: 0.1em 0.35em;
  font-family: 'Fira Code', 'JetBrains Mono', monospace;
  font-size: 0.83em;
  color: var(--accent);
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

/* ── Code block hljs token colours (structure/bg handled by CodeBlockView.vue) ── */
/* hljs tokens */
.tiptap-wrap :deep(.hljs-comment),
.tiptap-wrap :deep(.hljs-quote)       { color: #6c7086; font-style: italic; }
.tiptap-wrap :deep(.hljs-keyword),
.tiptap-wrap :deep(.hljs-selector-tag),
.tiptap-wrap :deep(.hljs-addition)    { color: #cba6f7; }
.tiptap-wrap :deep(.hljs-number),
.tiptap-wrap :deep(.hljs-literal),
.tiptap-wrap :deep(.hljs-link)        { color: #fab387; }
.tiptap-wrap :deep(.hljs-string),
.tiptap-wrap :deep(.hljs-doctag)      { color: #a6e3a1; }
.tiptap-wrap :deep(.hljs-title),
.tiptap-wrap :deep(.hljs-section),
.tiptap-wrap :deep(.hljs-selector-id),
.tiptap-wrap :deep(.hljs-built_in)   { color: #89b4fa; }
.tiptap-wrap :deep(.hljs-type),
.tiptap-wrap :deep(.hljs-class .hljs-title) { color: #f38ba8; }
.tiptap-wrap :deep(.hljs-attr),
.tiptap-wrap :deep(.hljs-variable),
.tiptap-wrap :deep(.hljs-template-variable) { color: #f5c2e7; }
.tiptap-wrap :deep(.hljs-regexp),
.tiptap-wrap :deep(.hljs-symbol)      { color: #94e2d5; }
.tiptap-wrap :deep(.hljs-tag)         { color: #89dceb; }
.tiptap-wrap :deep(.hljs-punctuation),
.tiptap-wrap :deep(.hljs-operator)    { color: #89dceb; }
.tiptap-wrap :deep(.hljs-meta)        { color: #f9e2af; }

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

.tiptap-block-menu__section-label {
  padding: 4px 10px 2px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-mid);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  opacity: 0.6;
}

.tiptap-block-menu__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  font-size: 10px;
  font-weight: 700;
  color: var(--text-mid);
  flex-shrink: 0;
  line-height: 1;
}

.tiptap-block-menu__separator {
  height: 1px;
  background: var(--border2);
  margin: 4px 0;
}

.tiptap-block-menu__item--danger {
  color: #e57373;
}

.tiptap-block-menu__item--danger svg {
  color: #e57373;
}

.tiptap-block-menu__item--danger:hover {
  background: rgba(229, 115, 115, 0.1);
}
</style>
