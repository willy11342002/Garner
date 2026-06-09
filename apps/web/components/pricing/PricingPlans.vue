<script setup lang="ts">
interface Props {
  currentPlan?: 'free' | 'pro'
  checkoutUrl?: string
}

const props = withDefaults(defineProps<Props>(), {
  currentPlan: undefined,
  checkoutUrl: undefined,
})

const emit = defineEmits<{
  upgrade: []
}>()

const { t } = useI18n()
</script>

<template>
  <div class="pricing-plans">
    <section class="plans">
      <article class="plan">
        <div class="plan__top">
          <span class="plan__name">FREE</span>
        </div>
        <div class="plan__price">
          <span class="amt">$0</span>
          <span class="per">{{ t('pricing.per_month') }}</span>
        </div>
        <p class="plan__tag">{{ t('pricing.free.tag') }}</p>
        <hr class="plan__div">
        <ul class="feats">
          <li class="feat feat--yes"><span class="ico">✓</span><span>{{ t('pricing.free.feat_save') }}</span></li>
          <li class="feat feat--yes"><span class="ico">✓</span><span>{{ t('pricing.free.feat_chat') }}</span></li>
          <li class="feat feat--no"><span class="ico">×</span><span class="label">{{ t('pricing.pro.feat_search') }}</span></li>
        </ul>
        <div class="plan__cta">
          <button class="btn btn--lg btn--disabled">{{ t('pricing.free.current_plan') }}</button>
        </div>
      </article>

      <article class="plan plan--pro">
        <div class="plan__top">
          <span class="plan__name">PRO</span>
          <span class="badge-pop">{{ t('pricing.pro.badge_popular') }}</span>
        </div>
        <div class="plan__price">
          <span class="amt">$12</span>
          <span class="per">{{ t('pricing.per_month') }}</span>
        </div>
        <p class="plan__tag">{{ t('pricing.pro.tag') }}</p>
        <hr class="plan__div">
        <ul class="feats">
          <li class="feat feat--yes"><span class="ico">✓</span><span>{{ t('pricing.pro.feat_save') }}</span></li>
          <li class="feat feat--yes"><span class="ico">✓</span><span><strong>{{ t('pricing.pro.feat_unlimited_chat') }}</strong></span></li>
          <li class="feat feat--yes"><span class="ico">✓</span><span>{{ t('pricing.pro.feat_search') }}</span></li>
        </ul>
        <div class="plan__cta">
          <template v-if="currentPlan === 'pro'">
            <button class="btn btn--lg btn--disabled">{{ t('pricing.free.current_plan') }}</button>
          </template>
          <template v-else>
            <a
              v-if="checkoutUrl"
              class="btn btn--accent btn--lg"
              :href="checkoutUrl"
            >{{ t('pricing.pro.upgrade') }}</a>
            <button
              v-else
              class="btn btn--accent btn--lg"
              @click="emit('upgrade')"
            >{{ t('pricing.pro.upgrade') }}</button>
          </template>
        </div>
      </article>
    </section>

  </div>
</template>

<style scoped>
.pricing-plans { display: contents; }

.plans { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-bottom: 36px; }
.plan {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 20px; padding: 30px 28px;
  display: flex; flex-direction: column;
  position: relative; overflow: hidden;
}
.plan--pro {
  border-color: var(--accent-bdr);
  background: linear-gradient(160deg, var(--surface) 0%, color-mix(in oklab, var(--accent) 4%, var(--surface)) 100%);
  box-shadow: 0 0 0 1px var(--accent-bdr), 0 24px 60px -24px color-mix(in oklab, var(--accent) 40%, transparent);
}
.plan--pro::before {
  content: ''; position: absolute; left: 0; top: 0;
  width: 75%; height: 2px;
  background: linear-gradient(90deg, var(--accent), transparent);
}
.plan__top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.plan__name { font-family: var(--font-mono); font-size: 12px; font-weight: 500; color: var(--text-mid); letter-spacing: 0.1em; }
.plan--pro .plan__name { color: var(--accent); }
.badge-pop {
  font-family: var(--font-mono); font-size: 10px; color: var(--accent);
  background: var(--accent-dim); border: 1px solid var(--accent-bdr);
  padding: 3px 10px; border-radius: 4px;
}
.plan__price { display: flex; align-items: baseline; gap: 6px; margin-bottom: 6px; }
.plan__price .amt { font-family: var(--font-brand); font-weight: 700; font-size: 44px; letter-spacing: -0.02em; line-height: 1; }
.plan__price .per { font-family: var(--font-mono); font-size: 12px; color: var(--text-dim); }
.plan__tag { font-size: 13px; color: var(--text-mid); margin: 0 0 22px; }
.plan__div { height: 1px; background: var(--border); margin: 0 0 22px; border: none; }
.feats { display: flex; flex-direction: column; gap: 10px; margin-bottom: 24px; list-style: none; padding: 0; }
.feat { display: flex; align-items: flex-start; gap: 10px; font-size: 13.5px; color: var(--text); line-height: 1.5; }
.feat .ico {
  width: 18px; height: 18px; flex-shrink: 0;
  border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; margin-top: 1px;
}
.feat--yes .ico { background: var(--accent-dim); color: var(--accent); }
.feat--no { color: var(--text-dim); }
.feat--no .ico { background: var(--surface2); color: var(--text-dim); border: 1px solid var(--border); }
.feat--no .label { text-decoration: line-through; text-decoration-color: var(--text-dim); }
.feat strong { color: var(--text); font-weight: 600; }
.feat .star { color: var(--accent); }
.plan__cta { margin-top: auto; }
.plan__cta :deep(button) { width: 100%; }
.btn--disabled { background: var(--surface2); color: var(--text-dim); border: 1px solid var(--border); cursor: not-allowed; }
.btn--disabled:hover { transform: none; filter: none; }


@media (max-width: 780px) {
  .plans { grid-template-columns: 1fr; }
  .plan { padding: 24px 22px; }
  .plan__price .amt { font-size: 36px; }
}
</style>
