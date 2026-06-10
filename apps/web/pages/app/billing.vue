<script setup lang="ts">
import type { UsageSummary } from '~/types/api'

definePageMeta({ ssr: false })
useHead({
  title: 'Garner — 方案與帳單',
  script: [{ src: 'https://gumroad.com/js/gumroad.js', defer: true }],
})
const { t } = useI18n()
const apiFetch = useApiFetch()
const supabaseUser = useSupabaseUser()

const checkoutUrl = computed(() => {
  const base = 'https://willy11342002.gumroad.com/l/garner?wanted=true'
  const email = supabaseUser.value?.email
  return email ? `${base}&email=${encodeURIComponent(email)}` : base
})

const quota = ref<UsageSummary | null>(null)
const pending = ref(true)

onMounted(async () => {
  try {
    quota.value = await apiFetch<UsageSummary>('/quota/me')
  } finally {
    pending.value = false
  }
})

const isPro = computed(() => quota.value?.plan === 'pro')

const renewsOn = computed(() => {
  const d = quota.value?.period_end
  if (!d) return null
  return new Date(d).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
})

const cancelling = ref(false)
const cancelError = ref(false)
const cancelConfirm = ref(false)

async function cancelSubscription() {
  if (cancelling.value) return
  cancelling.value = true
  cancelError.value = false
  cancelConfirm.value = false
  try {
    await apiFetch('/billing/cancel', { method: 'POST' })
    // 重新拉 quota，plan 會降回 free
    quota.value = await apiFetch<UsageSummary>('/quota/me')
  } catch {
    cancelError.value = true
  } finally {
    cancelling.value = false
  }
}


function pct(used: number, limit: number | null): number {
  if (limit === null || limit === 0) return 0
  return Math.min(100, Math.round((used / limit) * 100))
}
</script>

<template>
  <main class="shell shell--narrow settings-page fadeup">
    <div class="settings-layout">
      <div class="settings-content">

        <section class="settings-section">
          <div class="settings-card">
            <div class="settings-card__head">
              <h2 class="settings-card__title">{{ t('billing.current_plan') }}</h2>
            </div>

            <div class="settings-card__body">
              <!-- skeleton -->
              <div v-if="pending" class="billing-skeleton" />

              <template v-else-if="quota">
                <!-- Plan badge row -->
                <div class="billing-plan-row">
                  <span class="billing-badge" :class="isPro ? 'billing-badge--pro' : 'billing-badge--free'">
                    {{ isPro ? t('billing.plan_pro') : t('billing.plan_free') }}
                  </span>
                  <span v-if="isPro && renewsOn" class="billing-renews">
                    {{ t('billing.renews_on') }} {{ renewsOn }}
                  </span>
                </div>

                <!-- Usage section -->
                <p class="billing-section-label">{{ t('billing.usage_title') }}</p>

                <div class="billing-usage-list">
                  <!-- saves -->
                  <div class="billing-usage-row">
                    <div class="billing-usage-head">
                      <span class="billing-usage-name">{{ t('billing.usage_saves') }}</span>
                      <span class="billing-usage-reset">{{ t('billing.reset_monthly') }}</span>
                    </div>
                    <div class="billing-bar-wrap">
                      <div class="billing-bar">
                        <div
                          v-if="quota.saves.limit !== null"
                          class="billing-bar__fill"
                          :class="{ 'billing-bar__fill--warn': pct(quota.saves.used, quota.saves.limit) >= 80 }"
                          :style="{ width: `${pct(quota.saves.used, quota.saves.limit)}%` }"
                        />
                      </div>
                      <span v-if="quota.saves.limit !== null" class="billing-usage-stat">
                        {{ t('billing.usage_count_saves', { used: quota.saves.used, limit: quota.saves.limit }) }}
                        <span class="billing-usage-pct">· {{ pct(quota.saves.used, quota.saves.limit) }}%</span>
                      </span>
                      <span v-else class="billing-usage-stat billing-usage-stat--unlimited">
                        {{ t('billing.usage_unlimited_label') }}
                      </span>
                    </div>
                  </div>

                  <!-- chat -->
                  <div class="billing-usage-row">
                    <div class="billing-usage-head">
                      <span class="billing-usage-name">{{ t('billing.usage_chat') }}</span>
                      <span class="billing-usage-reset">{{ t('billing.reset_daily') }}</span>
                    </div>
                    <div class="billing-bar-wrap">
                      <div class="billing-bar">
                        <div
                          v-if="quota.chat.limit !== null"
                          class="billing-bar__fill"
                          :class="{ 'billing-bar__fill--warn': pct(quota.chat.used, quota.chat.limit) >= 80 }"
                          :style="{ width: `${pct(quota.chat.used, quota.chat.limit)}%` }"
                        />
                      </div>
                      <span v-if="quota.chat.limit !== null" class="billing-usage-stat">
                        {{ t('billing.usage_count', { used: quota.chat.used, limit: quota.chat.limit }) }}
                        <span class="billing-usage-pct">· {{ pct(quota.chat.used, quota.chat.limit) }}%</span>
                      </span>
                      <span v-else class="billing-usage-stat billing-usage-stat--unlimited">
                        {{ t('billing.usage_unlimited_label') }}
                      </span>
                    </div>
                  </div>

                </div>

                <!-- Feature flags -->
                <p class="billing-section-label">{{ t('billing.features_title') }}</p>
                <div class="billing-features">
                  <span
                    class="billing-feature"
                    :class="quota.search_enabled ? 'billing-feature--on' : 'billing-feature--off'"
                  >
                    {{ t('billing.feature_search') }}
                    <span class="billing-feature__sep" />
                    {{ quota.search_enabled ? t('billing.feature_on') : t('billing.feature_off') }}
                  </span>
                  <span class="billing-feature billing-feature--on">
                    {{ t('billing.feature_video', { n: quota.video_max_minutes }) }}
                  </span>
                </div>

                <!-- Manage billing -->
                <h2 class="billing-section-title">{{ t('billing.manage_title') }}</h2>
                <template v-if="isPro">
                  <p class="billing-cancel-hint">{{ t('billing.cancel_hint') }}</p>
                  <p v-if="cancelError" class="billing-portal-error">{{ t('billing.portal_error') }}</p>

                  <template v-if="!cancelConfirm">
                    <button class="btn-cancel" @click="cancelConfirm = true">
                      {{ t('billing.cancel_btn') }}
                    </button>
                  </template>
                  <template v-else>
                    <p class="billing-cancel-confirm">{{ t('billing.cancel_confirm') }}</p>
                    <div class="billing-cancel-actions">
                      <button class="btn-cancel" :disabled="cancelling" @click="cancelSubscription">
                        {{ cancelling ? t('billing.cancelling') : t('billing.cancel_confirm_yes') }}
                      </button>
                      <button class="btn-cancel-abort" :disabled="cancelling" @click="cancelConfirm = false">
                        {{ t('billing.cancel_confirm_no') }}
                      </button>
                    </div>
                  </template>
                </template>
                <template v-else>
                  <p class="billing-upgrade-hint">{{ t('billing.upgrade_hint') }}</p>
                </template>
              </template>
            </div>
          </div>
        </section>

        <!-- Free: show upgrade plans -->
        <section v-if="!pending && !isPro" class="settings-section billing-plans-section">
          <PricingPlans :current-plan="quota?.plan as 'free' | 'pro' | undefined" :checkout-url="checkoutUrl" />
        </section>

      </div>
    </div>
  </main>
</template>

<style scoped>
.billing-skeleton {
  height: 160px;
  border-radius: 8px;
  background: var(--surface2);
  animation: pulse 1.4s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.45; }
}

/* Plan badge row */
.billing-plan-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}
.billing-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  font-family: var(--font-ui);
  letter-spacing: 0.04em;
}
.billing-badge--free {
  background: var(--surface2);
  border: 1px solid var(--border);
  color: var(--text-mid);
}
.billing-badge--pro {
  background: color-mix(in srgb, var(--accent) 15%, transparent);
  border: 1px solid color-mix(in srgb, var(--accent) 40%, transparent);
  color: var(--accent);
}
.billing-renews {
  font-size: 13px;
  color: var(--text-dim);
}

/* Section label */
.billing-section-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--text-dim);
  margin: 0 0 12px;
}
.billing-section-title {
  font-family: var(--font-brand);
  font-size: 18px;
  font-weight: 600;
  color: var(--text);
  margin: 8px 0 14px;
}

/* Usage list */
.billing-usage-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 24px;
}
.billing-usage-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.billing-usage-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}
.billing-usage-name {
  font-size: 13px;
  color: var(--text);
  font-weight: 500;
}
.billing-usage-reset {
  font-size: 11px;
  color: var(--text-dim);
  font-family: var(--font-mono);
}

/* Bar + stat row */
.billing-bar-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}
.billing-bar {
  flex: 1;
  height: 5px;
  border-radius: 3px;
  background: var(--surface3);
  overflow: hidden;
}
.billing-bar__fill {
  height: 100%;
  border-radius: 3px;
  background: var(--accent);
  transition: width 0.5s ease;
}
.billing-bar__fill--warn {
  background: var(--warn);
}
.billing-usage-stat {
  flex-shrink: 0;
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--text-mid);
  white-space: nowrap;
}
.billing-usage-stat--unlimited {
  color: var(--accent);
}
.billing-usage-pct {
  color: var(--text-dim);
}

/* Feature pills */
.billing-features {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 24px;
}
.billing-feature {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 11px;
  border-radius: 12px;
  font-size: 12px;
  border: 1px solid var(--border);
}
.billing-feature--on {
  background: color-mix(in srgb, var(--accent) 8%, transparent);
  border-color: color-mix(in srgb, var(--accent) 25%, transparent);
  color: var(--accent);
}
.billing-feature--off {
  background: var(--surface2);
  border-color: var(--border);
  color: var(--text-dim);
}
.billing-feature__sep {
  width: 1px;
  height: 11px;
  background: currentColor;
  opacity: 0.3;
  flex-shrink: 0;
}

.billing-portal-error {
  font-size: 12px;
  color: var(--danger);
  margin: 0 0 8px;
}
.billing-upgrade-hint {
  font-size: 13px;
  color: var(--text-dim);
  margin: 0;
}
.billing-cancel-hint {
  font-size: 13px;
  color: var(--text-dim);
  margin: 0 0 12px;
}
.btn-cancel {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  background: transparent;
  border: 1px solid var(--danger, #e55);
  color: var(--danger, #e55);
  transition: background 0.15s, opacity 0.15s;
}
.btn-cancel:hover:not(:disabled) {
  background: color-mix(in srgb, var(--danger, #e55) 10%, transparent);
}
.btn-cancel:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.billing-cancel-confirm {
  font-size: 13px;
  color: var(--text);
  margin: 0 0 10px;
}
.billing-cancel-actions {
  display: flex;
  gap: 8px;
}
.btn-cancel-abort {
  display: inline-flex;
  align-items: center;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-mid);
  transition: background 0.15s;
}
.btn-cancel-abort:hover:not(:disabled) {
  background: var(--surface2);
}
.btn-cancel-abort:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}


.billing-plans-section {
  margin-top: 4px;
}
</style>
