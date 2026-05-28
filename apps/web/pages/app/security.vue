<script setup lang="ts">
const { t } = useI18n()
const supabaseUser = useSupabaseUser()
const client = useSupabaseClient()
const router = useRouter()
const apiFetch = useApiFetch()

const activeSection = ref<'connected' | 'danger'>('connected')

const PROVIDER_LABELS: Record<string, string> = {
  google: 'Google',
  github: 'GitHub',
  email: 'Email / Password',
}

const providers = computed(() => {
  const meta = supabaseUser.value?.app_metadata
  const list: string[] = meta?.providers ?? (meta?.provider ? [meta.provider] : [])
  return list.map(p => ({ id: p, label: PROVIDER_LABELS[p] ?? p }))
})

const userId = computed(() => supabaseUser.value?.id ?? '—')

const lastSignIn = computed(() => {
  const raw = supabaseUser.value?.last_sign_in_at
  if (!raw) return t('security.connected.session.unknown')
  return new Date(raw).toLocaleString()
})

// Danger zone — delete account
const deleteConfirm = ref('')
const showDeleteModal = ref(false)
const isDeleting = ref(false)
const deleteError = ref('')

const canDelete = computed(() => deleteConfirm.value === 'DELETE')

function openDeleteModal() {
  deleteConfirm.value = ''
  deleteError.value = ''
  showDeleteModal.value = true
}

function closeDeleteModal() {
  if (isDeleting.value) return
  showDeleteModal.value = false
}

async function deleteAccount() {
  if (!canDelete.value || isDeleting.value) return
  isDeleting.value = true
  deleteError.value = ''
  try {
    await apiFetch('/auth/me', { method: 'DELETE' })
    await client.auth.signOut()
    router.push('/')
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e)
    deleteError.value = msg || '刪除失敗，請稍後再試。'
  } finally {
    isDeleting.value = false
  }
}
</script>

<template>
  <main class="shell shell--narrow settings-page fadeup">
    <div class="settings-layout">

      <!-- Sidebar nav -->
      <nav class="settings-sidebar">
        <button
          class="settings-nav-item"
          :class="{ active: activeSection === 'connected' }"
          @click="activeSection = 'connected'"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
          {{ t('security.nav.connected') }}
        </button>
        <button
          class="settings-nav-item"
          :class="{ active: activeSection === 'danger' }"
          @click="activeSection = 'danger'"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          {{ t('security.nav.danger') }}
        </button>
      </nav>

      <!-- Content -->
      <div class="settings-content">

        <!-- Connected Accounts -->
        <section v-if="activeSection === 'connected'" class="settings-section">
          <div class="settings-card">
            <div class="settings-card__head">
              <h2 class="settings-card__title">{{ t('security.connected.title') }}</h2>
            </div>
            <div class="settings-card__body">
              <p class="security-desc">{{ t('security.connected.description') }}</p>

              <div class="security-providers">
                <div v-for="p in providers" :key="p.id" class="security-provider-row">
                  <div class="security-provider-icon">
                    <!-- Google -->
                    <svg v-if="p.id === 'google'" viewBox="0 0 24 24" width="18" height="18">
                      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
                      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                    </svg>
                    <!-- GitHub -->
                    <svg v-else-if="p.id === 'github'" viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                      <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844a9.59 9.59 0 0 1 2.504.337c1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0 0 22 12.017C22 6.484 17.522 2 12 2z"/>
                    </svg>
                    <!-- Email fallback -->
                    <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="18" height="18">
                      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                      <polyline points="22,6 12,13 2,6"/>
                    </svg>
                  </div>
                  <span class="security-provider-name">{{ p.label }}</span>
                  <span class="security-provider-badge">{{ t('security.connected.provider_label') }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Session info card -->
          <div class="settings-card">
            <div class="settings-card__head">
              <h2 class="settings-card__title">{{ t('security.connected.session.title') }}</h2>
            </div>
            <div class="settings-card__body">
              <div class="settings-field">
                <span class="settings-field__label">{{ t('security.connected.session.user_id') }}</span>
                <span class="settings-field__value settings-field__value--mono">{{ userId }}</span>
              </div>
              <div class="settings-field settings-field--last">
                <span class="settings-field__label">{{ t('security.connected.session.last_sign_in') }}</span>
                <span class="settings-field__value">{{ lastSignIn }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- Danger Zone -->
        <section v-if="activeSection === 'danger'" class="settings-section">
          <div class="settings-card settings-card--danger">
            <div class="settings-card__head">
              <h2 class="settings-card__title settings-card__title--danger">{{ t('security.danger.title') }}</h2>
            </div>
            <div class="settings-card__body">
              <div class="danger-row">
                <div class="danger-row__info">
                  <p class="danger-row__label">{{ t('security.danger.delete_account') }}</p>
                  <p class="danger-row__desc">{{ t('security.danger.delete_description') }}</p>
                </div>
                <button class="btn btn--danger" @click="openDeleteModal">
                  {{ t('security.danger.delete_button') }}
                </button>
              </div>
            </div>
          </div>
        </section>

      </div>
    </div>

    <!-- Delete confirmation modal -->
    <Transition name="modal">
      <div v-if="showDeleteModal" class="add-overlay" @click.self="closeDeleteModal">
        <div class="delete-modal">
          <div class="delete-modal__icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
          </div>
          <h3 class="delete-modal__title">{{ t('security.danger.confirm_title') }}</h3>
          <p class="delete-modal__desc">{{ t('security.danger.confirm_description') }}</p>
          <p class="delete-modal__prompt">{{ t('security.danger.confirm_prompt') }}</p>
          <input
            v-model="deleteConfirm"
            class="delete-modal__input"
            :placeholder="t('security.danger.confirm_placeholder')"
            :disabled="isDeleting"
            autocomplete="off"
            spellcheck="false"
          />
          <p v-if="deleteError" class="delete-modal__error">{{ deleteError }}</p>
          <div class="delete-modal__actions">
            <button class="btn btn--ghost" :disabled="isDeleting" @click="closeDeleteModal">
              {{ t('security.danger.cancel') }}
            </button>
            <button
              class="btn btn--danger"
              :disabled="!canDelete || isDeleting"
              @click="deleteAccount"
            >
              {{ isDeleting ? t('security.danger.deleting') : t('security.danger.confirm_button') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </main>
</template>

<style>
/* ── Shared settings-page layout (mirrors settings.vue) ── */
.settings-page { min-height: calc(100vh - 52px); }

.settings-layout {
  display: grid;
  grid-template-columns: 188px 1fr;
  gap: 28px;
  align-items: start;
  padding-top: 28px;
}

.settings-sidebar {
  position: sticky;
  top: 76px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 6px;
  display: flex;
  flex-direction: column;
}

.settings-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 9px 12px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 500;
  font-family: var(--font-ui);
  color: var(--text-mid);
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
  transition: all .12s;
}
.settings-nav-item:hover { background: var(--surface2); color: var(--text); }
.settings-nav-item.active { background: var(--surface2); color: var(--text); }
.settings-nav-item svg {
  width: 15px; height: 15px;
  flex-shrink: 0;
  color: var(--text-dim);
  transition: color .12s;
}
.settings-nav-item:hover svg,
.settings-nav-item.active svg { color: var(--text-mid); }

.settings-content { min-width: 0; }
.settings-section { display: flex; flex-direction: column; gap: 20px; }

.settings-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  overflow: hidden;
}
.settings-card__head {
  padding: 16px 22px;
  border-bottom: 1px solid var(--border);
}
.settings-card__title {
  font-family: var(--font-ui);
  font-weight: 600;
  font-size: 13.5px;
  color: var(--text);
  margin: 0;
}
.settings-card__body { padding: 20px 22px; }

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

@media (max-width: 640px) {
  .settings-layout {
    grid-template-columns: 1fr;
    padding-top: 18px;
    gap: 18px;
  }
  .settings-sidebar {
    position: static;
    flex-direction: row;
  }
  .settings-nav-item {
    flex: 1;
    justify-content: center;
    gap: 6px;
    font-size: 12.5px;
  }
  .settings-nav-item svg { display: none; }
}

/* ── Security-specific styles ── */
.security-desc {
  font-size: 13px;
  color: var(--text-mid);
  line-height: 1.65;
  margin: 0 0 20px;
}

.security-providers {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.security-provider-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 13px 0;
  border-bottom: 1px solid var(--border);
}
.security-provider-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.security-provider-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--surface2);
  border: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--text-mid);
}

.security-provider-name {
  flex: 1;
  font-size: 13.5px;
  font-weight: 500;
  color: var(--text);
}

.security-provider-badge {
  font-size: 11px;
  font-weight: 500;
  color: var(--accent);
  background: var(--accent-dim);
  border: 1px solid var(--accent-bdr);
  border-radius: 6px;
  padding: 3px 8px;
}

/* Session field mono */
.settings-field__value--mono {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-mid);
  word-break: break-all;
}

/* Danger card */
.settings-card--danger {
  border-color: rgba(232, 85, 85, 0.25);
}
.settings-card__title--danger {
  color: #e85555;
}

.danger-row {
  display: flex;
  align-items: flex-start;
  gap: 20px;
  justify-content: space-between;
}

.danger-row__info {
  flex: 1;
  min-width: 0;
}

.danger-row__label {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text);
  margin: 0 0 5px;
}

.danger-row__desc {
  font-size: 12.5px;
  color: var(--text-mid);
  line-height: 1.65;
  margin: 0;
}

/* Delete modal */
.delete-modal {
  background: var(--surface);
  border: 1px solid rgba(232, 85, 85, 0.3);
  border-radius: 16px;
  padding: 28px 28px 24px;
  width: 100%;
  max-width: 440px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.18);
}

.delete-modal__icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: rgba(232, 85, 85, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #e85555;
  margin-bottom: 2px;
}
.delete-modal__icon svg { width: 20px; height: 20px; }

.delete-modal__title {
  font-family: var(--font-brand);
  font-size: 17px;
  font-weight: 700;
  color: var(--text);
  margin: 0;
  letter-spacing: -0.01em;
}

.delete-modal__desc {
  font-size: 13px;
  color: var(--text-mid);
  line-height: 1.65;
  margin: 0;
}

.delete-modal__prompt {
  font-family: var(--font-mono);
  font-size: 11.5px;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin: 4px 0 0;
}

.delete-modal__input {
  background: var(--bg);
  border: 1.5px solid var(--border2);
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 13px;
  font-family: var(--font-mono);
  color: var(--text);
  outline: none;
  transition: border-color 0.15s;
  letter-spacing: 0.04em;
}
.delete-modal__input:focus {
  border-color: rgba(232, 85, 85, 0.5);
}
.delete-modal__input::placeholder {
  color: var(--text-dim);
  letter-spacing: 0;
}

.delete-modal__error {
  font-family: var(--font-mono);
  font-size: 11.5px;
  color: var(--danger);
  margin: 0;
}

.delete-modal__actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 4px;
}

/* Danger button */
.btn--danger {
  padding: 9px 16px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  font-family: var(--font-ui);
  cursor: pointer;
  border: 1.5px solid rgba(232, 85, 85, 0.35);
  background: rgba(232, 85, 85, 0.1);
  color: #e85555;
  transition: all 0.12s;
  white-space: nowrap;
  flex-shrink: 0;
}
.btn--danger:hover:not(:disabled) {
  background: rgba(232, 85, 85, 0.18);
  border-color: rgba(232, 85, 85, 0.55);
}
.btn--danger:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn--ghost {
  padding: 9px 16px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
  font-family: var(--font-ui);
  cursor: pointer;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text-mid);
  transition: all 0.12s;
}
.btn--ghost:hover:not(:disabled) {
  background: var(--surface2);
  color: var(--text);
}
.btn--ghost:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Responsive */
@media (max-width: 640px) {
  .danger-row {
    flex-direction: column;
    gap: 14px;
  }
  .btn--danger {
    width: 100%;
    text-align: center;
  }
}
</style>
