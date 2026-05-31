<template>
  <div v-if="collection">
    <section class="ch-wrap">
      <div class="ch-mosaic" :class="`ch-mosaic--n${mosaicItems.length}`">
        <div
          v-for="(item, i) in mosaicItems"
          :key="item.id"
          class="tile"
        >
          <img
            v-if="item.thumbnail_url"
            :src="item.thumbnail_url"
            :alt="item.title ?? ''"
            style="width:100%;height:100%;object-fit:cover;"
          />
          <div v-else :class="`placeholder placeholder--${placeholderColors[i % placeholderColors.length]}`">
            <div class="placeholder__stripes"></div>
          </div>
        </div>
      </div>
      <div class="ch-content">
        <div class="ch-author">
          <span class="ch-author__av" :style="avatarStyle">
            <img
              v-if="collection.author_avatar_url"
              :src="collection.author_avatar_url"
              :alt="collection.author_username"
              style="width:100%;height:100%;object-fit:cover;border-radius:50%;"
            />
            <template v-else>{{ authorInitials }}</template>
          </span>
          <span class="ch-author__name">@{{ collection.author_username }}</span>
          <span class="ch-author__suffix">{{ t('share.author_suffix') }}</span>
        </div>
        <h1 class="ch-title">{{ collection.title }}</h1>
        <div class="ch-stats">
          <span class="ch-stat">{{ t('share.stat_items', { count: collection.items.length }) }}</span>
          <span class="ch-stat">{{ t('share.stat_forks', { count: collection.fork_count }) }}</span>
          <span class="ch-stat">{{ t('share.stat_created', { date: createdAgo }) }}</span>
        </div>
      </div>
    </section>

    <div class="cta-bar">
      <span class="ch-author__av" style="width:28px;height:28px;font-size:10px;">
        <img
          v-if="collection.author_avatar_url"
          :src="collection.author_avatar_url"
          style="width:100%;height:100%;object-fit:cover;border-radius:50%;"
        />
        <template v-else>{{ authorInitials }}</template>
      </span>
      <span class="cta-bar__title">{{ collection.title }}</span>
      <span class="cta-bar__sub">{{ t('share.cta_items', { count: collection.items.length }) }} · @{{ collection.author_username }}</span>
      <div class="cta-bar__actions">
        <button class="btn btn--accent" @click="goFork">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="6" cy="3" r="2"/><circle cx="6" cy="21" r="2"/><circle cx="18" cy="12" r="2"/><path d="M6 5v6a4 4 0 0 0 4 4h6M6 13v6"/></svg>
          {{ t('share.fork_all', { count: collection.items.length }) }}
        </button>
      </div>
    </div>

    <section class="content-grid">
      <a
        v-for="(item, i) in collection.items"
        :key="item.id"
        class="icard"
        :href="item.url"
        target="_blank"
        rel="noopener noreferrer"
        @click.prevent="activeItem = item"
      >
        <span class="icard__check">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
        </span>
        <div class="icard__thumb">
          <img
            v-if="item.thumbnail_url"
            :src="item.thumbnail_url"
            :alt="item.title ?? ''"
            style="width:100%;height:100%;object-fit:cover;"
          />
          <div v-else :class="`placeholder placeholder--${placeholderColors[i % placeholderColors.length]}`">
            <div class="placeholder__stripes"></div>
          </div>
          <button
            class="add-btn"
            @click.prevent.stop="onAddClick(item)"
            :title="t('share.add_to_collection')"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </button>
        </div>
        <div class="icard__body">
          <h3 class="icard__title">{{ item.title || item.url }}</h3>
          <div class="icard__foot">
            <span class="tag-chip tag-chip--a">{{ sourceLabel(item.source_type) }}</span>
            <a :href="item.url" target="_blank" rel="noopener noreferrer" @click.stop>{{ t('share.source_link') }}</a>
          </div>
        </div>
      </a>
    </section>

    <!-- item detail modal -->
    <ItemDetailModal :item="activeItem" @close="activeItem = null" />

    <!-- add-to-collection picker -->
    <Transition name="id-fade-t">
      <div v-if="addPickerItem" class="id-overlay" @click.self="addPickerItem = null">
        <div class="add-picker fadeup">
          <button class="id-close" @click="addPickerItem = null">×</button>
          <div class="add-picker__head">{{ t('share.add_to_collection') }}</div>
          <div v-if="!session" class="add-picker__empty">{{ t('share.login_to_add') }}</div>
          <div v-else-if="userCollections.length === 0" class="add-picker__empty">{{ t('share.no_collections') }}</div>
          <ul v-else class="add-picker__list">
            <li
              v-for="col in userCollections"
              :key="col.id"
              class="add-picker__row"
              @click="addToCollection(addPickerItem, col.id)"
            >
              <span class="add-picker__name">{{ col.title }}</span>
              <span class="add-picker__count mono">{{ col.item_count ?? '' }}</span>
            </li>
          </ul>
        </div>
      </div>
    </Transition>

    <!-- fork wizard modal -->
    <Transition name="id-fade-t">
      <div v-if="forkModalOpen" class="id-overlay" @click.self="closeForkModal">
        <div class="fork-modal fadeup">
          <button class="id-close" @click="closeForkModal">×</button>

          <div class="fork-modal__head">
            <span class="eyebrow">FORK TO COLLECTION</span>
            <!-- Stepper -->
            <div class="fork-stepper" :data-step="forkStep">
              <div
                class="fork-step"
                :class="{ 'fork-step--done': forkStep > 1, 'fork-step--current': forkStep === 1, 'fork-step--clickable': forkStep > 1 }"
                @click="forkStep > 1 && (forkStep = 1)"
              >
                <span class="fork-step__circle">
                  <svg v-if="forkStep > 1" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
                  <template v-else>1</template>
                </span>
                <span class="fork-step__label">選擇集合</span>
              </div>
              <div class="fork-stepper__line"></div>
              <div
                class="fork-step"
                :class="{ 'fork-step--current': forkStep === 2, 'fork-step--locked': forkStep < 2 }"
              >
                <span class="fork-step__circle">2</span>
                <span class="fork-step__label">選擇內容</span>
              </div>
            </div>
          </div>

          <!-- Step 1 -->
          <div v-if="forkStep === 1" class="fork-modal__body">
            <h2 class="fork-modal__title">加入哪個集合？</h2>
            <p class="fork-modal__desc">選擇一個你已建立的集合，下一步可以挑選要加入的內容。</p>
            <div v-if="forkCollectionsLoading" class="fork-loading">載入集合中...</div>
            <div v-else-if="forkCollections.length === 0" class="fork-empty">
              你還沒有任何集合。
            </div>
            <div v-else class="fork-col-grid">
              <button
                v-for="col in forkCollections"
                :key="col.id"
                class="fork-col-pick"
                :class="{ sel: forkSelectedCollectionId === col.id }"
                @click="forkSelectedCollectionId = col.id"
              >
                <span class="fork-col-pick__title">{{ col.title }}</span>
                <span class="fork-col-pick__meta mono">⑂ {{ col.fork_count }}</span>
                <span v-if="forkSelectedCollectionId === col.id" class="fork-col-pick__check">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
                </span>
              </button>
            </div>
          </div>

          <!-- Step 2 -->
          <div v-if="forkStep === 2" class="fork-modal__body">
            <h2 class="fork-modal__title">選擇要加入的內容</h2>
            <p class="fork-modal__desc">預設全選，點擊取消勾選不想加入的項目。</p>
            <div class="fork-select-all">
              <button class="pill" @click="forkToggleAll">{{ forkSelectedIds.size === (collection?.items.length ?? 0) ? '取消全選' : '全選' }}</button>
              <span style="flex:1;"></span>
              <span class="mono" style="font-size:11px;color:var(--text-mid);">共 {{ collection?.items.length }} 筆 · 已選 {{ forkSelectedIds.size }}</span>
            </div>
            <div class="fork-clist">
              <div
                v-for="(item, i) in collection?.items ?? []"
                :key="item.id"
                class="fork-citem"
                :class="{ unsel: !forkSelectedIds.has(item.id) }"
                @click="forkToggleItem(item.id)"
              >
                <span class="fork-checkbox">
                  <svg v-if="forkSelectedIds.has(item.id)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
                </span>
                <div class="fork-citem__thumb">
                  <img v-if="item.thumbnail_url" :src="item.thumbnail_url" style="width:100%;height:100%;object-fit:cover;" />
                  <div v-else :class="`placeholder placeholder--${placeholderColors[i % placeholderColors.length]}`"><div class="placeholder__stripes"></div></div>
                </div>
                <div class="fork-citem__main">
                  <h4 class="fork-citem__title">{{ item.title || item.url }}</h4>
                  <span class="tag-chip tag-chip--a" style="font-size:10px;">{{ sourceLabel(item.source_type) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="fork-modal__foot">
            <template v-if="forkStep === 1">
              <span class="spacer"></span>
              <button class="btn btn--accent" :disabled="!forkSelectedCollectionId" @click="forkStep = 2">下一步 →</button>
            </template>
            <template v-else>
              <span class="mono" style="font-size:11.5px;color:var(--accent);">已選 {{ forkSelectedIds.size }} / {{ collection?.items.length }} 筆</span>
              <span class="spacer"></span>
              <button class="btn" @click="forkStep = 1">← 上一步</button>
              <button class="btn btn--accent" :disabled="forkSelectedIds.size === 0 || forkAdding" @click="confirmFork">
                {{ forkAdding ? '加入中...' : `加入 ${forkSelectedIds.size} 筆 →` }}
              </button>
            </template>
          </div>
        </div>
      </div>
    </Transition>

    <section class="rec-section">
      <header class="rec-head">
        <span class="eyebrow">{{ t('share.you_may_like') }}</span>
        <span class="line"></span>
        <NuxtLink to="/app/explore" class="mono" style="font-size:11px; color:var(--text-mid);">{{ t('share.see_all') }}</NuxtLink>
      </header>
      <div class="rec-scroll">
        <NuxtLink v-for="(rec, ri) in recs" :key="rec.slug" class="rec-card" :to="`/share/${rec.slug}`">
          <div class="rec-card__cover">
            <div class="t">
              <img v-if="rec.cover_thumbnails[0]" :src="rec.cover_thumbnails[0]" :alt="rec.title" style="width:100%;height:100%;object-fit:cover;">
              <div v-else :class="`placeholder placeholder--${placeholderColors[ri % placeholderColors.length]}`"><div class="placeholder__stripes"></div></div>
            </div>
            <div class="t">
              <img v-if="rec.cover_thumbnails[1]" :src="rec.cover_thumbnails[1]" :alt="rec.title" style="width:100%;height:100%;object-fit:cover;">
              <div v-else :class="`placeholder placeholder--${placeholderColors[(ri + 2) % placeholderColors.length]}`"><div class="placeholder__stripes"></div></div>
            </div>
          </div>
          <div class="rec-card__body">
            <h4 class="rec-card__title">{{ rec.title }}</h4>
            <div class="rec-card__meta">@{{ rec.author_username }} · {{ rec.item_count }} items · ⑂ {{ rec.fork_count }}</div>
          </div>
        </NuxtLink>
        <div v-if="!recs.length" class="rec-empty">暫無推薦集合</div>
      </div>
    </section>
  </div>

  <div v-else-if="error" class="empty-state" style="padding:80px 32px;text-align:center;">
    <p style="color:var(--text-mid);">{{ t('share.not_found') }}</p>
    <NuxtLink to="/app/explore" class="btn" style="margin-top:16px;">{{ t('share.explore_btn') }}</NuxtLink>
  </div>

  <Transition name="toast">
    <div v-if="toast" class="add-toast">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
      {{ toast }}
    </div>
  </Transition>
</template>

<script setup lang="ts">
import type { CollectionShareItem, CollectionShareRead, CollectionRead, PublicCollectionRead } from '~/types/api'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const config = useRuntimeConfig()
const session = useSupabaseSession()
const slug = route.params.slug as string

const { data: collection, error } = await useAsyncData<CollectionShareRead>(
  `share-${slug}`,
  () => $fetch(`${config.public.apiBase}/share/${slug}`)
)

const { data: recsData } = await useAsyncData<PublicCollectionRead[]>(
  `share-recs-${slug}`,
  () => ($fetch(`${config.public.apiBase}/share/recommendations`, {
    query: { exclude_slug: slug, limit: 8 }
  }) as Promise<PublicCollectionRead[]>).catch(() => [])
)

useHead({
  title: collection.value ? `${collection.value.title} — Vela` : 'Vela',
})

const placeholderColors = ['a', 'b', 'c', 'd', 'e']

// 最多取 5 張做 mosaic；若 items 超過 5 張仍只顯示前 5
const mosaicItems = computed(() => (collection.value?.items ?? []).slice(0, 5))

const authorInitials = computed(() => {
  const name = collection.value?.author_username ?? ''
  return name.slice(0, 2).toUpperCase()
})

const avatarStyle = computed(() => ({
  background: 'linear-gradient(135deg, var(--tag-c), var(--tag-a))',
}))

const createdAgo = computed(() => {
  if (!collection.value) return ''
  const diff = Date.now() - new Date(collection.value.created_at).getTime()
  const days = Math.floor(diff / 86400000)
  if (days === 0) return t('share.date_today')
  if (days === 1) return t('share.date_yesterday')
  if (days < 30) return t('share.date_days_ago', { days })
  if (days < 365) return t('share.date_months_ago', { months: Math.floor(days / 30) })
  return t('share.date_years_ago', { years: Math.floor(days / 365) })
})

function sourceBadge(sourceType: string | null): string {
  if (sourceType === 'youtube') return '▶'
  if (sourceType === 'ig') return 'IG'
  return '⎘'
}

function sourceLabel(sourceType: string | null): string {
  if (sourceType === 'youtube') return 'YouTube'
  if (sourceType === 'ig') return 'Instagram'
  return t('share.source_article')
}

// Item detail drawer
const activeItem = ref<CollectionShareItem | null>(null)

// fork modal state
const forkModalOpen = ref(false)
const forkStep = ref<1 | 2>(1)
const forkCollections = ref<CollectionRead[]>([])
const forkCollectionsLoading = ref(false)
const forkSelectedCollectionId = ref<string | null>(null)
const forkSelectedIds = reactive(new Set<string>())
const forkAdding = ref(false)

function goFork() {
  if (!session.value) {
    router.push('/login')
    return
  }
  openForkModal()
}

async function openForkModal() {
  forkStep.value = 1
  forkSelectedCollectionId.value = null
  forkSelectedIds.clear()
  collection.value?.items.forEach(i => forkSelectedIds.add(i.id))
  forkModalOpen.value = true

  if (forkCollections.value.length === 0) {
    forkCollectionsLoading.value = true
    const token = session.value!.access_token
    forkCollections.value = await $fetch<CollectionRead[]>(`${config.public.apiBase}/collections/`, {
      headers: { Authorization: `Bearer ${token}` },
    }).catch(() => [])
    forkCollectionsLoading.value = false
  }
}

function closeForkModal() {
  forkModalOpen.value = false
}

function forkToggleItem(id: string) {
  if (forkSelectedIds.has(id)) forkSelectedIds.delete(id)
  else forkSelectedIds.add(id)
}

function forkToggleAll() {
  const items = collection.value?.items ?? []
  if (forkSelectedIds.size === items.length) forkSelectedIds.clear()
  else items.forEach(i => forkSelectedIds.add(i.id))
}

async function confirmFork() {
  if (!forkSelectedCollectionId.value || forkAdding.value) return
  forkAdding.value = true
  const colId = forkSelectedCollectionId.value
  try {
    const token = session.value!.access_token
    for (const contentId of forkSelectedIds) {
      await $fetch(`${config.public.apiBase}/collections/${colId}/items/from-public`, {
        method: 'POST',
        query: { content_id: contentId },
        headers: { Authorization: `Bearer ${token}` },
      }).catch(() => {})
    }
    closeForkModal()
    showToast(`已加入 ${forkSelectedIds.size} 筆到集合`)
  } finally {
    forkAdding.value = false
  }
}

const recs = computed(() => recsData.value ?? [])

// add-to-collection
const addPickerItem = ref<CollectionShareItem | null>(null)
const userCollections = ref<CollectionRead[]>([])
const toast = ref<string | null>(null)
let toastTimer: ReturnType<typeof setTimeout> | null = null

function showToast(msg: string) {
  toast.value = msg
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = null }, 2500)
}

async function onAddClick(item: CollectionShareItem) {
  if (!session.value) {
    router.push('/login')
    return
  }
  if (userCollections.value.length === 0) {
    const token = session.value.access_token
    userCollections.value = await $fetch<CollectionRead[]>(`${config.public.apiBase}/collections/`, {
      headers: { Authorization: `Bearer ${token}` },
    }).catch(() => [])
  }
  addPickerItem.value = item
}

async function addToCollection(item: CollectionShareItem, collectionId: string) {
  if (!session.value) return
  const token = session.value.access_token
  const col = userCollections.value.find(c => c.id === collectionId)
  try {
    await $fetch(`${config.public.apiBase}/collections/${collectionId}/items/from-public`, {
      method: 'POST',
      query: { content_id: item.id },
      headers: { Authorization: `Bearer ${token}` },
    })
    addPickerItem.value = null
    showToast(`${t('share.add_to_collection_done')} — ${col?.title ?? ''}`)
  } catch {
    addPickerItem.value = null
    showToast(t('share.add_to_collection_error'))
  }
}
</script>

<style>
/* styles moved to assets/css/collection-view.css */
.ch-wrap {
  position: relative;
  height: 320px;
  margin-bottom: 0;
  overflow: hidden;
}
.ch-mosaic {
  position: absolute; inset: 0;
  display: grid;
  gap: 2px;
}
.ch-mosaic .tile { overflow: hidden; }

/* 1 item: full area */
.ch-mosaic--n1 {
  grid-template-columns: 1fr;
  grid-template-rows: 1fr;
}

/* 2 items: side by side */
.ch-mosaic--n2 {
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr;
}

/* 3 items: 1 large left + 2 stacked right */
.ch-mosaic--n3 {
  grid-template-columns: 2fr 1fr;
  grid-template-rows: 1fr 1fr;
}
.ch-mosaic--n3 .tile:nth-child(1) { grid-row: 1 / span 2; }

/* 4 items: 2x2 */
.ch-mosaic--n4 {
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
}

/* 5 items: original layout */
.ch-mosaic--n5 {
  grid-template-columns: 2fr 1fr 1fr 2fr;
  grid-template-rows: 1fr 1fr;
}
.ch-mosaic--n5 .tile:nth-child(1) { grid-row: 1 / span 2; }
.ch-mosaic--n5 .tile:nth-child(4) { grid-column: 4; grid-row: 1 / span 2; }
.ch-mosaic::after {
  content: '';
  position: absolute; inset: 0;
  background: linear-gradient(180deg, transparent 30%, var(--bg) 95%);
}
.ch-content {
  position: absolute;
  left: 32px; right: 32px;
  bottom: 28px;
  z-index: 2;
  max-width: 720px;
}
.ch-author {
  display: inline-flex; align-items: center; gap: 10px;
  margin-bottom: 12px;
}
.ch-author__av {
  width: 36px; height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--tag-c), var(--tag-a));
  color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
  font-family: var(--font-mono); font-size: 12px; font-weight: 500;
  border: 1px solid var(--border2);
  overflow: hidden;
}
.ch-author__name { font-weight: 500; font-size: 13.5px; }
.ch-author__suffix { font-family: var(--font-mono); font-size: 11px; color: var(--text-mid); margin-left: 4px; }
.ch-title {
  font-family: var(--font-brand);
  font-weight: 700;
  font-size: 36px;
  letter-spacing: -0.02em;
  margin: 0 0 10px;
  line-height: 1.15;
  text-wrap: balance;
}
.ch-stats {
  display: flex; gap: 14px; flex-wrap: wrap;
  font-family: var(--font-mono); font-size: 11.5px;
  color: var(--text-mid);
}
.ch-stats b { color: var(--text); font-weight: 500; }
.ch-stat::after { content: '·'; margin-left: 14px; color: var(--text-dim); }
.ch-stat:last-child::after { display: none; }
.cta-bar {
  position: sticky; top: 52px;
  z-index: 30;
  padding: 12px 32px;
  background: var(--nav-bg);
  backdrop-filter: blur(18px);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 12px;
}
.cta-bar__title { font-family: var(--font-brand); font-weight: 600; font-size: 14px; }
.cta-bar__sub { margin-left: 12px; font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); }
.cta-bar__actions { margin-left: auto; display: flex; gap: 8px; }
.content-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
  padding: 28px 32px 48px;
  max-width: 1400px;
  margin: 0 auto;
}
.icard {
  position: relative;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all .2s ease;
  text-decoration: none;
  color: inherit;
}
.icard:hover { transform: translateY(-3px); border-color: var(--border2); box-shadow: 0 12px 28px -12px var(--shadow); }
.icard__check {
  position: absolute; top: 10px; left: 10px;
  z-index: 3;
  width: 22px; height: 22px;
  border-radius: 6px;
  background: rgba(0,0,0,0.55);
  border: 1.5px solid #fff;
  backdrop-filter: blur(4px);
  display: none; align-items: center; justify-content: center;
  color: #fff;
}
.pick-mode .icard__check { display: inline-flex; }
.icard.sel .icard__check { background: var(--accent); border-color: var(--accent); color: var(--accent-fg); }
.icard__check svg { width: 14px; height: 14px; }
.icard__thumb { height: 130px; position: relative; overflow: hidden; }
.add-btn {
  position: absolute; right: 8px; bottom: 8px;
  width: 28px; height: 28px;
  border-radius: 8px;
  background: rgba(0,0,0,0.55);
  border: 1.5px solid rgba(255,255,255,0.35);
  backdrop-filter: blur(4px);
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  opacity: 0;
  transition: opacity .15s ease, background .15s ease, border-color .15s ease;
}
.add-btn svg { width: 14px; height: 14px; }
.icard:hover .add-btn { opacity: 1; }
.add-btn:hover { background: rgba(0,0,0,0.75); border-color: rgba(255,255,255,0.6); }

.add-toast {
  position: fixed;
  bottom: 28px; right: 28px;
  z-index: 500;
  display: flex; align-items: center; gap: 8px;
  padding: 10px 16px;
  background: var(--surface);
  border: 1px solid var(--border2);
  border-radius: 10px;
  box-shadow: 0 8px 28px -8px var(--shadow);
  font-size: 13px; font-weight: 500;
  color: var(--text);
  pointer-events: none;
}
.add-toast svg { width: 14px; height: 14px; color: var(--accent); flex-shrink: 0; }
.toast-enter-active, .toast-leave-active { transition: opacity .2s ease, transform .2s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(8px); }

.add-picker {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  width: 320px;
  max-width: calc(100vw - 32px);
  padding: 20px;
  position: relative;
  box-shadow: 0 20px 60px -12px var(--shadow);
}
.add-picker__head {
  font-family: var(--font-brand);
  font-weight: 600;
  font-size: 15px;
  margin-bottom: 14px;
  padding-right: 28px;
}
.add-picker__empty {
  font-size: 13px;
  color: var(--text-mid);
  padding: 8px 0;
}
.add-picker__list {
  list-style: none;
  margin: 0; padding: 0;
  display: flex; flex-direction: column; gap: 2px;
}
.add-picker__row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 9px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background .12s;
}
.add-picker__row:hover { background: var(--surface2); }
.add-picker__row--done { background: color-mix(in srgb, var(--accent) 12%, transparent); }
.add-picker__name { font-size: 13.5px; font-weight: 500; }
.add-picker__count { font-size: 11px; color: var(--text-dim); }
.icard__body { padding: 12px 14px 14px; display: flex; flex-direction: column; gap: 10px; }
.icard__title {
  font-size: 13px; font-weight: 500;
  line-height: 1.45; margin: 0;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.icard__foot { display: flex; align-items: center; justify-content: space-between; }
.icard__foot a { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); transition: color .15s ease; }
.icard__foot a:hover { color: var(--accent); }
.rec-section { border-top: 1px solid var(--border); padding: 30px 32px 60px; max-width: 1400px; margin: 0 auto; }
.rec-head { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.rec-head .line { flex: 1; height: 1px; background: var(--border); }
.rec-scroll { display: flex; gap: 14px; overflow-x: auto; padding-bottom: 8px; scrollbar-width: none; }
.rec-scroll::-webkit-scrollbar { display: none; }
.rec-card {
  flex: 0 0 240px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; overflow: hidden;
  transition: all .2s ease; text-decoration: none; color: inherit;
}
.rec-card:hover { transform: translateY(-3px); border-color: var(--border2); }
.rec-card__cover { height: 100px; display: grid; grid-template-columns: 2fr 1fr; gap: 2px; }
.rec-card__cover .t { overflow: hidden; }
.rec-card__body { padding: 12px 14px 14px; }
.rec-card__title { font-family: var(--font-brand); font-weight: 600; font-size: 14px; margin: 0 0 6px; line-height: 1.3; }
.rec-card__meta { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-mid); }
.rec-empty { font-size: 13px; color: var(--text-dim); padding: 20px 0; }

/* ── item detail drawer ── */
.item-drawer {
  position: fixed;
  inset: 0;
  z-index: 400;
  background: rgba(0,0,0,0.45);
  display: flex;
  justify-content: flex-end;
}
.item-drawer__panel {
  width: 440px;
  max-width: 100vw;
  height: 100%;
  background: var(--surface);
  border-left: 1px solid var(--border);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  position: relative;
  box-shadow: -16px 0 48px rgba(0,0,0,0.18);
}
.item-drawer__close {
  position: absolute;
  top: 14px; right: 14px;
  z-index: 2;
  width: 32px; height: 32px;
  border-radius: 8px;
  background: var(--surface2);
  border: 1px solid var(--border);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  color: var(--text-mid);
  transition: background .12s, color .12s;
}
.item-drawer__close:hover { background: var(--bg); color: var(--text); }
.item-drawer__thumb {
  height: 240px;
  flex-shrink: 0;
  position: relative;
  overflow: hidden;
  background: var(--surface2);
}
.item-drawer__badge { bottom: 12px; right: 12px; }
.item-drawer__body {
  padding: 22px 24px 40px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  flex: 1;
}
.item-drawer__title {
  font-family: var(--font-brand);
  font-size: 20px;
  font-weight: 700;
  line-height: 1.3;
  margin: 0;
  letter-spacing: -0.01em;
}
.item-drawer__summary {
  font-size: 13.5px;
  line-height: 1.7;
  color: var(--text-mid);
  margin: 0;
  flex: 1;
}
.item-drawer__cta {
  align-self: flex-start;
  display: flex;
  align-items: center;
  gap: 7px;
  margin-top: 4px;
}

/* drawer transition */
.drawer-enter-active, .drawer-leave-active { transition: opacity .2s ease; }
.drawer-enter-active .item-drawer__panel, .drawer-leave-active .item-drawer__panel { transition: transform .25s cubic-bezier(.32,0,.67,0); }
.drawer-enter-from, .drawer-leave-to { opacity: 0; }
.drawer-enter-from .item-drawer__panel, .drawer-leave-to .item-drawer__panel { transform: translateX(100%); }

/* ── fork wizard modal ── */
.fork-modal {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 18px;
  width: 520px;
  max-width: calc(100vw - 32px);
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  position: relative;
  box-shadow: 0 24px 64px -12px var(--shadow);
  overflow: hidden;
}
.fork-modal__head {
  padding: 22px 24px 16px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.fork-modal__head .eyebrow {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--accent);
  letter-spacing: 0.1em;
  display: block;
  margin-bottom: 12px;
}
.fork-modal__body {
  padding: 20px 24px;
  overflow-y: auto;
  flex: 1;
}
.fork-modal__title { font-family: var(--font-brand); font-weight: 600; font-size: 18px; margin: 0 0 5px; }
.fork-modal__desc { font-size: 13px; color: var(--text-mid); margin: 0 0 18px; }
.fork-modal__foot {
  padding: 14px 24px;
  border-top: 1px solid var(--border);
  display: flex; align-items: center; gap: 10px;
  flex-shrink: 0;
}
.fork-modal__foot .spacer { flex: 1; }

.fork-stepper {
  display: flex; align-items: center; gap: 0;
}
.fork-step { display: flex; align-items: center; gap: 8px; }
.fork-step__circle {
  width: 26px; height: 26px; border-radius: 50%;
  background: var(--surface3); border: 1.5px solid var(--border2);
  display: inline-flex; align-items: center; justify-content: center;
  font-family: var(--font-mono); font-size: 11px; font-weight: 500;
  color: var(--text-mid); flex-shrink: 0;
}
.fork-step--done .fork-step__circle { background: var(--accent); color: var(--accent-fg); border-color: var(--accent); }
.fork-step--current .fork-step__circle { border-color: var(--accent); color: var(--accent); background: var(--bg); box-shadow: 0 0 0 3px var(--accent-dim); }
.fork-step__label { font-family: var(--font-mono); font-size: 11px; color: var(--text-mid); white-space: nowrap; }
.fork-step--current .fork-step__label { color: var(--text); }
.fork-step--clickable { cursor: pointer; }
.fork-step--locked { opacity: 0.4; }
.fork-stepper__line { flex: 1; height: 1.5px; background: var(--border2); margin: 0 10px; }

.fork-loading { font-family: var(--font-mono); font-size: 12px; color: var(--text-dim); padding: 16px 0; }
.fork-empty { font-size: 13px; color: var(--text-mid); padding: 12px 0; }

.fork-col-grid { display: flex; flex-direction: column; gap: 7px; }
.fork-col-pick {
  display: flex; align-items: center; gap: 10px;
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 10px; padding: 12px 14px; cursor: pointer;
  transition: all .15s ease; text-align: left; width: 100%;
}
.fork-col-pick:hover { border-color: var(--border2); }
.fork-col-pick.sel { background: var(--accent-dim); border-color: var(--accent-bdr); }
.fork-col-pick__title { font-size: 13.5px; font-weight: 500; flex: 1; }
.fork-col-pick__meta { font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); }
.fork-col-pick__check {
  width: 16px; height: 16px; border-radius: 50%;
  background: var(--accent); color: var(--accent-fg);
  display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0;
}

.fork-select-all {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 10px;
}
.fork-select-all .pill {
  cursor: pointer; padding: 4px 10px;
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 6px; font-family: var(--font-mono); font-size: 11.5px;
  transition: all .15s ease;
}
.fork-select-all .pill:hover { color: var(--text); }

.fork-clist { display: flex; flex-direction: column; gap: 5px; max-height: 340px; overflow-y: auto; scrollbar-width: thin; padding-right: 2px; }
.fork-citem {
  display: grid; grid-template-columns: 20px 60px 1fr;
  gap: 10px; align-items: center;
  padding: 9px 10px; background: var(--surface);
  border: 1px solid var(--border); border-radius: 9px;
  cursor: pointer; transition: all .15s ease;
}
.fork-citem:hover { background: var(--surface2); }
.fork-citem.unsel { opacity: 0.4; }
.fork-checkbox {
  width: 16px; height: 16px; border-radius: 4px;
  border: 1.5px solid var(--border2); background: var(--surface);
  display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.fork-citem:not(.unsel) .fork-checkbox { background: var(--accent); border-color: var(--accent); color: var(--accent-fg); }
.fork-checkbox svg { width: 10px; height: 10px; }
.fork-citem__thumb { width: 60px; height: 38px; border-radius: 5px; overflow: hidden; flex-shrink: 0; }
.fork-citem__main { min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.fork-citem__title { font-size: 12.5px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin: 0; }

@media (max-width: 640px) {
  .fork-modal { border-radius: 16px 16px 0 0; max-height: 90vh; }
  .id-overlay { align-items: flex-end; }
}

@media (max-width: 640px) {
  .item-drawer { align-items: flex-end; justify-content: stretch; }
  .item-drawer__panel { width: 100%; height: 85vh; border-left: none; border-top: 1px solid var(--border); border-radius: 16px 16px 0 0; }
  .item-drawer__thumb { height: 180px; }
}
@media (max-width: 768px) {
  .ch-content { left: 18px; right: 18px; bottom: 18px; }
  .ch-title { font-size: 24px; }
  .cta-bar { padding: 10px 16px; flex-wrap: wrap; }
  .cta-bar__actions { width: 100%; }
  .content-grid { padding: 20px 16px 40px; gap: 10px; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); }
  .rec-section { padding: 24px 16px 40px; }
}
</style>
