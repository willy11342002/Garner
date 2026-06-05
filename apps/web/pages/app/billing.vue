<script setup lang="ts">
useHead({ title: 'Garner — 方案與帳單' })
const { t } = useI18n()
const authStore = useAuthStore()
const apiFetch = useApiFetch()

const isPro = computed(() => authStore.user?.plan === 'pro')

const renewsOn = computed(() => {
  const d = authStore.user?.plan_expires_at
  if (!d) return null
  return new Date(d).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
})

const isRedirecting = ref(false)
const portalError = ref(false)

async function openBillingPortal() {
  if (isRedirecting.value) return
  isRedirecting.value = true
  portalError.value = false
  try {
    const { url } = await apiFetch<{ url: string }>('/billing/portal', { method: 'POST' })
    window.location.href = url
  } catch {
    portalError.value = true
    isRedirecting.value = false
  }
}

async function handleUpgrade() {
  // TODO: initiate Stripe checkout
}
</script>

<template>
  <main class="shell shell--narrow settings-page fadeup">
    <div class="settings-layout">
      <div class="settings-content">

        <!-- Current Plan -->
        <section class="settings-section">
          <div class="settings-card">
            <div class="settings-card__head">
              <h2 class="settings-card__title">{{ t('billing.current_plan') }}</h2>
            </div>
            <div class="settings-card__body">
              <div class="billing-plan-row">
                <span class="billing-badge" :class="isPro ? 'billing-badge--pro' : 'billing-badge--free'">
                  {{ isPro ? t('billing.plan_pro') : t('billing.plan_free') }}
                </span>
                <span v-if="isPro && renewsOn" class="billing-renews">
                  {{ t('billing.renews_on') }} {{ renewsOn }}
                </span>
              </div>
              <template v-if="isPro">
                <p v-if="portalError" class="billing-portal-error">{{ t('billing.portal_error') }}</p>
                <button class="btn-save" :disabled="isRedirecting" @click="openBillingPortal">
                  {{ isRedirecting ? t('billing.managing') : t('billing.manage_btn') }}
                </button>
              </template>
            </div>
          </div>
        </section>

        <!-- Upgrade plans (free plan only) -->
        <section v-if="!isPro" class="settings-section billing-plans-section">
          <PricingPlans :current-plan="authStore.user?.plan" @upgrade="handleUpgrade" />
        </section>

      </div>
    </div>
  </main>
</template>

<style scoped>
.billing-plan-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.billing-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 11px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  font-family: var(--font-ui);
  letter-spacing: 0.03em;
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

.billing-portal-error {
  font-size: 12px;
  color: var(--danger, #e85555);
  margin: 0 0 8px;
}

.billing-plans-section {
  margin-top: 4px;
}
</style>
