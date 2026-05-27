<template>
  <main class="landing">
    <section class="landing__hero">
      <span class="eyebrow">PERSONAL KNOWLEDGE BASE</span>
      <h1 class="landing__title">被動建立的<br>第二大腦</h1>
      <p class="landing__sub">
        一鍵收集 YouTube 影片與網頁文章，AI 自動產生摘要、標籤、語意關聯。<br>
        讓知識庫隨時間自動成長。
      </p>
      <div class="landing__cta">
        <NuxtLink to="/app" class="btn btn--accent btn--lg">免費開始使用</NuxtLink>
        <NuxtLink to="/app/explore" class="btn btn--lg">探索公開集合</NuxtLink>
      </div>
    </section>

    <section class="landing__features">
      <div class="feat-card">
        <span class="feat-card__icon">⚡</span>
        <h3>一鍵收集</h3>
        <p>Chrome Extension 偵測目前頁面，按下按鈕即儲存，無需切換 app。</p>
      </div>
      <div class="feat-card">
        <span class="feat-card__icon">🧠</span>
        <h3>AI 自動整理</h3>
        <p>每筆內容自動產生摘要、標籤與語意 embedding，形成可查詢的知識圖譜。</p>
      </div>
      <div class="feat-card">
        <span class="feat-card__icon">🔍</span>
        <h3>自然語言搜尋</h3>
        <p>問「我存過哪些關於遠端工作文化的？」直接拿到答案，不是搜尋結果列表。</p>
      </div>
      <div class="feat-card">
        <span class="feat-card__icon">⑂</span>
        <h3>公開 & Fork</h3>
        <p>分享你的知識集合，讓他人 Fork 進自己的庫。知識傳遞，而非複製貼上。</p>
      </div>
    </section>

    <div class="landing__bottom">
      <NuxtLink to="/pricing" class="mono" style="color:var(--text-mid); font-size:13px;">查看方案與定價 →</NuxtLink>
    </div>
  </main>
</template>

<script setup lang="ts">
useHead({ title: 'Vela — 被動建立的個人知識庫' })

const user = useSupabaseUser()
if (user.value) {
  await navigateTo('/app')
}
watch(user, (u) => {
  if (u) navigateTo('/app')
})
</script>

<style>
.landing {
  max-width: 860px;
  margin: 0 auto;
  padding: 80px 32px 100px;
  text-align: center;
}
.landing__hero { margin-bottom: 72px; }
.landing__title {
  font-family: var(--font-brand);
  font-weight: 700;
  font-size: 56px;
  line-height: 1.12;
  letter-spacing: -0.025em;
  margin: 16px 0 18px;
  text-wrap: balance;
}
.landing__sub {
  font-size: 16px;
  color: var(--text-mid);
  line-height: 1.7;
  margin: 0 auto 32px;
  max-width: 540px;
  text-wrap: pretty;
}
.landing__cta { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }

.landing__features {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  text-align: left;
  margin-bottom: 48px;
}
.feat-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 22px 20px;
}
.feat-card__icon { font-size: 22px; display: block; margin-bottom: 12px; }
.feat-card h3 { font-family: var(--font-brand); font-weight: 600; font-size: 15px; margin: 0 0 8px; }
.feat-card p { font-size: 13px; color: var(--text-mid); line-height: 1.6; margin: 0; }

.landing__bottom { text-align: center; }

@media (max-width: 640px) {
  .landing { padding: 48px 20px 64px; }
  .landing__title { font-size: 36px; }
  .landing__sub { font-size: 14px; }
}
</style>
