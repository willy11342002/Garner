<script setup lang="ts">
const { t, locale, setLocale } = useI18n()
const { isDark, toggle } = useTheme()
const supabaseUser = useSupabaseUser()

const activeSection = ref<'profile' | 'appearance'>('profile')

const displayName = computed(() =>
  supabaseUser.value?.user_metadata?.full_name
  ?? supabaseUser.value?.user_metadata?.name
  ?? supabaseUser.value?.email?.split('@')[0]
  ?? '—'
)
const authStore = useAuthStore()
const avatarUrl = computed(() =>
  authStore.user?.avatar_url
  ?? supabaseUser.value?.user_metadata?.avatar_url
  ?? null
)
const initials = computed(() => displayName.value.slice(0, 2).toUpperCase())
const email = computed(() => supabaseUser.value?.email ?? '—')

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
              <div class="profile-row">
                <div class="profile-avatar">
                  <img v-if="avatarUrl" :src="avatarUrl" :alt="displayName" referrerpolicy="no-referrer" />
                  <span v-else>{{ initials }}</span>
                </div>
                <div>
                  <p class="profile-name">{{ displayName }}</p>
                  <p class="profile-email">{{ email }}</p>
                </div>
              </div>

              <div class="settings-field">
                <span class="settings-field__label">{{ t('settings.profile.displayName') }}</span>
                <span class="settings-field__value">{{ displayName }}</span>
              </div>
              <div class="settings-field">
                <span class="settings-field__label">{{ t('settings.profile.email') }}</span>
                <span class="settings-field__value">{{ email }}</span>
              </div>
              <div class="settings-field settings-field--last">
                <span class="settings-field__label">{{ t('settings.profile.provider') }}</span>
                <span class="settings-field__value">{{ providerName }}</span>
              </div>

              <p class="profile-note">{{ t('settings.profile.readonly_note') }}</p>
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

/* Profile */
.profile-row {
  display: flex;
  align-items: center;
  gap: 18px;
  padding-bottom: 20px;
  margin-bottom: 4px;
  border-bottom: 1px solid var(--border);
}
.profile-avatar {
  width: 60px; height: 60px;
  border-radius: 50%;
  overflow: hidden;
  background: linear-gradient(135deg, var(--tag-d), var(--tag-b));
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-mono);
  font-size: 18px; font-weight: 600;
  color: #fff;
  border: 2px solid var(--border2);
  flex-shrink: 0;
}
.profile-avatar img { width: 100%; height: 100%; object-fit: cover; }
.profile-name {
  font-family: var(--font-brand);
  font-size: 18px; font-weight: 600;
  letter-spacing: -0.01em;
  margin: 0 0 3px;
  color: var(--text);
}
.profile-email { font-size: 12.5px; color: var(--text-mid); margin: 0; }

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

.profile-note {
  font-size: 12px;
  color: var(--text-dim);
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 14px;
  margin: 16px 0 0;
  line-height: 1.65;
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
