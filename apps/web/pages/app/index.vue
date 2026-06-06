<script setup lang="ts">
import type { Tag } from '~/types/api'
useHead({ title: 'Garner — 我的知識庫' })

const itemStore = useItemStore()
const { getItemTags, getPendingReview } = useItems()
const { pendingItems } = usePendingItems()
const { activeItemId } = useItemModal()
const { t } = useI18n()


const loading = ref(true)
const itemTagsMap = ref<Record<string, Tag[]>>({})

// URL quick-save (empty state CTA)
const newUrl = ref('')
const saving = ref(false)
const saveError = ref('')

const route = useRoute()
const currentView = computed(() => (route.query.view as string) || 'tags')

// Share wizard modal
const shareModalOpen = ref(false)
const shareModalTagId = ref<string | undefined>(undefined)

function openShareModal(tagId: string) {
  shareModalTagId.value = tagId
  shareModalOpen.value = true
}

async function refreshTags(itemId: string) {
  itemTagsMap.value = { ...itemTagsMap.value, [itemId]: await getItemTags(itemId) }
}

async function quickSave() {
  const url = newUrl.value.trim()
  if (!url) return
  saving.value = true
  saveError.value = ''
  try {
    const item = await itemStore.add({ url })
    newUrl.value = ''
    itemTagsMap.value[item.id] = await getItemTags(item.id)
  } catch (err: any) {
    if (err?.response?.status === 429) {
      saveError.value = t('home.error_quota_full')
    } else {
      saveError.value = t('home.error')
    }
  } finally {
    saving.value = false
  }
}

watch(() => itemStore.recentlyProcessed, async (itemId) => {
  if (!itemId) return
  await refreshTags(itemId)
})

// Refresh tags when item modal is closed
watch(activeItemId, async (newId, oldId) => {
  if (!newId && oldId) await refreshTags(oldId)
})

onMounted(async () => {
  const [, pending] = await Promise.all([itemStore.load(), getPendingReview()])
  pendingItems.value = pending
  for (const item of itemStore.items) {
    itemTagsMap.value[item.id] = item.tags
  }
  loading.value = false
})
</script>

<template>
  <main class="shell">
    <!-- Loading -->
    <div v-if="loading" class="loading-state">載入中...</div>

    <!-- Empty: Ghost Preview + CTA -->
    <template v-else-if="itemStore.items.length === 0">
      <section class="empty-state fadeup">
        <div class="placeholder placeholder--b empty-state__art">
          <div class="placeholder__stripes"></div>
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
            />
            <button class="btn btn--accent" :disabled="saving" @click="quickSave">
              {{ saving ? '存入中...' : '存入' }}
            </button>
          </div>
          <p v-if="saveError" class="cta-error">{{ saveError }}</p>
          <div class="cta-divider"><span>或</span></div>
          <a href="#" class="btn cta-ext-btn">安裝 Chrome Extension →</a>
        </div>
      </section>
    </template>

    <!-- Populated -->
    <template v-else>
      <HomePendingSection @item-tags-updated="refreshTags" />
      <div class="page-header">
        <h1 class="page-header__title">{{ t('home.title') }}</h1>
        <HomeViewSwitcher />
      </div>
      <HomeTagView
        v-if="currentView === 'tags'"
        :item-tags-map="itemTagsMap"
        @open-share="openShareModal"
      />
      <HomeMapView v-else-if="currentView === 'map'" />
      <HomeSemanticSearchView v-else-if="currentView === 'semantic'" />
    </template>

    <LayoutAppFooter />
  </main>

  <ShareWizardModal
    :open="shareModalOpen"
    :preset-tag-id="shareModalTagId"
    @close="shareModalOpen = false"
  />
</template>
