<script setup lang="ts">
import type { UsageSummary } from '~/types/api'
useHead({ title: 'Garner — 我的知識庫' })

const apiFetch = useApiFetch()
const itemStore = useItemStore()
const { getItemTags } = useItems()
const { activeItemId, open: openModal } = useItemModal()
const { t } = useI18n()


const loading = ref(true)
const loadError = ref(false)
const quota = ref<UsageSummary | null>(null)

// URL quick-save (empty state CTA)
const newUrl = ref('')
const saving = ref(false)
const saveError = ref('')

const route = useRoute()
const router = useRouter()
const currentView = computed(() => (route.query.view as string) || 'tags')

async function refreshTags(itemId: string) {
  const tags = await getItemTags(itemId)
  const idx = itemStore.items.findIndex(i => i.id === itemId)
  if (idx !== -1) itemStore.items[idx] = { ...itemStore.items[idx], tags }
}

async function quickSave() {
  const url = newUrl.value.trim()
  if (!url) return
  saving.value = true
  saveError.value = ''
  try {
    await itemStore.add({ url })
    newUrl.value = ''
  } catch (err: any) {
    // 原本指向 home.error / home.error_quota_full，但這兩個 key 不存在，
    // 存入失敗時使用者看到的是字面字串「home.error」。正確的在 add.* 命名空間。
    if (err?.response?.status === 429) {
      saveError.value = t('add.error_quota_full')
    } else {
      saveError.value = t('add.error')
    }
  } finally {
    saving.value = false
  }
}

// Refresh tags when item modal is closed
watch(activeItemId, async (newId, oldId) => {
  if (!newId && oldId) {
    await refreshTags(oldId)
    if (route.query.item) {
      const { item: _removed, ...rest } = route.query
      router.replace({ query: rest })
    }
  }
})

async function loadInitial() {
  loading.value = true
  loadError.value = false
  try {
    await Promise.all([
      itemStore.load(),
      apiFetch<UsageSummary>('/quota/me').then(q => { quota.value = q }).catch(() => {}),
    ])
    if (route.query.item) openModal(route.query.item as string)
  } catch {
    // 之前這裡沒有 try/catch，itemStore.load() 一 reject 就讓 loading 永遠停在 true，
    // 而且 template 沒有錯誤分支，使用者只會看到永久的「載入中」而且沒有出路。
    loadError.value = true
  } finally {
    loading.value = false
  }
}

onMounted(loadInitial)
</script>

<template>
  <main class="shell">
    <!-- Loading -->
    <div v-if="loading" class="loading-state">{{ t('home.loading') }}</div>

    <!-- Load failed: 給使用者一條出路，不要只是停在載入中 -->
    <div v-else-if="loadError" class="loading-state">
      <p>{{ t('home.load_failed') }}</p>
      <button class="btn btn--accent" @click="loadInitial">{{ t('home.retry') }}</button>
    </div>

    <!-- Empty: Ghost Preview + CTA -->
    <template v-else-if="itemStore.totalAll === 0">
      <section class="empty-state fadeup">
        <div class="placeholder placeholder--b empty-state__art">
          <div class="placeholder__stripes"/>
        </div>
        <div class="empty-state__body">
          <span class="empty-state__eyebrow">WELCOME TO GARNER</span>
          <h1 class="empty-state__title">你的知識庫還是空的</h1>
          <p class="empty-state__desc">存入第一筆內容，知識庫就會開始自動成長。</p>
          <div class="cta-input-row">
            <input
              v-model="newUrl"
              class="cta-input"
              placeholder="貼入任何 YouTube 或網頁 URL..."
              :disabled="saving"
              @keydown.enter="quickSave"
            >
            <button class="btn btn--accent" :disabled="saving" @click="quickSave">
              {{ saving ? '存入中...' : '存入' }}
            </button>
          </div>
          <p v-if="saveError" class="cta-error">{{ saveError }}</p>
          <div class="cta-divider"><span>或</span></div>
          <NuxtLink to="/app/connected" class="btn cta-ext-btn">設置極速存入 →</NuxtLink>
        </div>
      </section>
    </template>

    <!-- Populated -->
    <template v-else>
      <div class="page-header">
        <h1 class="page-header__title">{{ t('home.title') }}</h1>
        <HomeViewSwitcher :search-enabled="quota?.search_enabled ?? false" />
      </div>
      <HomeTagView v-if="currentView === 'tags'" />
      <HomeMapView v-else-if="currentView === 'map'" />
      <HomeSemanticSearchView v-else-if="currentView === 'semantic'" />
    </template>

    <div class="shell__spacer"/>
  </main>

  <HomeChatFab />
</template>
