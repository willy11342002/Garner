<script setup lang="ts">
interface Props {
  currentPlan?: 'free' | 'pro'
}

const props = withDefaults(defineProps<Props>(), {
  currentPlan: undefined,
})

const emit = defineEmits<{
  upgrade: []
}>()

const { t } = useI18n()
const billing = ref<'monthly' | 'yearly'>('monthly')
</script>

<template>
  <div class="pricing-plans">
    <div class="billing-toggle">
      <button :class="{ active: billing === 'monthly' }" @click="billing = 'monthly'">{{ t('pricing.billing_monthly') }}</button>
      <button :class="{ active: billing === 'yearly' }" @click="billing = 'yearly'">
        {{ t('pricing.billing_yearly') }} <span class="save-badge">{{ t('pricing.save_badge') }}</span>
      </button>
    </div>

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
          <li class="feat feat--yes"><span class="ico">✓</span><span>{{ t('pricing.free.feat_relations') }}</span></li>
          <li class="feat feat--yes"><span class="ico">✓</span><span>{{ t('pricing.free.feat_browse') }}</span></li>
          <li class="feat feat--no"><span class="ico">×</span><span class="label">{{ t('pricing.pro.feat_search') }}</span></li>
          <li class="feat feat--no"><span class="ico">×</span><span class="label">{{ t('pricing.pro.feat_fork') }}</span></li>
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
          <span class="amt">{{ billing === 'monthly' ? '$12' : '$115' }}</span>
          <span class="per">{{ billing === 'monthly' ? t('pricing.per_month') : t('pricing.pro.per_year') }}</span>
        </div>
        <p class="plan__tag">{{ t('pricing.pro.tag') }}</p>
        <hr class="plan__div">
        <ul class="feats">
          <li class="feat feat--yes"><span class="ico">✓</span><span>{{ t('pricing.pro.feat_save') }}</span></li>
          <li class="feat feat--yes"><span class="ico">✓</span><span><strong>{{ t('pricing.pro.feat_unlimited_chat') }}</strong></span></li>
          <li class="feat feat--yes"><span class="ico">✓</span><span>{{ t('pricing.pro.feat_relations') }} <span class="star">✦</span></span></li>
          <li class="feat feat--yes"><span class="ico">✓</span><span>{{ t('pricing.pro.feat_browse') }}</span></li>
          <li class="feat feat--yes"><span class="ico">✓</span><span>{{ t('pricing.pro.feat_search') }}</span></li>
          <li class="feat feat--yes"><span class="ico">✓</span><span>{{ t('pricing.pro.feat_fork') }}</span></li>
        </ul>
        <div class="plan__cta">
          <template v-if="currentPlan === 'pro'">
            <button class="btn btn--lg btn--disabled">{{ t('pricing.free.current_plan') }}</button>
          </template>
          <template v-else>
            <button class="btn btn--accent btn--lg" @click="emit('upgrade')">{{ t('pricing.pro.upgrade') }}</button>
          </template>
        </div>
      </article>
    </section>

    <section class="faq">
      <h2>{{ t('pricing.faq.title') }}</h2>
      <details class="faq-item" open>
        <summary>{{ t('pricing.faq.q1') }}</summary>
        <p class="a">{{ t('pricing.faq.a1') }}</p>
      </details>
      <details class="faq-item">
        <summary>{{ t('pricing.faq.q2') }}</summary>
        <p class="a">{{ t('pricing.faq.a2') }}</p>
      </details>
      <details class="faq-item">
        <summary>{{ t('pricing.faq.q3') }}</summary>
        <p class="a">{{ t('pricing.faq.a3') }}</p>
      </details>
      <details class="faq-item">
        <summary>{{ t('pricing.faq.q4') }}</summary>
        <p class="a">{{ t('pricing.faq.a4') }}</p>
      </details>
      <details class="faq-item">
        <summary>{{ t('pricing.faq.q5') }}</summary>
        <p class="a">{{ t('pricing.faq.a5') }}</p>
      </details>
    </section>
  </div>
</template>

<style scoped>
.pricing-plans { display: contents; }

.billing-toggle {
  display: inline-flex;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 999px; padding: 4px; gap: 4px;
  margin-bottom: 28px;
}
.billing-toggle button {
  font-family: var(--font-mono); font-size: 12px;
  padding: 8px 18px; border-radius: 999px;
  color: var(--text-mid); transition: background .15s ease, color .15s ease, border-color .15s ease;
  display: inline-flex; align-items: center; gap: 8px;
  border: 1px solid transparent;
}
.billing-toggle button.active {
  background: var(--surface2); color: var(--text);
  border-color: var(--border2);
}
.save-badge {
  font-family: var(--font-mono); font-size: 9.5px;
  padding: 2px 7px; border-radius: 4px;
  background: var(--accent-dim); color: var(--accent); border: 1px solid var(--accent-bdr);
}

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


.faq h2 { font-family: var(--font-brand); font-weight: 600; font-size: 22px; margin: 0 0 18px; }
.faq-item { border-bottom: 1px solid var(--border); padding: 16px 4px; }
.faq-item summary {
  cursor: pointer; list-style: none;
  display: flex; align-items: center; gap: 12px;
  font-size: 14px; font-weight: 500; color: var(--text);
}
.faq-item summary::-webkit-details-marker { display: none; }
.faq-item summary::after {
  content: '+'; margin-left: auto;
  font-family: var(--font-mono); font-size: 18px; color: var(--text-dim); transition: transform .2s ease;
}
.faq-item[open] summary::after { content: '−'; }
.faq-item .a { padding: 12px 0 4px 0; font-size: 13px; color: var(--text-mid); line-height: 1.7; max-width: 720px; }

@media (max-width: 780px) {
  .plans { grid-template-columns: 1fr; }
  .plan { padding: 24px 22px; }
  .plan__price .amt { font-size: 36px; }
}
</style>
