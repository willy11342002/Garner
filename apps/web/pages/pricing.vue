<template>
  <main class="pr-shell">
    <section class="pr-hero">
      <span class="eyebrow">UPGRADE YOUR VELA</span>
      <h1>讓知識庫真正<br>發揮魔法</h1>
      <p>免費版已經幫你建立了基礎。升級後，無限查詢與完整 AI 關聯讓它真正活起來。</p>
      <div class="billing-toggle">
        <button :class="{ active: billing === 'monthly' }" @click="billing = 'monthly'">月付</button>
        <button :class="{ active: billing === 'yearly' }" @click="billing = 'yearly'">
          年付 <span class="save-badge">省 20%</span>
        </button>
      </div>
    </section>

    <section class="plans">
      <article class="plan">
        <div class="plan__top">
          <span class="plan__name">FREE</span>
        </div>
        <div class="plan__price">
          <span class="amt">$0</span>
          <span class="per">/ 月</span>
        </div>
        <p class="plan__tag">開始探索你的第二大腦</p>
        <hr class="plan__div">
        <ul class="feats">
          <li class="feat feat--yes">
            <span class="ico"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg></span>
            <span>每月 <strong>50 次</strong> AI 查詢<span class="hint">本月剩 12 次</span></span>
          </li>
          <li class="feat feat--yes"><span class="ico">✓</span><span>無限存入內容</span></li>
          <li class="feat feat--yes"><span class="ico">✓</span><span>AI 自動摘要與標籤</span></li>
          <li class="feat feat--yes"><span class="ico">✓</span><span>基本關聯（前 50 筆）</span></li>
          <li class="feat feat--no"><span class="ico">×</span><span class="label">進階語意搜尋</span></li>
          <li class="feat feat--no"><span class="ico">×</span><span class="label">無限關聯</span></li>
          <li class="feat feat--no"><span class="ico">×</span><span class="label">匯出知識庫</span></li>
        </ul>
        <div class="plan__cta">
          <button class="btn btn--lg btn--disabled">目前方案</button>
        </div>
      </article>

      <article class="plan plan--pro">
        <div class="plan__top">
          <span class="plan__name">PRO</span>
          <span class="badge-pop">最受歡迎</span>
        </div>
        <div class="plan__price">
          <span class="amt">{{ billing === 'monthly' ? '$12' : '$115' }}</span>
          <span class="per">{{ billing === 'monthly' ? '/ 月' : '/ 年（約 $9.6/月）' }}</span>
        </div>
        <p class="plan__tag">讓 AI 真正讀懂你的知識庫</p>
        <hr class="plan__div">
        <ul class="feats">
          <li class="feat feat--yes"><span class="ico">✓</span><span><strong>無限</strong> AI 查詢</span></li>
          <li class="feat feat--yes"><span class="ico">✓</span><span>無限存入內容</span></li>
          <li class="feat feat--yes"><span class="ico">✓</span><span>AI 自動摘要與標籤</span></li>
          <li class="feat feat--yes"><span class="ico">✓</span><span><strong>完整語意關聯</strong> <span class="star">✦</span></span></li>
          <li class="feat feat--yes"><span class="ico">✓</span><span>進階自然語言搜尋（5 個維度）</span></li>
          <li class="feat feat--yes"><span class="ico">✓</span><span>公開集合 + Fork 功能</span></li>
          <li class="feat feat--yes"><span class="ico">✓</span><span>知識庫匯出（Markdown / JSON）</span></li>
          <li class="feat feat--yes"><span class="ico">✓</span><span>優先客服</span></li>
        </ul>
        <div class="plan__cta">
          <button class="btn btn--accent btn--lg">升級到 Pro →</button>
        </div>
      </article>
    </section>

    <section class="magic">
      <h3>為什麼值得升級？</h3>
      <div class="quote-block">
        <span class="quote-block__line"></span>
        <div style="flex:1;">
          <p class="quote-block__text">「我存了一個月東西，某天隨口問了一句『我記得有篇講遠端團隊文化的...』，系統把我自己都忘記存過的東西找出來，還連結到另一篇我完全沒想過有關係的設計文章。那一刻，這個 app 才真的活起來。」</p>
          <div class="quote-block__author">
            <span class="quote-block__avatar">MW</span>
            <span>Mei Wu · 產品經理 · 使用 Vela 6 個月</span>
            <span class="pro-badge">Pro 用戶</span>
          </div>
        </div>
      </div>
    </section>

    <section class="faq">
      <h2>常見問題</h2>
      <details class="faq-item" open>
        <summary>免費版的 50 次查詢怎麼計算？</summary>
        <p class="a">每次你在「Focus（問知識庫）」頁面按下「探索」算 1 次。從首頁、文章詳細頁點進關聯卡片不算查詢。Surprise tab 的洞察也不計入。每月 1 號 UTC 重置。</p>
      </details>
      <details class="faq-item">
        <summary>可以隨時取消嗎？</summary>
        <p class="a">可以。取消後你會繼續享有 Pro 直到當前計費周期結束，之後自動降回 Free。所有資料保留，只是查詢功能會回到 50 次/月 的限制。</p>
      </details>
      <details class="faq-item">
        <summary>我的資料安全嗎？</summary>
        <p class="a">所有內容加密儲存（AES-256 at rest）。AI 摘要與標籤由 Anthropic Claude 處理，我們不會用你的內容做模型訓練，且資料 30 天後從 LLM 端清除。</p>
      </details>
      <details class="faq-item">
        <summary>Fork 別人的集合需要付費嗎？</summary>
        <p class="a">不需要。瀏覽與 Fork 公開集合是免費功能。Fork 後內容會進入你的知識庫，套用你選的標籤，從此屬於你。</p>
      </details>
      <details class="faq-item">
        <summary>年付和月付可以切換嗎？</summary>
        <p class="a">可以。從月付升級到年付，差額按比例折抵；從年付降到月付，剩餘金額退回原付款方式或轉成 credit。</p>
      </details>
    </section>
  </main>
</template>

<script setup lang="ts">
useHead({ title: 'Vela — 升級' })

const billing = ref<'monthly' | 'yearly'>('monthly')
</script>

<style>
.pr-shell { max-width: 920px; margin: 0 auto; padding: 56px 32px 80px; }

.pr-hero { text-align: center; margin-bottom: 48px; }
.pr-hero .eyebrow { color: var(--accent); letter-spacing: 0.12em; }
.pr-hero h1 {
  font-family: var(--font-brand);
  font-weight: 700;
  font-size: 44px;
  line-height: 1.15;
  letter-spacing: -0.02em;
  margin: 14px 0 14px;
  text-wrap: balance;
}
.pr-hero p {
  font-size: 15.5px; color: var(--text-mid); line-height: 1.6;
  margin: 0 auto 24px; max-width: 520px; text-wrap: pretty;
}
.billing-toggle {
  display: inline-flex;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 999px; padding: 4px; gap: 4px;
}
.billing-toggle button {
  font-family: var(--font-mono); font-size: 12px;
  padding: 8px 18px; border-radius: 999px;
  color: var(--text-mid); transition: all .15s ease;
  display: inline-flex; align-items: center; gap: 8px;
}
.billing-toggle button.active {
  background: var(--surface2); color: var(--text);
  border: 1px solid var(--border2); margin: -1px;
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
.feat .hint { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); display: block; margin-top: 2px; }
.feat strong { color: var(--text); font-weight: 600; }
.feat .star { color: var(--accent); }
.plan__cta { margin-top: auto; }
.plan__cta button { width: 100%; }
.btn--disabled { background: var(--surface2); color: var(--text-dim); border: 1px solid var(--border); cursor: not-allowed; }
.btn--disabled:hover { transform: none; filter: none; }

.magic {
  background: var(--surface2); border-radius: 16px;
  padding: 26px 30px; margin-bottom: 48px; border: 1px solid var(--border);
}
.magic h3 { font-family: var(--font-brand); font-weight: 600; font-size: 19px; margin: 0 0 16px; }
.quote-block { display: flex; gap: 16px; align-items: flex-start; }
.quote-block__line { width: 3px; flex-shrink: 0; background: var(--accent); border-radius: 2px; align-self: stretch; }
.quote-block__text { flex: 1; font-size: 14px; font-style: italic; color: var(--text); line-height: 1.7; margin: 0 0 14px; text-wrap: pretty; }
.quote-block__author { display: flex; align-items: center; gap: 10px; font-family: var(--font-mono); font-size: 11.5px; color: var(--text-mid); }
.quote-block__avatar {
  width: 28px; height: 28px; border-radius: 50%;
  background: linear-gradient(135deg, var(--tag-b), var(--tag-d));
  display: inline-flex; align-items: center; justify-content: center;
  color: #fff; font-size: 10px; font-weight: 500;
}
.pro-badge { margin-left: 6px; font-size: 9.5px; padding: 2px 7px; border-radius: 4px; background: var(--accent-dim); color: var(--accent); border: 1px solid var(--accent-bdr); }

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
  .pr-shell { padding: 32px 16px 60px; }
  .pr-hero h1 { font-size: 30px; }
  .pr-hero p { font-size: 14px; }
  .plans { grid-template-columns: 1fr; }
  .plan { padding: 24px 22px; }
  .plan__price .amt { font-size: 36px; }
}
</style>
