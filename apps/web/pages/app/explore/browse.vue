<template>
  <main class="ex-pane">
    <div class="browse-bar">
      <div class="browse-search">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
        <input type="text" placeholder="搜尋公開集合、主題、或使用者...">
      </div>
      <div class="filter-pills">
        <button class="pill" :class="{ 'pill--active': browseFilter === 'all' }" @click="browseFilter = 'all'">All</button>
        <button class="pill" :class="{ 'pill--active': browseFilter === 'travel' }" @click="browseFilter = 'travel'">旅遊</button>
        <button class="pill" :class="{ 'pill--active': browseFilter === 'design' }" @click="browseFilter = 'design'">設計</button>
        <button class="pill" :class="{ 'pill--active': browseFilter === 'tech' }" @click="browseFilter = 'tech'">科技</button>
        <button class="pill" :class="{ 'pill--active': browseFilter === 'food' }" @click="browseFilter = 'food'">美食</button>
      </div>
    </div>
    <div class="col-grid">
      <NuxtLink class="col-card" to="/share/kyoto-osaka-14d">
        <div class="col-card__cover"><div class="tile"><div class="placeholder placeholder--c"><div class="placeholder__stripes"></div></div></div><div class="tile"><div class="placeholder placeholder--a"><div class="placeholder__stripes"></div></div></div><div class="tile"><div class="placeholder placeholder--b"><div class="placeholder__stripes"></div></div></div><span class="col-card__count">42 items</span><button class="btn btn--accent col-card__fork">⑂ Fork</button></div>
        <div class="col-card__body"><h3 class="col-card__title">京都・大阪深度 14 天</h3><p class="col-card__desc">從早晨的清水寺路線到深夜的法善寺横丁，含 4 家不收訂金的隱藏 sushi。</p><div class="col-card__user"><span class="col-avatar">YK</span><span>@yuki_travels</span><span style="color:var(--text-dim)">· 6d ago</span></div><div class="col-card__foot"><span class="tag-chip tag-chip--c">日本旅遊</span><span class="tag-chip tag-chip--e">美食</span><span class="col-card__forks">⑂ 184 forks</span></div></div>
      </NuxtLink>
      <NuxtLink class="col-card" to="/share/ai-agent-reading">
        <div class="col-card__cover"><div class="tile"><div class="placeholder placeholder--a"><div class="placeholder__stripes"></div></div></div><div class="tile"><div class="placeholder placeholder--d"><div class="placeholder__stripes"></div></div></div><div class="tile"><div class="placeholder placeholder--b"><div class="placeholder__stripes"></div></div></div><span class="col-card__count">68 items</span><button class="btn btn--accent col-card__fork">⑂ Fork</button></div>
        <div class="col-card__body"><h3 class="col-card__title">AI Agent 工程師閱讀清單</h3><p class="col-card__desc">從 Karpathy 到 LangGraph 文件 — 一個資深工程師整理的 60 篇 must-read。</p><div class="col-card__user"><span class="col-avatar" style="background:linear-gradient(135deg,var(--tag-b),var(--tag-d))">DC</span><span>@dchen.ai</span><span style="color:var(--text-dim)">· 12d ago</span></div><div class="col-card__foot"><span class="tag-chip tag-chip--a">AI</span><span class="tag-chip tag-chip--d">工程</span><span class="col-card__forks">⑂ 421 forks</span></div></div>
      </NuxtLink>
      <NuxtLink class="col-card" to="/share/design-system-101">
        <div class="col-card__cover"><div class="tile"><div class="placeholder placeholder--b"><div class="placeholder__stripes"></div></div></div><div class="tile"><div class="placeholder placeholder--c"><div class="placeholder__stripes"></div></div></div><div class="tile"><div class="placeholder placeholder--e"><div class="placeholder__stripes"></div></div></div><span class="col-card__count">31 items</span><button class="btn btn--accent col-card__fork">⑂ Fork</button></div>
        <div class="col-card__body"><h3 class="col-card__title">Design System 從 0 到 1</h3><p class="col-card__desc">Linear / Vercel / Stripe 公開的設計系統文章，含我寫的 8 篇拆解。</p><div class="col-card__user"><span class="col-avatar" style="background:linear-gradient(135deg,var(--tag-c),var(--tag-a))">MO</span><span>@minonai</span><span style="color:var(--text-dim)">· 3d ago</span></div><div class="col-card__foot"><span class="tag-chip tag-chip--b">設計</span><span class="col-card__forks">⑂ 96 forks</span></div></div>
      </NuxtLink>
      <NuxtLink class="col-card" to="/share/simple-cooking">
        <div class="col-card__cover"><div class="tile"><div class="placeholder placeholder--e"><div class="placeholder__stripes"></div></div></div><div class="tile"><div class="placeholder placeholder--a"><div class="placeholder__stripes"></div></div></div><div class="tile"><div class="placeholder placeholder--c"><div class="placeholder__stripes"></div></div></div><span class="col-card__count">24 items</span><button class="btn btn--accent col-card__fork">⑂ Fork</button></div>
        <div class="col-card__body"><h3 class="col-card__title">一個人簡單也吃得很好</h3><p class="col-card__desc">所有食譜都是 20 分鐘內、一個鍋子完成、台灣超市買得到食材。</p><div class="col-card__user"><span class="col-avatar" style="background:linear-gradient(135deg,var(--tag-e),var(--tag-d))">PL</span><span>@pinglee</span><span style="color:var(--text-dim)">· 21d ago</span></div><div class="col-card__foot"><span class="tag-chip tag-chip--e">食譜</span><span class="col-card__forks">⑂ 58 forks</span></div></div>
      </NuxtLink>
      <NuxtLink class="col-card" to="/share/b2b-saas-growth">
        <div class="col-card__cover"><div class="tile"><div class="placeholder placeholder--d"><div class="placeholder__stripes"></div></div></div><div class="tile"><div class="placeholder placeholder--b"><div class="placeholder__stripes"></div></div></div><div class="tile"><div class="placeholder placeholder--accent"><div class="placeholder__stripes"></div></div></div><span class="col-card__count">52 items</span><button class="btn btn--accent col-card__fork">⑂ Fork</button></div>
        <div class="col-card__body"><h3 class="col-card__title">B2B SaaS 早期成長閱讀清單</h3><p class="col-card__desc">First Round Review, a16z, Lenny 的 newsletter 精華 — 從 0 到 $1M ARR。</p><div class="col-card__user"><span class="col-avatar" style="background:linear-gradient(135deg,var(--tag-d),var(--tag-b))">JF</span><span>@j_fang</span><span style="color:var(--text-dim)">· 9d ago</span></div><div class="col-card__foot"><span class="tag-chip tag-chip--d">產品</span><span class="col-card__forks">⑂ 312 forks</span></div></div>
      </NuxtLink>
      <NuxtLink class="col-card" to="/share/novels-2026">
        <div class="col-card__cover"><div class="tile"><div class="placeholder placeholder--c"><div class="placeholder__stripes"></div></div></div><div class="tile"><div class="placeholder placeholder--e"><div class="placeholder__stripes"></div></div></div><div class="tile"><div class="placeholder placeholder--d"><div class="placeholder__stripes"></div></div></div><span class="col-card__count">19 items</span><button class="btn btn--accent col-card__fork">⑂ Fork</button></div>
        <div class="col-card__body"><h3 class="col-card__title">2026 該讀的 19 本小說</h3><p class="col-card__desc">紐約客、衛報、東京文藝春秋的選書交集，含我的閱讀順序建議。</p><div class="col-card__user"><span class="col-avatar" style="background:linear-gradient(135deg,var(--tag-a),var(--tag-e))">SR</span><span>@sarahreads</span><span style="color:var(--text-dim)">· 17d ago</span></div><div class="col-card__foot"><span class="tag-chip tag-chip--a">閱讀</span><span class="col-card__forks">⑂ 73 forks</span></div></div>
      </NuxtLink>
    </div>
  </main>
</template>

<script setup lang="ts">
const browseFilter = ref('all')
</script>

<style>
.browse-bar { display: flex; gap: 10px; margin-bottom: 22px; }
.browse-search { flex: 1; position: relative; }
.browse-search input { width: 100%; height: 44px; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 0 16px 0 42px; font-size: 13.5px; color: var(--text); outline: none; }
.browse-search input:focus { border-color: var(--accent-bdr); box-shadow: 0 0 0 3px var(--accent-dim); }
.browse-search svg { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); width: 16px; height: 16px; color: var(--text-mid); }
.filter-pills { display: flex; gap: 6px; flex-wrap: wrap; }
.pill { font-family: var(--font-mono); font-size: 11.5px; padding: 8px 14px; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; color: var(--text-mid); cursor: pointer; transition: all .15s ease; }
.pill:hover { color: var(--text); }
.pill--active { background: var(--accent-dim); color: var(--accent); border-color: var(--accent-bdr); }
.col-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.col-card { position: relative; background: var(--surface); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; transition: all .2s ease; cursor: pointer; }
.col-card:hover { transform: translateY(-4px); border-color: var(--border2); box-shadow: 0 14px 32px -14px var(--shadow); }
.col-card:hover .col-card__fork { opacity: 1; transform: translateY(0); }
.col-card__cover { height: 130px; display: grid; grid-template-columns: 2fr 1fr; grid-template-rows: 1fr 1fr; gap: 2px; position: relative; background: var(--surface2); }
.col-card__cover .tile { overflow: hidden; }
.col-card__cover .tile:nth-child(1) { grid-row: 1 / span 2; }
.col-card__cover::after { content: ''; position: absolute; inset: 0; background: linear-gradient(180deg, transparent 60%, rgba(0,0,0,0.55)); pointer-events: none; }
.col-card__count { position: absolute; right: 12px; bottom: 10px; z-index: 2; font-family: var(--font-mono); font-size: 10.5px; color: #fff; }
.col-card__fork { position: absolute; top: 12px; right: 12px; z-index: 3; opacity: 0; transform: translateY(-4px); transition: all .2s ease; height: 30px; padding: 0 12px; font-size: 11.5px; }
.col-card__body { padding: 14px 16px 16px; display: flex; flex-direction: column; gap: 10px; }
.col-card__title { font-family: var(--font-brand); font-weight: 600; font-size: 15px; margin: 0; line-height: 1.35; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.col-card__desc { font-size: 12px; color: var(--text-mid); line-height: 1.55; margin: 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.col-card__user { display: flex; align-items: center; gap: 8px; font-family: var(--font-mono); font-size: 11px; color: var(--text-mid); }
.col-avatar { width: 22px; height: 22px; border-radius: 50%; flex-shrink: 0; background: linear-gradient(135deg, var(--tag-a), var(--tag-c)); display: inline-flex; align-items: center; justify-content: center; color: #fff; font-size: 9px; }
.col-card__foot { display: flex; align-items: center; gap: 6px; padding-top: 10px; border-top: 1px solid var(--border); }
.col-card__forks { margin-left: auto; font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); }

@media (max-width: 980px) { .col-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 640px) { .col-grid { grid-template-columns: 1fr; } .browse-bar { flex-direction: column; } }
</style>
