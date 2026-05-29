<template>
  <Transition name="id-fade-t">
    <div v-if="open" class="id-overlay" @click.self="$emit('close')">
      <div class="swm fadeup">
        <button class="id-close" @click="$emit('close')">×</button>

        <!-- Head -->
        <div class="swm__head">
          <span class="eyebrow">SHARE COLLECTION</span>
          <div class="swm-stepper" :data-step="currentStep">
            <div
              class="swm-step"
              :class="{ 'swm-step--done': currentStep > 1, 'swm-step--current': currentStep === 1, 'swm-step--clickable': currentStep > 1 }"
              @click="currentStep > 1 && goToStep(1)"
            >
              <span class="swm-step__circle">
                <svg v-if="currentStep > 1" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
                <template v-else>1</template>
              </span>
              <span class="swm-step__label">選擇來源</span>
            </div>
            <div class="swm-stepper__line" :class="{ active: currentStep > 1 }"></div>
            <div
              class="swm-step"
              :class="{ 'swm-step--done': currentStep > 2, 'swm-step--current': currentStep === 2, 'swm-step--clickable': maxReachedStep >= 2, 'swm-step--locked': maxReachedStep < 2 }"
              @click="maxReachedStep >= 2 && goToStep(2)"
            >
              <span class="swm-step__circle">
                <svg v-if="currentStep > 2" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
                <template v-else>2</template>
              </span>
              <span class="swm-step__label">微調內容</span>
            </div>
            <div class="swm-stepper__line" :class="{ active: currentStep > 2 }"></div>
            <div
              class="swm-step"
              :class="{ 'swm-step--current': currentStep === 3, 'swm-step--clickable': maxReachedStep >= 3, 'swm-step--locked': maxReachedStep < 3 }"
              @click="maxReachedStep >= 3 && goToStep(3)"
            >
              <span class="swm-step__circle">3</span>
              <span class="swm-step__label">設定公開</span>
            </div>
          </div>
        </div>

        <!-- Step 1 — Tag picker -->
        <div v-if="currentStep === 1" class="swm__body">
          <h2 class="swm__title">從哪個標籤建立集合？</h2>
          <p class="swm__desc">系統會把這個標籤底下的所有內容帶入集合，下一步可以微調。</p>
          <div v-if="tagsLoading" class="swm-loading">載入標籤中...</div>
          <div v-else-if="tags.length === 0" class="swm-empty">你還沒有任何標籤，先去存幾篇內容吧。</div>
          <div v-else class="swm-tag-grid">
            <button
              v-for="(tag, i) in tags"
              :key="tag.id"
              class="swm-tag-pick"
              :class="{ sel: selectedTagId === tag.id }"
              @click="selectTag(tag)"
            >
              <span class="swm-dot" :style="{ background: `var(--tag-${tagColor(i)})` }"></span>
              <span class="swm-tag-pick__name">{{ tag.name }}</span>
              <span class="swm-tag-pick__count">{{ tag.item_count }} 筆</span>
              <span v-if="selectedTagId === tag.id" class="swm-tag-pick__check">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
              </span>
            </button>
          </div>
        </div>

        <!-- Step 2 — Item picker -->
        <div v-if="currentStep === 2" class="swm__body">
          <h2 class="swm__title">選擇要包含哪些內容</h2>
          <p class="swm__desc">預設全選，點擊取消勾選你不想公開的項目。</p>
          <div v-if="itemsLoading" class="swm-loading">載入內容中...</div>
          <template v-else>
            <div class="swm-select-all">
              <button class="pill" @click="toggleAllItems">{{ selectedItemIds.size === tagItems.length ? '取消全選' : '全選' }}</button>
              <span style="flex:1;"></span>
              <span class="mono" style="font-size:11px;color:var(--text-mid);">共 {{ tagItems.length }} 筆 · 已選 {{ selectedItemIds.size }}</span>
            </div>
            <div class="swm-clist">
              <div
                v-for="(item, i) in tagItems"
                :key="item.id"
                class="swm-citem"
                :class="{ unsel: !selectedItemIds.has(item.id) }"
                @click="toggleItem(item.id)"
              >
                <span class="swm-checkbox">
                  <svg v-if="selectedItemIds.has(item.id)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
                </span>
                <div class="swm-citem__thumb">
                  <img v-if="item.thumbnail_url" :src="item.thumbnail_url" style="width:100%;height:100%;object-fit:cover;" />
                  <div v-else :class="`placeholder placeholder--${tagColor(i)}`"><div class="placeholder__stripes"></div></div>
                </div>
                <div class="swm-citem__main">
                  <h4 class="swm-citem__title">{{ item.title || item.url }}</h4>
                  <span class="tag-chip tag-chip--a" style="font-size:10px;">{{ sourceLabel(item.source_type) }}</span>
                </div>
              </div>
            </div>
          </template>
        </div>

        <!-- Step 3 — Visibility -->
        <div v-if="currentStep === 3" class="swm__body">
          <h2 class="swm__title">設定這個集合的公開程度</h2>
          <p class="swm__desc">你可以隨時改變公開設定，原本 Fork 過的人不會被回收。</p>
          <div class="swm-vis-options">
            <label v-for="opt in visOptions" :key="opt.value" class="swm-vis-opt" :class="{ sel: visibility === opt.value }" @click="visibility = opt.value">
              <div class="swm-vis-opt__head">
                <span>{{ opt.icon }}</span>
                <span class="swm-vis-opt__title">{{ opt.label }}</span>
                <span class="swm-radio"></span>
              </div>
              <p class="swm-vis-opt__desc">{{ opt.desc }}</p>
            </label>
          </div>
          <div class="swm-form-row">
            <label>集合標題</label>
            <input class="input" v-model="collectionTitle" placeholder="輸入標題..." />
          </div>
        </div>

        <!-- Footer -->
        <div class="swm__foot">
          <template v-if="currentStep === 1">
            <span class="spacer"></span>
            <button class="btn btn--accent" :disabled="!selectedTagId" @click="goToStep2">下一步 →</button>
          </template>
          <template v-else-if="currentStep === 2">
            <span class="mono" style="font-size:11.5px;color:var(--accent);">已選 {{ selectedItemIds.size }} / {{ tagItems.length }} 筆</span>
            <span class="spacer"></span>
            <button class="btn" @click="goToStep(1)">← 上一步</button>
            <button class="btn btn--accent" :disabled="selectedItemIds.size === 0" @click="advanceTo3">下一步 →</button>
          </template>
          <template v-else>
            <button class="btn" @click="goToStep(2)">← 上一步</button>
            <span class="spacer"></span>
            <button class="btn btn--accent btn--lg" :disabled="publishing || !collectionTitle" @click="publish">
              {{ publishing ? '建立中...' : '建立並分享 →' }}
            </button>
          </template>
        </div>
      </div>
    </div>
  </Transition>

  <!-- Success toast -->
  <Transition name="toast">
    <div v-if="done && newCollectionId" class="swm-toast">
      <div class="swm-toast__head">
        <span class="swm-toast__ico">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
        </span>
        <span class="swm-toast__title">集合已建立</span>
        <span style="flex:1;"></span>
        <button style="color:var(--text-dim);font-size:14px;" @click="done = false">×</button>
      </div>
      <div class="swm-toast__actions">
        <NuxtLink :to="`/app/collection/${newCollectionId}`" class="btn btn--accent">前往查看 →</NuxtLink>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import type { Collection, Item, Tag } from '~/types/api'

const props = defineProps<{
  open: boolean
  presetTagId?: string
}>()

const emit = defineEmits<{ close: [] }>()

const authStore = useAuthStore()
const apiFetch = useApiFetch()

const COLORS = ['a', 'b', 'c', 'd', 'e'] as const
function tagColor(i: number) { return COLORS[i % COLORS.length] }

// ── Step state ─────────────────────────────────────────────────────
const currentStep = ref<1 | 2 | 3>(1)
const maxReachedStep = ref(1)

function goToStep(n: 1 | 2 | 3) {
  if (maxReachedStep.value < n) return
  currentStep.value = n
}

function advanceTo3() {
  maxReachedStep.value = Math.max(maxReachedStep.value, 3)
  currentStep.value = 3
}

// ── Tags (step 1) ─────────────────────────────────────────────────
const tags = ref<Tag[]>([])
const tagsLoading = ref(false)
const selectedTagId = ref<string | null>(null)
const selectedTagName = ref('')

watch(() => props.open, async (val) => {
  if (!val) return
  reset()
  if (tags.value.length === 0) {
    tagsLoading.value = true
    try {
      const all = await apiFetch<Tag[]>('/tags/')
      tags.value = all.filter(t => t.item_count > 0)
    } finally {
      tagsLoading.value = false
    }
  }
  if (props.presetTagId) {
    const tag = tags.value.find(t => t.id === props.presetTagId)
    if (tag) await goToStep2WithTag(tag)
  }
})

function selectTag(tag: Tag) {
  selectedTagId.value = tag.id
  selectedTagName.value = tag.name
  collectionTitle.value = tag.name
}

// ── Items (step 2) ────────────────────────────────────────────────
const tagItems = ref<Item[]>([])
const itemsLoading = ref(false)
const selectedItemIds = reactive(new Set<string>())

async function goToStep2WithTag(tag: Tag) {
  selectTag(tag)
  await loadTagItems(tag.id)
}

async function goToStep2() {
  if (!selectedTagId.value) return
  await loadTagItems(selectedTagId.value)
}

async function loadTagItems(tagId: string) {
  maxReachedStep.value = Math.max(maxReachedStep.value, 2)
  currentStep.value = 2
  itemsLoading.value = true
  selectedItemIds.clear()
  try {
    tagItems.value = await apiFetch<Item[]>(`/tags/${tagId}/items`)
    tagItems.value.forEach(item => selectedItemIds.add(item.id))
  } finally {
    itemsLoading.value = false
  }
}

function toggleItem(id: string) {
  if (selectedItemIds.has(id)) selectedItemIds.delete(id)
  else selectedItemIds.add(id)
}

function toggleAllItems() {
  if (selectedItemIds.size === tagItems.value.length) selectedItemIds.clear()
  else tagItems.value.forEach(i => selectedItemIds.add(i.id))
}

function sourceLabel(t: string | null) {
  if (t === 'youtube') return 'YouTube'
  if (t === 'ig') return 'Instagram'
  return '文章'
}

// ── Visibility & publish (step 3) ────────────────────────────────
const visibility = ref<'private' | 'link' | 'public'>('public')
const collectionTitle = ref('')
const publishing = ref(false)
const done = ref(false)
const newCollectionId = ref<string | null>(null)

const visOptions: { value: 'private' | 'link' | 'public'; icon: string; label: string; desc: string }[] = [
  { value: 'private', icon: '🔒', label: '私人',    desc: '只有你自己看得到，連結分享也無效。' },
  { value: 'link',    icon: '🔗', label: '連結分享', desc: '知道連結的人可以查看與 Fork，但不會被搜尋到。' },
  { value: 'public',  icon: '🌐', label: '公開',    desc: '任何人都能搜尋與 Fork。會出現在 Browse、Google 結果中。' },
]

async function publish() {
  if (!collectionTitle.value || publishing.value) return
  publishing.value = true
  try {
    const slug = collectionTitle.value
      .toLowerCase()
      .replace(/[^a-z0-9一-鿿]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 40) + '-' + Math.random().toString(36).slice(2, 8)

    const col = await apiFetch<Collection>('/collections/', {
      method: 'POST',
      body: { title: collectionTitle.value, visibility: visibility.value, slug },
    })

    for (const itemId of selectedItemIds) {
      await apiFetch(`/collections/${col.id}/items?item_id=${itemId}`, { method: 'POST' })
    }

    newCollectionId.value = col.id
    done.value = true
    emit('close')
  } finally {
    publishing.value = false
  }
}

function reset() {
  currentStep.value = 1
  maxReachedStep.value = 1
  selectedTagId.value = null
  selectedTagName.value = ''
  tagItems.value = []
  selectedItemIds.clear()
  collectionTitle.value = ''
  visibility.value = 'public'
  done.value = false
  newCollectionId.value = null
}
</script>

<style>
.swm {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 18px;
  width: 560px;
  max-width: calc(100vw - 32px);
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  position: relative;
  box-shadow: 0 24px 64px -12px var(--shadow);
  overflow: hidden;
}

.swm__head {
  padding: 22px 24px 16px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.swm__head .eyebrow {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--accent);
  letter-spacing: 0.1em;
  display: block;
  margin-bottom: 12px;
}

.swm__body {
  padding: 20px 24px;
  overflow-y: auto;
  flex: 1;
}
.swm__title { font-family: var(--font-brand); font-weight: 600; font-size: 18px; margin: 0 0 5px; }
.swm__desc { font-size: 13px; color: var(--text-mid); margin: 0 0 18px; }

.swm__foot {
  padding: 14px 24px;
  border-top: 1px solid var(--border);
  display: flex; align-items: center; gap: 10px;
  flex-shrink: 0;
}
.swm__foot .spacer { flex: 1; }

/* Stepper */
.swm-stepper { display: flex; align-items: center; }
.swm-step { display: flex; align-items: center; gap: 8px; }
.swm-step__circle {
  width: 26px; height: 26px; border-radius: 50%;
  background: var(--surface3); border: 1.5px solid var(--border2);
  display: inline-flex; align-items: center; justify-content: center;
  font-family: var(--font-mono); font-size: 11px; font-weight: 500;
  color: var(--text-mid); flex-shrink: 0;
}
.swm-step--done .swm-step__circle { background: var(--accent); color: var(--accent-fg); border-color: var(--accent); }
.swm-step--current .swm-step__circle { border-color: var(--accent); color: var(--accent); background: var(--bg); box-shadow: 0 0 0 3px var(--accent-dim); }
.swm-step__label { font-family: var(--font-mono); font-size: 11px; color: var(--text-mid); white-space: nowrap; }
.swm-step--current .swm-step__label { color: var(--text); }
.swm-step--clickable { cursor: pointer; }
.swm-step--locked { opacity: 0.4; }
.swm-stepper__line { flex: 1; height: 1.5px; background: var(--border2); margin: 0 10px; }
.swm-stepper__line.active { background: var(--accent); }

/* Tag grid */
.swm-loading { font-family: var(--font-mono); font-size: 12px; color: var(--text-dim); padding: 16px 0; }
.swm-empty { font-size: 13px; color: var(--text-mid); padding: 12px 0; }

.swm-tag-grid { display: flex; flex-direction: column; gap: 7px; max-height: 340px; overflow-y: auto; scrollbar-width: thin; padding-right: 2px; }
.swm-tag-pick {
  display: flex; align-items: center; gap: 10px;
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 10px; padding: 12px 14px; cursor: pointer;
  transition: all .15s ease; text-align: left; width: 100%;
}
.swm-tag-pick:hover { border-color: var(--border2); }
.swm-tag-pick.sel { background: var(--accent-dim); border-color: var(--accent-bdr); }
.swm-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.swm-tag-pick__name { font-size: 13.5px; font-weight: 500; flex: 1; }
.swm-tag-pick__count { font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); }
.swm-tag-pick__check {
  width: 16px; height: 16px; border-radius: 50%;
  background: var(--accent); color: var(--accent-fg);
  display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0;
}

/* Item list */
.swm-select-all {
  display: flex; align-items: center; gap: 10px; margin-bottom: 10px;
}
.swm-select-all .pill {
  cursor: pointer; padding: 4px 10px;
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 6px; font-family: var(--font-mono); font-size: 11.5px;
  transition: all .15s ease;
}
.swm-select-all .pill:hover { color: var(--text); }

.swm-clist {
  display: flex; flex-direction: column; gap: 5px;
  max-height: 300px; overflow-y: auto; scrollbar-width: thin; padding-right: 2px;
}
.swm-citem {
  display: grid; grid-template-columns: 20px 60px 1fr;
  gap: 10px; align-items: center;
  padding: 9px 10px; background: var(--surface);
  border: 1px solid var(--border); border-radius: 9px;
  cursor: pointer; transition: all .15s ease;
}
.swm-citem:hover { background: var(--surface2); }
.swm-citem.unsel { opacity: 0.4; }
.swm-checkbox {
  width: 16px; height: 16px; border-radius: 4px;
  border: 1.5px solid var(--border2); background: var(--surface);
  display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.swm-citem:not(.unsel) .swm-checkbox { background: var(--accent); border-color: var(--accent); color: var(--accent-fg); }
.swm-checkbox svg { width: 10px; height: 10px; }
.swm-citem__thumb { width: 60px; height: 38px; border-radius: 5px; overflow: hidden; flex-shrink: 0; }
.swm-citem__main { min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.swm-citem__title { font-size: 12.5px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin: 0; }

/* Visibility */
.swm-vis-options { display: flex; flex-direction: column; gap: 8px; margin-bottom: 18px; }
.swm-vis-opt {
  position: relative; background: var(--surface2);
  border: 1px solid var(--border); border-radius: 10px;
  padding: 12px 16px 12px 20px; cursor: pointer; transition: all .15s ease;
}
.swm-vis-opt:hover { background: var(--surface3); }
.swm-vis-opt.sel { background: var(--accent-dim); border-color: var(--accent-bdr); }
.swm-vis-opt.sel::before {
  content: ''; position: absolute; left: 0; top: 10px; bottom: 10px;
  width: 3px; background: var(--accent); border-radius: 2px;
}
.swm-vis-opt__head { display: flex; align-items: center; gap: 8px; margin-bottom: 3px; }
.swm-vis-opt__title { font-size: 13.5px; font-weight: 500; }
.swm-vis-opt__desc { color: var(--text-mid); font-size: 12px; line-height: 1.5; margin: 0; }
.swm-radio {
  margin-left: auto; width: 15px; height: 15px;
  border-radius: 50%; border: 1.5px solid var(--border2); flex-shrink: 0; position: relative;
}
.swm-vis-opt.sel .swm-radio { border-color: var(--accent); }
.swm-vis-opt.sel .swm-radio::after { content: ''; position: absolute; inset: 3px; background: var(--accent); border-radius: 50%; }

.swm-form-row { display: flex; flex-direction: column; gap: 6px; }
.swm-form-row label { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.06em; }

/* Toast */
.swm-toast {
  position: fixed; right: 24px; bottom: 24px; z-index: 500;
  width: 300px; background: var(--surface); border: 1px solid var(--accent-bdr);
  border-radius: 14px; padding: 14px 16px;
  box-shadow: 0 20px 48px -16px var(--shadow);
}
.swm-toast__head { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.swm-toast__ico {
  width: 22px; height: 22px; border-radius: 50%;
  background: var(--accent); color: var(--accent-fg);
  display: inline-flex; align-items: center; justify-content: center;
}
.swm-toast__title { font-size: 13px; font-weight: 500; }
.swm-toast__actions { display: flex; gap: 6px; }
.swm-toast__actions .btn { height: 30px; padding: 0 12px; font-size: 12px; flex: 1; justify-content: center; }

@media (max-width: 640px) {
  .swm { border-radius: 16px 16px 0 0; max-height: 92vh; }
}
</style>
