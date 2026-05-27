<template>
  <main class="shell">
    <!-- Hero -->
    <section class="hero fadeup">
      <div class="hero__media">
        <div class="placeholder placeholder--b">
          <div class="placeholder__stripes"></div>
          <div class="placeholder__label">[ YOUTUBE 影片縮圖 · 16:9 ]</div>
        </div>
        <div class="hero__mediaTag mono" style="color:var(--text-dim); font-size:10px; letter-spacing:.08em;">
          TODAY'S REVISIT · 30 DAYS AGO
        </div>
        <span class="source-badge hero__source">▶ YouTube</span>
      </div>
      <div class="hero__body">
        <span class="hero__day">Day 31</span>
        <span class="hero__eyebrow">TODAY'S REVISIT</span>
        <h1 class="hero__title">Andrej Karpathy 對軟體 3.0 的看法：當自然語言成為新的程式介面</h1>
        <p class="hero__summary">
          Karpathy 將軟體分為三世代：傳統手寫程式（1.0）、訓練神經網路權重（2.0）、用自然語言操控大模型（3.0）。他主張未來幾乎所有應用都會內嵌一層 LLM 作為通用認知層，工程師的工作是設計上下文、評估與工具。
        </p>
        <div class="hero__chips">
          <span class="tag-chip tag-chip--a">AI</span>
          <span class="tag-chip tag-chip--b">軟體工程</span>
          <span class="tag-chip tag-chip--c">演講筆記</span>
        </div>
        <div class="hero__actions">
          <a href="#" class="btn btn--accent">開啟閱讀 →</a>
          <button class="btn">封存</button>
        </div>
      </div>
    </section>

    <!-- Tag row: AI -->
    <section class="tagrow">
      <header class="tagrow__head">
        <span class="tagrow__dot" style="background:var(--tag-a)"></span>
        <span class="tagrow__name">AI</span>
        <span class="tagrow__count">142</span>
        <NuxtLink to="/app/share" class="tagrow__share">↗ 分享這個標籤</NuxtLink>
        <a href="#" class="tagrow__all">查看全部 →</a>
      </header>
      <div class="tagrow__scroll">
        <a class="card" href="#"><div class="card__thumb"><div class="placeholder placeholder--a"><div class="placeholder__stripes"></div><div class="placeholder__label">[ ARTICLE COVER ]</div></div><span class="assoc-badge">↗ 關聯</span><span class="source-badge">Article</span></div><div class="card__body"><h3 class="card__title">為什麼 Transformer 還是壓不死 Mamba 與 SSM 架構</h3><div class="card__footer"><span class="tag-chip tag-chip--a">AI</span><span class="mono">3d ago</span></div></div></a>
        <a class="card" href="#"><div class="card__thumb"><div class="placeholder placeholder--b"><div class="placeholder__stripes"></div><div class="placeholder__label">[ YOUTUBE 16:9 ]</div></div><span class="source-badge">▶ YouTube</span></div><div class="card__body"><h3 class="card__title">Lex Fridman × Sam Altman：GPT-6 與通用代理人的進度</h3><div class="card__footer"><span class="tag-chip tag-chip--a">AI</span><span class="mono">5d ago</span></div></div></a>
        <a class="card" href="#"><div class="card__thumb"><div class="placeholder placeholder--c"><div class="placeholder__stripes"></div><div class="placeholder__label">[ TWITTER 縮圖 ]</div></div><span class="assoc-badge">↗ 關聯</span><span class="source-badge">𝕏 Post</span></div><div class="card__body"><h3 class="card__title">Anthropic 工程師談 Claude 4.5 的 reward model 微調策略</h3><div class="card__footer"><span class="tag-chip tag-chip--a">AI</span><span class="mono">8d ago</span></div></div></a>
        <a class="card" href="#"><div class="card__thumb"><div class="placeholder placeholder--d"><div class="placeholder__stripes"></div><div class="placeholder__label">[ PAPER PDF ]</div></div><span class="source-badge">PDF</span></div><div class="card__body"><h3 class="card__title">Test-time Compute Scaling Laws (Anthropic, 2026)</h3><div class="card__footer"><span class="tag-chip tag-chip--a">AI</span><span class="mono">12d ago</span></div></div></a>
        <a class="card" href="#"><div class="card__thumb"><div class="placeholder placeholder--e"><div class="placeholder__stripes"></div><div class="placeholder__label">[ ARTICLE COVER ]</div></div><span class="source-badge">Article</span></div><div class="card__body"><h3 class="card__title">Karpathy：軟體 3.0 不是寫 prompt，是經營 context</h3><div class="card__footer"><span class="tag-chip tag-chip--a">AI</span><span class="mono">21d ago</span></div></div></a>
        <a class="card" href="#"><div class="card__thumb"><div class="placeholder placeholder--accent"><div class="placeholder__stripes"></div><div class="placeholder__label">[ BLOG POST ]</div></div><span class="assoc-badge">↗ 關聯</span><span class="source-badge">Article</span></div><div class="card__body"><h3 class="card__title">Latent Space：開發者如何在 6 個月內被 AI agent 取代或加倍生產</h3><div class="card__footer"><span class="tag-chip tag-chip--a">AI</span><span class="mono">28d ago</span></div></div></a>
        <a class="card--more" href="#">查看更多 +136</a>
      </div>
    </section>

    <!-- Tag row: 設計 -->
    <section class="tagrow">
      <header class="tagrow__head">
        <span class="tagrow__dot" style="background:var(--tag-b)"></span>
        <span class="tagrow__name">設計</span>
        <span class="tagrow__count">87</span>
        <NuxtLink to="/app/share" class="tagrow__share">↗ 分享這個標籤</NuxtLink>
        <a href="#" class="tagrow__all">查看全部 →</a>
      </header>
      <div class="tagrow__scroll">
        <a class="card" href="#"><div class="card__thumb"><div class="placeholder placeholder--b"><div class="placeholder__stripes"></div><div class="placeholder__label">[ DRIBBBLE 縮圖 ]</div></div><span class="source-badge">Article</span></div><div class="card__body"><h3 class="card__title">Linear 重新設計 sidebar 的 12 個版本：為什麼最終選擇了第 7 版</h3><div class="card__footer"><span class="tag-chip tag-chip--b">設計</span><span class="mono">2d ago</span></div></div></a>
        <a class="card" href="#"><div class="card__thumb"><div class="placeholder placeholder--c"><div class="placeholder__stripes"></div><div class="placeholder__label">[ FIGMA PREVIEW ]</div></div><span class="source-badge">Figma</span></div><div class="card__body"><h3 class="card__title">Refactoring UI：為什麼 grayscale 是設計師最該掌握的色盤</h3><div class="card__footer"><span class="tag-chip tag-chip--b">設計</span><span class="mono">7d ago</span></div></div></a>
        <a class="card" href="#"><div class="card__thumb"><div class="placeholder placeholder--a"><div class="placeholder__stripes"></div><div class="placeholder__label">[ YOUTUBE ]</div></div><span class="assoc-badge">↗ 關聯</span><span class="source-badge">▶ YouTube</span></div><div class="card__body"><h3 class="card__title">如何用 8pt grid 在不破壞節奏的前提下做出 16 種密度</h3><div class="card__footer"><span class="tag-chip tag-chip--b">設計</span><span class="mono">9d ago</span></div></div></a>
        <a class="card" href="#"><div class="card__thumb"><div class="placeholder placeholder--d"><div class="placeholder__stripes"></div><div class="placeholder__label">[ ARTICLE ]</div></div><span class="source-badge">Article</span></div><div class="card__body"><h3 class="card__title">Anti-design 的反撲：當 brutalism 成為 2026 年 SaaS 的主流</h3><div class="card__footer"><span class="tag-chip tag-chip--b">設計</span><span class="mono">14d ago</span></div></div></a>
        <a class="card" href="#"><div class="card__thumb"><div class="placeholder placeholder--e"><div class="placeholder__stripes"></div><div class="placeholder__label">[ TWITTER ]</div></div><span class="source-badge">𝕏 Post</span></div><div class="card__body"><h3 class="card__title">Steve Schoger：12 個讓你的 dashboard 立刻不像 bootstrap 的小招</h3><div class="card__footer"><span class="tag-chip tag-chip--b">設計</span><span class="mono">18d ago</span></div></div></a>
        <a class="card--more" href="#">查看更多 +82</a>
      </div>
    </section>

    <!-- Tag row: 日本旅遊 -->
    <section class="tagrow">
      <header class="tagrow__head">
        <span class="tagrow__dot" style="background:var(--tag-c)"></span>
        <span class="tagrow__name">日本旅遊</span>
        <span class="tagrow__count">34</span>
        <NuxtLink to="/app/share" class="tagrow__share">↗ 分享這個標籤</NuxtLink>
        <a href="#" class="tagrow__all">查看全部 →</a>
      </header>
      <div class="tagrow__scroll">
        <a class="card" href="#"><div class="card__thumb"><div class="placeholder placeholder--c"><div class="placeholder__stripes"></div><div class="placeholder__label">[ IG POST ]</div></div><span class="source-badge">IG</span></div><div class="card__body"><h3 class="card__title">京都嵐山竹林 7am 完全沒人的拍照路線</h3><div class="card__footer"><span class="tag-chip tag-chip--c">日本旅遊</span><span class="mono">1d ago</span></div></div></a>
        <a class="card" href="#"><div class="card__thumb"><div class="placeholder placeholder--a"><div class="placeholder__stripes"></div><div class="placeholder__label">[ ARTICLE 全景 ]</div></div><span class="assoc-badge">↗ 關聯</span><span class="source-badge">Note</span></div><div class="card__body"><h3 class="card__title">金澤 vs 富山：北陸新幹線開通後的客流量轉移</h3><div class="card__footer"><span class="tag-chip tag-chip--c">日本旅遊</span><span class="mono">6d ago</span></div></div></a>
        <a class="card" href="#"><div class="card__thumb"><div class="placeholder placeholder--b"><div class="placeholder__stripes"></div><div class="placeholder__label">[ TIKTOK 9:16 ]</div></div><span class="source-badge">TikTok</span></div><div class="card__body"><h3 class="card__title">大阪心齋橋一蘭排隊變半小時的時段：23:00 後</h3><div class="card__footer"><span class="tag-chip tag-chip--c">日本旅遊</span><span class="mono">11d ago</span></div></div></a>
        <a class="card" href="#"><div class="card__thumb"><div class="placeholder placeholder--d"><div class="placeholder__stripes"></div><div class="placeholder__label">[ MAPS LIST ]</div></div><span class="source-badge">Maps</span></div><div class="card__body"><h3 class="card__title">東京：18 家不需訂位但值得一吃的居酒屋清單</h3><div class="card__footer"><span class="tag-chip tag-chip--c">日本旅遊</span><span class="mono">19d ago</span></div></div></a>
        <a class="card--more" href="#">查看更多 +30</a>
      </div>
    </section>

    <!-- Tag row: 產品策略 -->
    <section class="tagrow">
      <header class="tagrow__head">
        <span class="tagrow__dot" style="background:var(--tag-d)"></span>
        <span class="tagrow__name">產品策略</span>
        <span class="tagrow__count">56</span>
        <NuxtLink to="/app/share" class="tagrow__share">↗ 分享這個標籤</NuxtLink>
        <a href="#" class="tagrow__all">查看全部 →</a>
      </header>
      <div class="tagrow__scroll">
        <a class="card" href="#"><div class="card__thumb"><div class="placeholder placeholder--d"><div class="placeholder__stripes"></div><div class="placeholder__label">[ NEWSLETTER ]</div></div><span class="source-badge">Email</span></div><div class="card__body"><h3 class="card__title">First Round Review：第一個 100 個客戶不要做 marketing，要做 retention</h3><div class="card__footer"><span class="tag-chip tag-chip--d">產品策略</span><span class="mono">4d ago</span></div></div></a>
        <a class="card" href="#"><div class="card__thumb"><div class="placeholder placeholder--a"><div class="placeholder__stripes"></div><div class="placeholder__label">[ PODCAST 封面 ]</div></div><span class="assoc-badge">↗ 關聯</span><span class="source-badge">Podcast</span></div><div class="card__body"><h3 class="card__title">Lenny × Linear CEO：為什麼我們五年都不接 enterprise sales</h3><div class="card__footer"><span class="tag-chip tag-chip--d">產品策略</span><span class="mono">10d ago</span></div></div></a>
        <a class="card" href="#"><div class="card__thumb"><div class="placeholder placeholder--b"><div class="placeholder__stripes"></div><div class="placeholder__label">[ TWITTER 串 ]</div></div><span class="source-badge">𝕏 Post</span></div><div class="card__body"><h3 class="card__title">Naval：付費牆是最後的考慮，不是第一個</h3><div class="card__footer"><span class="tag-chip tag-chip--d">產品策略</span><span class="mono">15d ago</span></div></div></a>
        <a class="card" href="#"><div class="card__thumb"><div class="placeholder placeholder--c"><div class="placeholder__stripes"></div><div class="placeholder__label">[ ARTICLE ]</div></div><span class="source-badge">Article</span></div><div class="card__body"><h3 class="card__title">Notion 是怎麼從 toy 變成 $10B：六年的 community-led growth 拆解</h3><div class="card__footer"><span class="tag-chip tag-chip--d">產品策略</span><span class="mono">22d ago</span></div></div></a>
        <a class="card--more" href="#">查看更多 +52</a>
      </div>
    </section>

    <!-- Tag row: 食譜 -->
    <section class="tagrow">
      <header class="tagrow__head">
        <span class="tagrow__dot" style="background:var(--tag-e)"></span>
        <span class="tagrow__name">食譜</span>
        <span class="tagrow__count">23</span>
        <NuxtLink to="/app/share" class="tagrow__share">↗ 分享這個標籤</NuxtLink>
        <a href="#" class="tagrow__all">查看全部 →</a>
      </header>
      <div class="tagrow__scroll">
        <a class="card" href="#"><div class="card__thumb"><div class="placeholder placeholder--e"><div class="placeholder__stripes"></div><div class="placeholder__label">[ YOUTUBE SHORT ]</div></div><span class="source-badge">▶ Shorts</span></div><div class="card__body"><h3 class="card__title">5 分鐘 Pad See Ew：不要 oyster sauce，要 dark soy</h3><div class="card__footer"><span class="tag-chip tag-chip--e">食譜</span><span class="mono">2d ago</span></div></div></a>
        <a class="card" href="#"><div class="card__thumb"><div class="placeholder placeholder--c"><div class="placeholder__stripes"></div><div class="placeholder__label">[ INSTAGRAM ]</div></div><span class="source-badge">IG</span></div><div class="card__body"><h3 class="card__title">Bon Appétit：浸泡 24 小時的鷹嘴豆 vs 罐頭，口感的差別</h3><div class="card__footer"><span class="tag-chip tag-chip--e">食譜</span><span class="mono">8d ago</span></div></div></a>
        <a class="card" href="#"><div class="card__thumb"><div class="placeholder placeholder--a"><div class="placeholder__stripes"></div><div class="placeholder__label">[ RECIPE PHOTO ]</div></div><span class="assoc-badge">↗ 關聯</span><span class="source-badge">Article</span></div><div class="card__body"><h3 class="card__title">Kenji López-Alt：完美煎蛋的物理 — 冷油下鍋與蛋白凝固時間</h3><div class="card__footer"><span class="tag-chip tag-chip--e">食譜</span><span class="mono">17d ago</span></div></div></a>
        <a class="card--more" href="#">查看更多 +20</a>
      </div>
    </section>
  </main>
</template>

<style>
.hero {
  position: relative;
  margin: 28px 0 40px;
  border-radius: 20px;
  overflow: hidden;
  border: 1px solid var(--border);
  background: var(--surface);
  min-height: 300px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 0.85fr);
}
.hero__media { position: relative; min-height: 300px; overflow: hidden; }
.hero__media .placeholder__label { font-size: 11px; color: rgba(255,255,255,0.55); }
body.light .hero__media .placeholder__label { color: rgba(0,0,0,0.5); }
.hero__media::after {
  content: ''; position: absolute; inset: 0;
  background: linear-gradient(90deg, transparent 0%, transparent 45%, var(--surface) 95%);
  pointer-events: none;
}
.hero__mediaTag { position: absolute; left: 18px; top: 18px; z-index: 2; }
.hero__source { position: absolute; right: 18px; bottom: 18px; z-index: 2; }
.hero__body {
  padding: 28px 32px 28px 8px;
  display: flex; flex-direction: column; justify-content: center; gap: 14px;
  position: relative; z-index: 3;
}
.hero__day { position: absolute; right: 24px; top: 22px; font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); letter-spacing: 0.06em; }
.hero__eyebrow { display: inline-flex; align-items: center; gap: 10px; font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.1em; }
.hero__eyebrow::before { content: ''; width: 3px; height: 12px; background: var(--accent); border-radius: 2px; }
.hero__title { font-family: var(--font-brand); font-weight: 600; font-size: 26px; line-height: 1.25; letter-spacing: -0.015em; margin: 0; max-width: 520px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.hero__summary { font-size: 13px; color: var(--text-mid); line-height: 1.75; max-width: 520px; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.hero__chips { display: flex; gap: 6px; flex-wrap: wrap; }
.hero__actions { display: flex; gap: 10px; margin-top: 4px; }

.tagrow { margin-bottom: 36px; }
.tagrow__head { display: flex; align-items: center; padding: 0 4px 10px; border-bottom: 1px solid var(--border); margin-bottom: 14px; }
.tagrow__dot { width: 7px; height: 7px; border-radius: 50%; margin-right: 10px; }
.tagrow__name { font-family: var(--font-ui); font-weight: 500; font-size: 14px; color: var(--text); }
.tagrow__count { margin-left: 10px; font-family: var(--font-mono); font-size: 11.5px; color: var(--text-dim); }
.tagrow__share { margin-left: 12px; font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); padding: 2px 8px; border: 1px solid var(--border); border-radius: 12px; transition: all .15s ease; }
.tagrow__share:hover { color: var(--accent); border-color: var(--accent-bdr); }
.tagrow__all { margin-left: auto; font-family: var(--font-mono); font-size: 11.5px; color: var(--text-dim); transition: color .15s ease; }
.tagrow__all:hover { color: var(--text); }
.tagrow__scroll { display: flex; gap: 12px; overflow-x: auto; padding: 4px 4px 8px; scrollbar-width: none; }
.tagrow__scroll::-webkit-scrollbar { display: none; }
.card--more { width: 200px; flex: 0 0 auto; border: 1px dashed var(--border2); background: transparent; display: flex; align-items: center; justify-content: center; color: var(--text-mid); font-family: var(--font-mono); font-size: 12px; border-radius: 12px; }
.card--more:hover { color: var(--accent); border-color: var(--accent-bdr); }

@media (max-width: 880px) {
  .hero { grid-template-columns: 1fr; min-height: 0; }
  .hero__media { height: 200px; min-height: 0; }
  .hero__media::after { background: linear-gradient(180deg, transparent 0%, var(--surface) 90%); }
  .hero__body { padding: 20px 22px 24px; }
  .hero__day { right: 18px; top: 14px; }
  .hero__title { font-size: 22px; }
  .card { width: 168px; }
  .card__thumb { height: 96px; }
}
</style>
