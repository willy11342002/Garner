<script setup lang="ts">
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'

const props = defineProps<{
  modelValue: Record<string, unknown> | null | undefined
  readonly?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: Record<string, unknown>]
}>()

const editor = useEditor({
  extensions: [StarterKit],
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

onBeforeUnmount(() => editor.value?.destroy())
</script>

<template>
  <EditorContent :editor="editor" class="tiptap-wrap" :class="{ 'tiptap-wrap--readonly': readonly, 'tiptap-wrap--edit': !readonly }" />
</template>

<style scoped>
.tiptap-wrap {
  color: var(--text);
  font-family: var(--font-ui);
  font-size: 0.9rem;
  line-height: 1.75;
}

/* prose styles injected into the ProseMirror element */
.tiptap-wrap :deep(.ProseMirror) {
  outline: none;
}

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

/* edit mode border */
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
</style>
