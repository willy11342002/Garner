<script setup lang="ts">
import { NodeViewWrapper, NodeViewContent } from '@tiptap/vue-3'

defineProps<{
  node: any
  updateAttributes: (attrs: Record<string, unknown>) => void
}>()

const LANGUAGES: { value: string; label: string }[] = [
  { value: 'bash',       label: 'Bash' },
  { value: 'c',          label: 'C' },
  { value: 'cpp',        label: 'C++' },
  { value: 'csharp',     label: 'C#' },
  { value: 'css',        label: 'CSS' },
  { value: 'go',         label: 'Go' },
  { value: 'html',       label: 'HTML' },
  { value: 'java',       label: 'Java' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'json',       label: 'JSON' },
  { value: 'kotlin',     label: 'Kotlin' },
  { value: 'markdown',   label: 'Markdown' },
  { value: 'python',     label: 'Python' },
  { value: 'ruby',       label: 'Ruby' },
  { value: 'rust',       label: 'Rust' },
  { value: 'sql',        label: 'SQL' },
  { value: 'swift',      label: 'Swift' },
  { value: 'typescript', label: 'TypeScript' },
  { value: 'xml',        label: 'XML' },
  { value: 'yaml',       label: 'YAML' },
]

function onLangChange(e: Event, updateAttributes: (a: Record<string, unknown>) => void) {
  const val = (e.target as HTMLSelectElement).value
  updateAttributes({ language: val || null })
}
</script>

<template>
  <NodeViewWrapper class="cb-wrap">
    <!-- Language selector -->
    <div class="cb-header" contenteditable="false">
      <select
        class="cb-lang"
        :value="node.attrs.language ?? ''"
        @change="(e) => onLangChange(e, updateAttributes)"
      >
        <option value="">自動偵測</option>
        <option v-for="l in LANGUAGES" :key="l.value" :value="l.value">
          {{ l.label }}
        </option>
      </select>
    </div>

    <!-- Code content -->
    <pre class="cb-pre"><NodeViewContent as="code" class="cb-code" /></pre>
  </NodeViewWrapper>
</template>

<style scoped>
.cb-wrap {
  background: #1e1e2e;
  border-radius: 8px;
  margin: 0.6em 0 1em;
  overflow: hidden;
}

.cb-header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding: 5px 10px;
  border-bottom: 1px solid rgba(205, 214, 244, 0.07);
}

.cb-lang {
  background: transparent;
  border: none;
  color: #6c7086;
  font-size: 11px;
  font-family: 'Fira Code', 'JetBrains Mono', monospace;
  cursor: pointer;
  outline: none;
  padding: 2px 2px;
  border-radius: 3px;
  transition: color 0.15s;
  appearance: auto;
}

.cb-lang:hover { color: #cdd6f4; }

.cb-lang option {
  background: #1e1e2e;
  color: #cdd6f4;
}

.cb-pre {
  background: none;
  margin: 0;
  padding: 0.85rem 1.2rem 1rem;
  overflow-x: auto;
  font-family: 'Fira Code', 'Cascadia Code', 'JetBrains Mono', monospace;
  font-size: 0.82rem;
  line-height: 1.7;
}

.cb-pre :deep(.cb-code) {
  background: none;
  color: #cdd6f4;
  padding: 0;
  font-size: inherit;
  font-family: inherit;
}
</style>
