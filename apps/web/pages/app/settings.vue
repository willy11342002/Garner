<script setup lang="ts">
const { t, locale, setLocale } = useI18n()
const { isDark, toggle } = useTheme()
const supabaseUser = useSupabaseUser()
const authStore = useAuthStore()

const activeSection = ref<'profile' | 'appearance'>('profile')

const avatarUrl = computed(() =>
  authStore.user?.avatar_url
  ?? supabaseUser.value?.user_metadata?.avatar_url
  ?? null
)
const email = computed(() => authStore.user?.email ?? supabaseUser.value?.email ?? '—')

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

// ── Profile edit ──
const editUsername = ref('')
const isSaving = ref(false)
const saveStatus = ref<'' | 'success' | 'error'>('')
const isUploadingAvatar = ref(false)
const avatarInput = ref<HTMLInputElement | null>(null)

watch(
  () => authStore.user?.username,
  (val) => { if (val) editUsername.value = val },
  { immediate: true },
)

async function saveProfile() {
  if (isSaving.value) return
  isSaving.value = true
  saveStatus.value = ''
  try {
    await authStore.updateProfile({ username: editUsername.value.trim() })
    saveStatus.value = 'success'
    setTimeout(() => { saveStatus.value = '' }, 2500)
  } catch {
    saveStatus.value = 'error'
  } finally {
    isSaving.value = false
  }
}

function triggerAvatarPick() {
  avatarInput.value?.click()
}

async function onAvatarSelected(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  isUploadingAvatar.value = true
  try {
    await authStore.uploadAvatar(file)
  } catch {
    // silently ignore — avatar is non-critical
  } finally {
    isUploadingAvatar.value = false
    if (avatarInput.value) avatarInput.value.value = ''
  }
}

const initials = computed(() => {
  const name = authStore.user?.username ?? editUsername.value ?? '?'
  return name.slice(0, 2).toUpperCase()
})

function setTheme(dark: boolean) {
  if (isDark.value !== dark) toggle()
}
</script>

<template>
  <main class="shell shell--narrow settings-page fadeup">
    <div class="settings-layout">

      <!-- Sidebar nav -->
      <nav class="settings-sidebar">
        <button
          class="settings-nav-item"
          :class="{ active: activeSection === 'profile' }"
          @click="activeSection = 'profile'"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="8" r="4"/>
            <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
          </svg>
          {{ t('settings.profile.title') }}
        </button>
        <button
          class="settings-nav-item"
          :class="{ active: activeSection === 'appearance' }"
          @click="activeSection = 'appearance'"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="4" fill="none"/>
            <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>
          </svg>
          {{ t('settings.appearance.title') }}
        </button>
      </nav>

      <!-- Content -->
      <div class="settings-content">

        <!-- Profile section -->
        <section v-if="activeSection === 'profile'" class="settings-section">
          <div class="settings-card">
            <div class="settings-card__head">
              <h2 class="settings-card__title">{{ t('settings.profile.title') }}</h2>
            </div>
            <div class="settings-card__body">

              <!-- Avatar -->
              <div class="profile-avatar-row">
                <div class="profile-avatar profile-avatar--lg">
                  <img v-if="avatarUrl && !isUploadingAvatar" :src="avatarUrl" :alt="editUsername" referrerpolicy="no-referrer" />
                  <span v-else-if="!isUploadingAvatar">{{ initials }}</span>
                  <div v-else class="avatar-uploading-spinner"></div>
                </div>
                <div class="profile-avatar-meta">
                  <p class="profile-email-sm">{{ email }}</p>
                  <p class="profile-provider-sm">{{ providerName }}</p>
                  <button class="btn-avatar-change" :disabled="isUploadingAvatar" @click="triggerAvatarPick">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="13" height="13">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                      <polyline points="17 8 12 3 7 8"/>
                      <line x1="12" y1="3" x2="12" y2="15"/>
                    </svg>
                    {{ isUploadingAvatar ? t('settings.profile.avatar_uploading') : t('settings.profile.avatar_change') }}
                  </button>
                  <p class="avatar-hint">{{ t('settings.profile.avatar_hint') }}</p>
                </div>
                <input
                  ref="avatarInput"
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/gif"
                  style="display:none"
                  @change="onAvatarSelected"
                />
              </div>

              <!-- Username field -->
              <div class="settings-field settings-field--edit">
                <span class="settings-field__label">{{ t('settings.profile.username_label') }}</span>
                <input
                  v-model="editUsername"
                  class="settings-field__input"
                  :placeholder="t('settings.profile.username_placeholder')"
                  maxlength="50"
                  @keydown.enter="saveProfile"
                />
              </div>

              <!-- Email (readonly) -->
              <div class="settings-field settings-field--last">
                <span class="settings-field__label">{{ t('settings.profile.email') }}</span>
                <span class="settings-field__value">{{ email }}</span>
              </div>

              <!-- Save button -->
              <div class="profile-actions">
                <button
                  class="btn-save"
                  :class="{ 'btn-save--success': saveStatus === 'success' }"
                  :disabled="isSaving || !editUsername.trim()"
                  @click="saveProfile"
                >
                  <template v-if="saveStatus === 'success'">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="13" height="13">
                      <polyline points="20 6 9 17 4 12"/>
                    </svg>
                    {{ t('settings.profile.save_success') }}
                  </template>
                  <template v-else>
                    {{ isSaving ? t('settings.profile.saving') : t('settings.profile.save') }}
                  </template>
                </button>
                <p v-if="saveStatus === 'error'" class="save-error">{{ t('settings.profile.save_error') }}</p>
              </div>

            </div>
          </div>
        </section>

        <!-- Appearance section -->
        <section v-if="activeSection === 'appearance'" class="settings-section">
          <div class="settings-card">
            <div class="settings-card__head">
              <h2 class="settings-card__title">{{ t('settings.appearance.title') }}</h2>
            </div>
            <div class="settings-card__body">

              <!-- Theme -->
              <div class="settings-row">
                <span class="settings-row__label">{{ t('settings.appearance.theme') }}</span>
                <div class="theme-selector">
                  <button
                    class="theme-card theme-card--dark"
                    :class="{ selected: isDark }"
                    :aria-pressed="isDark"
                    @click="setTheme(true)"
                  >
                    <div class="theme-card__preview">
                      <div class="theme-preview-bar theme-preview-bar--accent"></div>
                      <div class="theme-preview-bar"></div>
                      <div class="theme-preview-bar theme-preview-bar--short"></div>
                      <div class="theme-preview-bar"></div>
                    </div>
                    <div class="theme-card__label">
                      <span>{{ t('settings.appearance.dark') }}</span>
                      <svg v-if="isDark" class="check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="20 6 9 17 4 12"/>
                      </svg>
                    </div>
                  </button>
                  <button
                    class="theme-card theme-card--light"
                    :class="{ selected: !isDark }"
                    :aria-pressed="!isDark"
                    @click="setTheme(false)"
                  >
                    <div class="theme-card__preview">
                      <div class="theme-preview-bar theme-preview-bar--accent"></div>
                      <div class="theme-preview-bar"></div>
                      <div class="theme-preview-bar theme-preview-bar--short"></div>
                      <div class="theme-preview-bar"></div>
                    </div>
                    <div class="theme-card__label">
                      <span>{{ t('settings.appearance.light') }}</span>
                      <svg v-if="!isDark" class="check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="20 6 9 17 4 12"/>
                      </svg>
                    </div>
                  </button>
                </div>
              </div>

              <!-- Language -->
              <div class="settings-row settings-row--last">
                <span class="settings-row__label">{{ t('settings.appearance.language') }}</span>
                <div class="lang-selector">
                  <button
                    class="lang-option"
                    :class="{ selected: locale === 'zh-TW' }"
                    @click="setLocale('zh-TW')"
                  >繁體中文</button>
                  <button
                    class="lang-option"
                    :class="{ selected: locale === 'en' }"
                    @click="setLocale('en')"
                  >English</button>
                </div>
              </div>

            </div>
          </div>
        </section>

      </div>
    </div>
  </main>
</template>

<style>
.settings-page {
  min-height: calc(100vh - 52px);
}

.settings-layout {
  display: grid;
  grid-template-columns: 188px 1fr;
  gap: 28px;
  align-items: start;
  padding-top: 28px;
}

/* Sidebar */
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

.avatar-uploading-spinner {
  width: 20px; height: 20px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.profile-avatar-meta {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.profile-email-sm {
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  margin: 0;
}
.profile-provider-sm {
  font-size: 12px;
  color: var(--text-dim);
  margin: 0 0 6px;
}

.btn-avatar-change {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 11px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  font-family: var(--font-ui);
  background: var(--surface2);
  border: 1px solid var(--border);
  color: var(--text-mid);
  cursor: pointer;
  transition: all .12s;
  width: fit-content;
}
.btn-avatar-change:hover:not(:disabled) { border-color: var(--border2); color: var(--text); }
.btn-avatar-change:disabled { opacity: 0.5; cursor: not-allowed; }

.avatar-hint {
  font-size: 11.5px;
  color: var(--text-dim);
  margin: 2px 0 0;
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

.settings-field--edit { align-items: center; }

.settings-field__input {
  flex: 1;
  background: var(--bg);
  border: 1.5px solid var(--border);
  border-radius: 9px;
  padding: 8px 12px;
  font-size: 13.5px;
  font-family: var(--font-ui);
  color: var(--text);
  outline: none;
  transition: border-color .12s;
}
.settings-field__input:focus { border-color: var(--accent-bdr); }
.settings-field__input::placeholder { color: var(--text-dim); }

/* Save */
.profile-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 18px;
}

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

/* Appearance rows */
.settings-row {
  padding: 18px 0;
  border-bottom: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.settings-row--last { border-bottom: none; padding-bottom: 0; }
.settings-row__label {
  font-size: 12.5px;
  font-weight: 500;
  color: var(--text-mid);
}

/* Theme cards */
.theme-selector { display: flex; gap: 10px; }
.theme-card {
  flex: 1;
  border: 2px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  background: transparent;
  padding: 0;
  transition: border-color .15s;
}
.theme-card:hover { border-color: var(--border2); }
.theme-card.selected { border-color: var(--accent); }

.theme-card__preview {
  padding: 10px 10px 8px;
  display: flex; flex-direction: column; gap: 5px;
  height: 72px;
}
.theme-card--dark .theme-card__preview { background: #111318; }
.theme-card--light .theme-card__preview { background: #f4f5f7; }

.theme-preview-bar {
  height: 7px;
  border-radius: 4px;
  width: 100%;
}
.theme-card--dark .theme-preview-bar { background: rgba(255,255,255,0.08); }
.theme-card--light .theme-preview-bar { background: rgba(0,0,0,0.08); }
.theme-card--dark .theme-preview-bar--accent { background: #4effc8; width: 55%; }
.theme-card--light .theme-preview-bar--accent { background: #00c896; width: 55%; }
.theme-preview-bar--short { width: 40%; }

.theme-card__label {
  display: flex; align-items: center; justify-content: space-between;
  padding: 9px 12px 10px;
  font-size: 12.5px; font-weight: 500;
  color: var(--text);
  background: var(--surface2);
  border-top: 1px solid var(--border);
}
.check-icon { width: 13px; height: 13px; color: var(--accent); }

/* Language selector */
.lang-selector { display: flex; gap: 8px; }
.lang-option {
  flex: 1;
  padding: 9px 16px;
  border: 1.5px solid var(--border);
  border-radius: 10px;
  background: var(--surface2);
  font-size: 13px; font-weight: 500;
  color: var(--text-mid);
  font-family: var(--font-ui);
  cursor: pointer;
  transition: all .12s;
  text-align: center;
}
.lang-option:hover { border-color: var(--border2); color: var(--text); }
.lang-option.selected {
  border-color: var(--accent-bdr);
  background: var(--accent-dim);
  color: var(--accent);
  font-weight: 600;
}

/* Responsive */
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
</style>
