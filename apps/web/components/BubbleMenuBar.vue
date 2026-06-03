<script setup lang="ts">
import type { Editor } from '@tiptap/core'

const props = defineProps<{ editor: Editor }>()

// ── Visibility & position ──
const visible   = ref(false)
const menuTop   = ref(0)
const menuLeft  = ref(0)
const menuEl    = ref<HTMLElement | null>(null)
let insideMenu  = false

async function reposition() {
  const { selection } = props.editor.state
  if (selection.empty) { visible.value = false; return }

  const domSel = window.getSelection()
  if (!domSel || domSel.rangeCount === 0) { visible.value = false; return }
  const rect = domSel.getRangeAt(0).getBoundingClientRect()
  if (!rect.width && !rect.height) { visible.value = false; return }

  visible.value = true
  await nextTick()
  if (!menuEl.value) return

  const mw = menuEl.value.offsetWidth
  const mh = menuEl.value.offsetHeight

  let l = rect.left + rect.width / 2 - mw / 2
  let t = rect.top - mh - 8

  l = Math.max(8, Math.min(l, window.innerWidth - mw - 8))
  if (t < 8) t = rect.bottom + 8

  menuLeft.value = l
  menuTop.value  = t
}

function onBlur() {
  // Keep visible while user types in link input
  setTimeout(() => {
    if (!props.editor.isFocused && !insideMenu) visible.value = false
  }, 150)
}

onMounted(() => {
  props.editor.on('selectionUpdate', reposition)
  props.editor.on('transaction',     reposition)
  props.editor.on('blur',            onBlur)
})
onBeforeUnmount(() => {
  props.editor.off('selectionUpdate', reposition)
  props.editor.off('transaction',     reposition)
  props.editor.off('blur',            onBlur)
})

// ── Color palette ──
const COLORS = [
  { label: '預設', value: null },
  { label: '灰',   value: '#6b7280' },
  { label: '棕',   value: '#92400e' },
  { label: '橘',   value: '#c2410c' },
  { label: '黃',   value: '#ca8a04' },
  { label: '綠',   value: '#16a34a' },
  { label: '藍',   value: '#2563eb' },
  { label: '紫',   value: '#7c3aed' },
  { label: '粉',   value: '#db2777' },
  { label: '紅',   value: '#dc2626' },
]

const showColorPicker = ref(false)
const showLinkInput   = ref(false)
const linkInput       = ref('')
const linkInputEl     = ref<HTMLInputElement | null>(null)
let savedSel: { from: number; to: number } | null = null

const activeColor = computed(() =>
  (props.editor.getAttributes('textStyle').color as string | null) ?? null
)

// ── Helpers ──
function cmd(fn: () => void) {
  fn()
  showColorPicker.value = false
}

function toggleColorPicker() {
  showColorPicker.value = !showColorPicker.value
  if (showColorPicker.value) showLinkInput.value = false
}
function applyColor(value: string | null) {
  if (value === null) props.editor.chain().focus().unsetColor().run()
  else props.editor.chain().focus().setColor(value).run()
  showColorPicker.value = false
}

async function openLinkInput() {
  const { from, to } = props.editor.state.selection
  savedSel = { from, to }
  linkInput.value = props.editor.getAttributes('link').href ?? ''
  showLinkInput.value = true
  showColorPicker.value = false
  await nextTick()
  linkInputEl.value?.focus()
  linkInputEl.value?.select()
}
function applyLink() {
  const url = linkInput.value.trim()
  let chain = props.editor.chain().focus()
  if (savedSel) chain = (chain as any).setTextSelection(savedSel)
  if (!url) chain.unsetLink().run()
  else chain.setLink({ href: /^https?:\/\//.test(url) ? url : `https://${url}`, target: '_blank' }).run()
  closeLinkInput()
}
function removeLink() {
  props.editor.chain().focus().unsetLink().run()
  closeLinkInput()
}
function closeLinkInput() {
  showLinkInput.value = false
  savedSel = null
  props.editor.commands.focus()
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="visible"
      ref="menuEl"
      class="bm"
      :style="{ top: `${menuTop}px`, left: `${menuLeft}px` }"
      @mouseenter="insideMenu = true"
      @mouseleave="insideMenu = false"
      @mousedown.stop
    >
      <!-- ── Main toolbar ── -->
      <div v-show="!showLinkInput" class="bm__bar">
        <button class="bm__btn" :class="{ on: editor.isActive('bold') }"
          title="粗體" @mousedown.prevent @click="cmd(() => editor.chain().focus().toggleBold().run())">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
            <path d="M6 4h8a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z"/>
            <path d="M6 12h9a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z"/>
          </svg>
        </button>

        <button class="bm__btn" :class="{ on: editor.isActive('italic') }"
          title="斜體" @mousedown.prevent @click="cmd(() => editor.chain().focus().toggleItalic().run())">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
            <line x1="19" y1="4" x2="10" y2="4"/><line x1="14" y1="20" x2="5" y2="20"/><line x1="15" y1="4" x2="9" y2="20"/>
          </svg>
        </button>

        <button class="bm__btn" :class="{ on: editor.isActive('underline') }"
          title="底線" @mousedown.prevent @click="cmd(() => editor.chain().focus().toggleUnderline().run())">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
            <path d="M6 4v6a6 6 0 0 0 12 0V4"/><line x1="4" y1="20" x2="20" y2="20"/>
          </svg>
        </button>

        <button class="bm__btn" :class="{ on: editor.isActive('strike') }"
          title="刪除線" @mousedown.prevent @click="cmd(() => editor.chain().focus().toggleStrike().run())">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
            <line x1="4" y1="12" x2="20" y2="12"/>
            <path d="M17.5 6.5C17 5 15.5 4 13 4c-3 0-5 1.5-5 4 0 1.2.5 2.1 1.4 2.8"/>
            <path d="M6.8 17C7.4 18.7 9 20 12 20c3.5 0 5.5-1.8 5.5-4 0-.9-.3-1.7-.8-2.3"/>
          </svg>
        </button>

        <div class="bm__sep"/>

        <!-- Text color -->
        <button class="bm__btn bm__btn--clr" :class="{ on: showColorPicker }"
          title="文字顏色" @mousedown.prevent @click="toggleColorPicker">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M4 20h16"/><path d="M6 16 12 4l6 12"/><path d="M8.5 11h7"/>
          </svg>
          <span class="bm__clr-bar" :style="{ background: activeColor ?? 'var(--text)' }"/>
        </button>

        <div class="bm__sep"/>

        <!-- Inline code -->
        <button class="bm__btn" :class="{ on: editor.isActive('code') }"
          title="行內程式碼" @mousedown.prevent @click="cmd(() => editor.chain().focus().toggleCode().run())">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
          </svg>
        </button>

        <!-- Link -->
        <button class="bm__btn" :class="{ on: editor.isActive('link') }"
          title="超連結" @mousedown.prevent @click="openLinkInput">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
          </svg>
        </button>
      </div>

      <!-- ── Color palette ── -->
      <div v-if="showColorPicker" class="bm__colors">
        <button v-for="c in COLORS" :key="c.label"
          class="bm__swatch" :class="{ active: activeColor === c.value }"
          :title="c.label" @mousedown.prevent @click="applyColor(c.value)">
          <span class="bm__dot"
            :style="c.value ? { background: c.value } : { border: '1.5px solid var(--border2)' }">
            <span v-if="!c.value" class="bm__dot-x">✕</span>
          </span>
        </button>
      </div>

      <!-- ── Link input ── -->
      <div v-if="showLinkInput" class="bm__link">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--text-mid)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0">
          <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
          <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
        </svg>
        <input ref="linkInputEl" v-model="linkInput" class="bm__link-input"
          placeholder="貼上網址…"
          @keydown.enter.prevent="applyLink"
          @keydown.escape.prevent="closeLinkInput" />
        <button class="bm__link-ok" @mousedown.prevent @click="applyLink">確認</button>
        <button v-if="editor.isActive('link')" class="bm__link-rm" @mousedown.prevent @click="removeLink">移除</button>
      </div>
    </div>
  </Teleport>
</template>

<style>
.bm {
  position: fixed;
  z-index: 9999;
  background: var(--surface);
  border: 1px solid var(--border2);
  border-radius: 8px;
  box-shadow: 0 8px 24px var(--shadow);
  overflow: hidden;
  user-select: none;
  pointer-events: auto;
}

.bm__bar {
  display: flex;
  align-items: center;
  padding: 3px 4px;
  gap: 1px;
}

.bm__btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  width: 28px;
  height: 26px;
  border: none;
  background: none;
  border-radius: 5px;
  color: var(--text);
  cursor: pointer;
  transition: background 0.1s, color 0.1s;
  flex-shrink: 0;
}
.bm__btn:hover { background: var(--surface2); }
.bm__btn.on    { background: var(--surface3); color: var(--accent); }

.bm__sep {
  width: 1px;
  height: 16px;
  background: var(--border2);
  margin: 0 2px;
  flex-shrink: 0;
}

.bm__btn--clr { width: 32px; }
.bm__clr-bar  { width: 16px; height: 2.5px; border-radius: 2px; }

/* ── Color palette ── */
.bm__colors {
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 5px 8px 6px;
  border-top: 1px solid var(--border2);
}

.bm__swatch {
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  padding: 3px;
  border-radius: 5px;
  cursor: pointer;
  transition: background 0.1s;
}
.bm__swatch:hover  { background: var(--surface2); }
.bm__swatch.active { background: var(--surface3); }

.bm__dot {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
}
.bm__dot-x { font-size: 9px; color: var(--text-mid); line-height: 1; }

/* ── Link input ── */
.bm__link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-top: 1px solid var(--border2);
}

.bm__link-input {
  flex: 1;
  min-width: 180px;
  background: var(--surface2);
  border: 1px solid var(--border2);
  border-radius: 5px;
  padding: 3px 8px;
  font-size: 12px;
  color: var(--text);
  outline: none;
  font-family: var(--font-ui);
}
.bm__link-input:focus        { border-color: var(--accent-bdr); }
.bm__link-input::placeholder { color: var(--text-mid); }

.bm__link-ok {
  padding: 3px 10px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 5px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  font-family: var(--font-ui);
}
.bm__link-ok:hover { opacity: 0.9; }

.bm__link-rm {
  padding: 3px 8px;
  background: none;
  border: none;
  border-radius: 5px;
  font-size: 12px;
  color: #e57373;
  cursor: pointer;
  white-space: nowrap;
  font-family: var(--font-ui);
}
.bm__link-rm:hover { background: rgba(229,115,115,0.1); }
</style>
