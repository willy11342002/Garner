<template>
  <main class="ex-pane">
    <div class="browse-bar">
      <div class="browse-search">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
        <input v-model="searchQuery" type="text" placeholder="搜尋公開集合、主題、或使用者...">
      </div>
      <div class="filter-pills">
        <button class="pill" :class="{ 'pill--active': activeTag === null }" @click="setTag(null)">All</button>
        <button
          v-for="t in userTags.slice(0, 4)"
          :key="t.id"
          class="pill"
          :class="{ 'pill--active': activeTag === t.name }"
          @click="setTag(t.name)"
        >{{ t.name }}</button>
      </div>
    </div>

    <!-- loading skeletons -->
    <div v-if="pending" class="col-grid">
      <div v-for="n in 6" :key="n" class="col-card col-card--skeleton">
        <div class="col-card__cover col-card__cover--skel"></div>
        <div class="col-card__body">
          <div class="skel-line skel-line--title"></div>
          <div class="skel-line skel-line--desc"></div>
          <div class="skel-line skel-line--desc" style="width:60%"></div>
        </div>
      </div>
    </div>

    <!-- results -->
    <div v-else-if="collections.length" class="col-grid">
      <NuxtLink
        v-for="(col, idx) in collections"
        :key="col.id"
        class="col-card"
        :to="`/share/${col.slug}`"
      >
        <div class="col-card__cover">
          <div
            v-for="ti in 3"
            :key="ti"
            class="tile"
          >
            <img
              v-if="col.cover_thumbnails[ti - 1]"
              :src="col.cover_thumbnails[ti - 1]!"
              :alt="col.title"
              style="width:100%;height:100%;object-fit:cover;"
            >
            <div v-else :class="`placeholder placeholder--${placeholderColor(idx, ti - 1)}`">
              <div class="placeholder__stripes"></div>
            </div>
          </div>
          <span class="col-card__count">{{ col.item_count }} items</span>
          <button class="btn btn--accent col-card__fork" @click.prevent="forkCol(col.slug)">⑂ Fork</button>
        </div>
        <div class="col-card__body">
          <h3 class="col-card__title">{{ col.title }}</h3>
          <div class="col-card__user">
            <span class="col-avatar" :style="avatarStyle(col, idx)">
              <img v-if="col.author_avatar_url" :src="col.author_avatar_url" :alt="col.author_username" style="width:100%;height:100%;object-fit:cover;border-radius:50%">
              <template v-else>{{ initials(col.author_username) }}</template>
            </span>
            <span>@{{ col.author_username }}</span>
            <span style="color:var(--text-dim)">· {{ timeAgo(col.created_at) }}</span>
          </div>
          <div class="col-card__foot">
            <span v-if="col.source_tag_name" class="tag-chip tag-chip--a">{{ col.source_tag_name }}</span>
            <span class="col-card__forks">⑂ {{ col.fork_count }} forks</span>
          </div>
        </div>
      </NuxtLink>
    </div>

    <!-- empty -->
    <div v-else class="browse-empty">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="40" height="40"><path d="M21 21l-4.35-4.35M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16z"/></svg>
      <p>找不到符合的公開集合</p>
    </div>
  </main>
</template>

<script setup lang="ts">
import type { PublicCollectionRead, Tag } from '~/types/api'
definePageMeta({ ssr: false })
useHead({ title: 'Garner — 公開集合' })

const PLACEHOLDER_COLORS = ['a', 'b', 'c', 'd', 'e', 'accent']
const AVATAR_GRADIENTS = [
  'linear-gradient(135deg,var(--tag-a),var(--tag-c))',
  'linear-gradient(135deg,var(--tag-b),var(--tag-d))',
  'linear-gradient(135deg,var(--tag-c),var(--tag-a))',
  'linear-gradient(135deg,var(--tag-e),var(--tag-d))',
  'linear-gradient(135deg,var(--tag-d),var(--tag-b))',
  'linear-gradient(135deg,var(--tag-a),var(--tag-e))',
]

const apiFetch = useApiFetch()
const searchQuery = ref('')
const activeTag = ref<string | null>(null)
const collections = ref<PublicCollectionRead[]>([])
const pending = ref(false)
const userTags = ref<Tag[]>([])

async function fetchUserTags() {
  try {
    userTags.value = await apiFetch<Tag[]>('/tags/')
  } catch {
    userTags.value = []
  }
}

let debounceTimer: ReturnType<typeof setTimeout>

async function fetchCollections() {
  pending.value = true
  try {
    const params: Record<string, string> = {}
    if (searchQuery.value.trim()) params.q = searchQuery.value.trim()
    if (activeTag.value) params.tag = activeTag.value
    const qs = new URLSearchParams(params).toString()
    collections.value = await apiFetch<PublicCollectionRead[]>(`/explore/browse${qs ? '?' + qs : ''}`)
  } catch {
    collections.value = []
  } finally {
    pending.value = false
  }
}

watch(searchQuery, () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(fetchCollections, 350)
})

function setTag(tag: string | null) {
  activeTag.value = tag
  fetchCollections()
}

function placeholderColor(colIdx: number, tileIdx: number) {
  return PLACEHOLDER_COLORS[(colIdx * 3 + tileIdx) % PLACEHOLDER_COLORS.length]
}

function avatarStyle(col: PublicCollectionRead, idx: number) {
  if (col.author_avatar_url) return {}
  return { background: AVATAR_GRADIENTS[idx % AVATAR_GRADIENTS.length] }
}

function initials(username: string) {
  return username.slice(0, 2).toUpperCase()
}

function timeAgo(isoDate: string) {
  const diff = Date.now() - new Date(isoDate).getTime()
  const days = Math.floor(diff / 86400000)
  if (days === 0) return 'today'
  if (days === 1) return '1d ago'
  if (days < 30) return `${days}d ago`
  const months = Math.floor(days / 30)
  return `${months}mo ago`
}

async function forkCol(slug: string) {
  // navigate to share page where fork dialog is handled
  await navigateTo(`/share/${slug}`)
}

onMounted(() => {
  fetchUserTags()
  fetchCollections()
})
</script>

<style>
.browse-bar { display: flex; gap: 10px; margin-bottom: 22px; }
.browse-search { flex: 1; position: relative; }
.browse-search input { width: 100%; height: 44px; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 0 16px 0 42px; font-size: 13.5px; color: var(--text); outline: none; }
.browse-search input:focus { border-color: var(--accent-bdr); box-shadow: 0 0 0 3px var(--accent-dim); }
.browse-search svg { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); width: 16px; height: 16px; color: var(--text-mid); }
.filter-pills { display: flex; gap: 6px; flex-wrap: wrap; }
.pill { font-family: var(--font-mono); font-size: 11.5px; padding: 8px 14px; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; color: var(--text-mid); cursor: pointer; transition: all .15s ease; }
.pill:hover { color: var(--text); }
.pill--active { background: var(--accent-dim); color: var(--accent); border-color: var(--accent-bdr); }
.col-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.col-card { position: relative; background: var(--surface); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; transition: all .2s ease; cursor: pointer; }
.col-card:hover { transform: translateY(-4px); border-color: var(--border2); box-shadow: 0 14px 32px -14px var(--shadow); }
.col-card:hover .col-card__fork { opacity: 1; transform: translateY(0); }
.col-card__cover { height: 130px; display: grid; grid-template-columns: 2fr 1fr; grid-template-rows: 1fr 1fr; gap: 2px; position: relative; background: var(--surface2); }
.col-card__cover .tile { overflow: hidden; }
.col-card__cover .tile:nth-child(1) { grid-row: 1 / span 2; }
.col-card__cover::after { content: ''; position: absolute; inset: 0; background: linear-gradient(180deg, transparent 60%, rgba(0,0,0,0.55)); pointer-events: none; }
.col-card__cover--skel { background: var(--surface2); animation: skel-pulse 1.4s ease infinite; }
.col-card__count { position: absolute; right: 12px; bottom: 10px; z-index: 2; font-family: var(--font-mono); font-size: 10.5px; color: #fff; }
.col-card__fork { position: absolute; top: 12px; right: 12px; z-index: 3; opacity: 0; transform: translateY(-4px); transition: all .2s ease; height: 30px; padding: 0 12px; font-size: 11.5px; }
.col-card__body { padding: 14px 16px 16px; display: flex; flex-direction: column; gap: 10px; }
.col-card__title { font-family: var(--font-brand); font-weight: 600; font-size: 15px; margin: 0; line-height: 1.35; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.col-card__user { display: flex; align-items: center; gap: 8px; font-family: var(--font-mono); font-size: 11px; color: var(--text-mid); }
.col-avatar { width: 22px; height: 22px; border-radius: 50%; flex-shrink: 0; background: linear-gradient(135deg, var(--tag-a), var(--tag-c)); display: inline-flex; align-items: center; justify-content: center; color: #fff; font-size: 9px; overflow: hidden; }
.col-card__foot { display: flex; align-items: center; gap: 6px; padding-top: 10px; border-top: 1px solid var(--border); }
.col-card__forks { margin-left: auto; font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); }
.col-card--skeleton { pointer-events: none; }
.skel-line { background: var(--surface2); border-radius: 6px; height: 14px; animation: skel-pulse 1.4s ease infinite; }
.skel-line--title { width: 70%; height: 16px; }
.skel-line--desc { width: 100%; margin-top: 6px; }
@keyframes skel-pulse { 0%,100%{opacity:.6} 50%{opacity:1} }
.browse-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; padding: 80px 0; color: var(--text-dim); }
.browse-empty p { font-size: 13px; }

@media (max-width: 980px) { .col-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 640px) { .col-grid { grid-template-columns: 1fr; } .browse-bar { flex-direction: column; } }
</style>
