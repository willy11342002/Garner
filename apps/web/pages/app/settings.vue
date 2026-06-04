<script setup lang="ts">
useHead({ title: 'Vela — 設置' })
const { t } = useI18n()
const supabaseUser = useSupabaseUser()
const authStore = useAuthStore()

const avatarUrl = computed(() =>
  authStore.user?.avatar_url
  ?? supabaseUser.value?.user_metadata?.avatar_url
  ?? null
)
const email = computed(() => authStore.user?.email ?? supabaseUser.value?.email ?? '—')
const displayName = computed(() => authStore.user?.username ?? supabaseUser.value?.user_metadata?.name ?? '—')

const PROVIDER_LABELS: Record<string, string> = {
  google: 'Google',
  github: 'GitHub',
  email: 'Email',
}
const providerName = computed(() => {
  const meta = supabaseUser.value?.app_metadata
  const providers: string[] = meta?.providers ?? (meta?.provider ? [meta.provider] : [])
  return providers.map(p => PROVIDER_LABELS[p] ?? p).join(' · ') || '—'
})

const initials = computed(() => {
  const name = authStore.user?.username ?? '?'
  return name.slice(0, 2).toUpperCase()
})

// ── Explore settings ──
const editAllowPublicChain = ref(false)
const isExploreChanged = computed(() => editAllowPublicChain.value !== (authStore.user?.allow_public_chain ?? false))
const isSavingExplore = ref(false)
const exploreStatus = ref<'' | 'success' | 'error'>('')

watch(
  () => authStore.user?.allow_public_chain,
  (val) => { editAllowPublicChain.value = val ?? false },
  { immediate: true },
)

async function saveExplore() {
  if (isSavingExplore.value) return
  isSavingExplore.value = true
  exploreStatus.value = ''
  try {
    await authStore.updateProfile({ allow_public_chain: editAllowPublicChain.value })
    exploreStatus.value = 'success'
    setTimeout(() => { exploreStatus.value = '' }, 2500)
  } catch {
    exploreStatus.value = 'error'
  } finally {
    isSavingExplore.value = false
  }
}

// ── Delete account ──
const showDeleteDialog = ref(false)
const deleteConfirmInput = ref('')
const isDeleting = ref(false)

const deleteConfirmed = computed(() => deleteConfirmInput.value === 'DELETE')

async function confirmDelete() {
  if (!deleteConfirmed.value || isDeleting.value) return
  isDeleting.value = true
  try {
    await authStore.deleteAccount()
    await navigateTo('/')
  } finally {
    isDeleting.value = false
  }
}

function openDeleteDialog() {
  deleteConfirmInput.value = ''
  showDeleteDialog.value = true
}
</script>

<template>
  <main class="shell shell--narrow settings-page fadeup">
    <div class="settings-layout">

      <!-- Content -->
      <div class="settings-content">

        <!-- Profile section -->
        <section class="settings-section">
          <div class="settings-card">
            <div class="settings-card__head">
              <h2 class="settings-card__title">{{ t('settings.profile.title') }}</h2>
            </div>
            <div class="settings-card__body">

              <!-- Avatar -->
              <div class="profile-avatar-row">
                <div class="profile-avatar profile-avatar--lg">
                  <img v-if="avatarUrl" :src="avatarUrl" :alt="displayName" referrerpolicy="no-referrer" />
                  <span v-else>{{ initials }}</span>
                </div>
                <div class="profile-avatar-meta">
                  <p class="profile-name-sm">{{ displayName }}</p>
                  <p class="profile-email-sm">{{ email }}</p>
                  <p class="profile-provider-sm">{{ providerName }}</p>
                </div>
              </div>

            </div>
          </div>
        </section>

        <!-- Explore section -->
        <section class="settings-section">
          <div class="settings-card">
            <div class="settings-card__head">
              <h2 class="settings-card__title">{{ t('settings.explore.title') }}</h2>
              <div class="settings-card__head-actions">
                <p v-if="exploreStatus === 'error'" class="save-error">{{ t('settings.profile.save_error') }}</p>
                <button
                  class="btn-save"
                  :class="{ 'btn-save--success': exploreStatus === 'success' }"
                  :disabled="isSavingExplore || !isExploreChanged"
                  @click="saveExplore"
                >
                  <template v-if="exploreStatus === 'success'">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="13" height="13">
                      <polyline points="20 6 9 17 4 12"/>
                    </svg>
                    {{ t('settings.profile.save_success') }}
                  </template>
                  <template v-else>
                    {{ isSavingExplore ? t('settings.profile.saving') : t('settings.profile.save') }}
                  </template>
                </button>
              </div>
            </div>
            <div class="settings-card__body">
              <div class="settings-toggle-row settings-field settings-field--last">
                <div class="settings-toggle-info">
                  <span class="settings-field__label">{{ t('settings.explore.public_chain_label') }}</span>
                  <span class="settings-toggle-desc">{{ t('settings.explore.public_chain_desc') }}</span>
                </div>
                <button
                  class="toggle-btn"
                  :class="{ 'toggle-btn--on': editAllowPublicChain }"
                  :disabled="isSavingExplore"
                  @click="editAllowPublicChain = !editAllowPublicChain"
                >
                  <span class="toggle-thumb" />
                </button>
              </div>
            </div>
          </div>
        </section>

        <!-- Danger Zone -->
        <section class="settings-section">
          <div class="settings-card settings-card--danger">
            <div class="settings-card__head">
              <h2 class="settings-card__title settings-card__title--danger">{{ t('settings.danger.title') }}</h2>
            </div>
            <div class="settings-card__body danger-body">
              <p class="danger-desc">{{ t('settings.danger.delete_desc') }}</p>
              <button class="btn-delete-account" @click="openDeleteDialog">
                {{ t('settings.danger.delete_button') }}
              </button>
            </div>
          </div>
        </section>

      </div>
    </div>
  </main>

  <!-- Delete confirmation dialog -->
  <Teleport to="body">
    <div v-if="showDeleteDialog" class="delete-overlay" @click.self="showDeleteDialog = false">
      <div class="delete-dialog">
        <h3 class="delete-dialog__title">{{ t('settings.danger.confirm_title') }}</h3>
        <p class="delete-dialog__desc">{{ t('settings.danger.confirm_desc') }}</p>
        <label class="delete-dialog__label">{{ t('settings.danger.confirm_input_label') }}</label>
        <input
          v-model="deleteConfirmInput"
          class="delete-dialog__input"
          :placeholder="t('settings.danger.confirm_input_placeholder')"
          autocomplete="off"
          spellcheck="false"
        />
        <div class="delete-dialog__actions">
          <button class="btn-cancel" @click="showDeleteDialog = false">
            {{ t('settings.danger.cancel') }}
          </button>
          <button
            class="btn-confirm-delete"
            :disabled="!deleteConfirmed || isDeleting"
            @click="confirmDelete"
          >
            {{ isDeleting ? t('settings.danger.deleting') : t('settings.danger.confirm_button') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style>
.settings-page {
  min-height: calc(100vh - 52px);
}

.settings-layout {
  padding-top: 28px;
}

/* Content */
.settings-content { min-width: 0; }
.settings-section { display: flex; flex-direction: column; gap: 20px; }

/* Cards */
.settings-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  overflow: hidden;
}
.settings-card__head {
  padding: 16px 22px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 12px;
}
.settings-card__head-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
}
.settings-card__title {
  font-family: var(--font-ui);
  font-weight: 600;
  font-size: 13.5px;
  color: var(--text);
  margin: 0;
}
.settings-card__body { padding: 20px 22px; }

/* Avatar row */
.profile-avatar-row {
  display: flex;
  align-items: center;
  gap: 18px;
  padding-bottom: 20px;
  margin-bottom: 4px;
  border-bottom: 1px solid var(--border);
}

.profile-avatar {
  border-radius: 50%;
  overflow: hidden;
  background: linear-gradient(135deg, var(--tag-d), var(--tag-b));
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-mono);
  font-weight: 600;
  color: #fff;
  border: 2px solid var(--border2);
  flex-shrink: 0;
}
.profile-avatar--lg { width: 64px; height: 64px; font-size: 20px; }
.profile-avatar img { width: 100%; height: 100%; object-fit: cover; }

.profile-avatar-meta {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.profile-name-sm {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  margin: 0;
}

.profile-email-sm {
  font-size: 13px;
  font-weight: 400;
  color: var(--text-mid);
  margin: 0;
}
.profile-provider-sm {
  font-size: 12px;
  color: var(--text-dim);
  margin: 0 0 6px;
}

/* Fields */
.settings-field {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 13px 0;
  border-bottom: 1px solid var(--border);
}
.settings-field--last { border-bottom: none; }
.settings-field__label {
  font-size: 12.5px;
  color: var(--text-mid);
  min-width: 110px;
  flex-shrink: 0;
}
.settings-field__value {
  font-size: 13.5px;
  color: var(--text);
  font-weight: 500;
}

/* Save */
.btn-save {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 20px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  font-family: var(--font-ui);
  background: var(--accent);
  color: #000;
  border: none;
  cursor: pointer;
  transition: all .12s;
}
.btn-save:hover:not(:disabled) { opacity: 0.88; }
.btn-save:disabled { opacity: 0.45; cursor: not-allowed; }
.btn-save--success {
  background: var(--accent-dim);
  color: var(--accent);
  border: 1px solid var(--accent-bdr);
}

.save-error {
  font-size: 12px;
  color: var(--danger, #e85555);
  margin: 0;
}

/* Toggle row */
.settings-toggle-row {
  align-items: flex-start !important;
}
.settings-toggle-info {
  display: flex;
  flex-direction: column;
  gap: 5px;
  flex: 1;
}
.settings-toggle-desc {
  font-size: 12px;
  color: var(--text-dim);
  line-height: 1.5;
}

.toggle-btn {
  position: relative;
  width: 38px;
  height: 21px;
  border-radius: 11px;
  background: var(--border2);
  border: 1.5px solid var(--border);
  cursor: pointer;
  flex-shrink: 0;
  transition: background .18s ease, border-color .18s ease;
  margin-top: 1px;
}
.toggle-btn--on { background: var(--accent); border-color: var(--accent); }
.toggle-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.toggle-thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 13px;
  height: 13px;
  border-radius: 50%;
  background: var(--text-dim);
  transition: transform .18s ease, background .18s ease;
  display: block;
}
.toggle-btn--on .toggle-thumb {
  transform: translateX(17px);
  background: #000;
}

/* Danger Zone */
.settings-section + .settings-section { margin-top: 12px; }
.settings-card--danger { border-color: color-mix(in srgb, var(--danger, #e85555) 30%, transparent); }
.settings-card__title--danger { color: var(--danger, #e85555); }
.danger-body {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.danger-desc {
  font-size: 13px;
  color: var(--text-mid);
  margin: 0;
  flex: 1;
}
.btn-delete-account {
  padding: 8px 16px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 500;
  font-family: var(--font-ui);
  background: transparent;
  border: 1.5px solid var(--danger, #e85555);
  color: var(--danger, #e85555);
  cursor: pointer;
  transition: all .12s;
  white-space: nowrap;
  flex-shrink: 0;
}
.btn-delete-account:hover { background: color-mix(in srgb, var(--danger, #e85555) 10%, transparent); }

/* Delete dialog */
.delete-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}
.delete-dialog {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 28px;
  width: 100%;
  max-width: 420px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.delete-dialog__title {
  font-size: 16px;
  font-weight: 700;
  font-family: var(--font-ui);
  color: var(--text);
  margin: 0;
}
.delete-dialog__desc {
  font-size: 13.5px;
  color: var(--text-mid);
  margin: 0;
  line-height: 1.5;
}
.delete-dialog__label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-mid);
}
.delete-dialog__input {
  background: var(--bg);
  border: 1.5px solid var(--border);
  border-radius: 9px;
  padding: 9px 12px;
  font-size: 13.5px;
  font-family: var(--font-mono);
  color: var(--text);
  outline: none;
  transition: border-color .12s;
  letter-spacing: 0.05em;
}
.delete-dialog__input:focus { border-color: var(--danger, #e85555); }
.delete-dialog__actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 4px;
}
.btn-cancel {
  padding: 9px 18px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 500;
  font-family: var(--font-ui);
  background: var(--surface2);
  border: 1px solid var(--border);
  color: var(--text-mid);
  cursor: pointer;
  transition: all .12s;
}
.btn-cancel:hover { border-color: var(--border2); color: var(--text); }
.btn-confirm-delete {
  padding: 9px 18px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 600;
  font-family: var(--font-ui);
  background: var(--danger, #e85555);
  border: none;
  color: #fff;
  cursor: pointer;
  transition: all .12s;
}
.btn-confirm-delete:hover:not(:disabled) { opacity: 0.88; }
.btn-confirm-delete:disabled { opacity: 0.35; cursor: not-allowed; }

/* Responsive */
@media (max-width: 640px) {
  .settings-layout {
    padding-top: 18px;
  }
}
</style>
