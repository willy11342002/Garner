<template>
  <div>
    <header class="ex-head">
      <div class="ex-head__top">
        <div>
          <span class="eyebrow">EXPLORE</span>
          <h1 class="page-title" style="margin-top:4px;">探索 · 漫遊</h1>
        </div>
        <div class="ex-head__stats">
          <div class="stat"><b>1,284</b>知識庫總量</div>
          <div class="stat"><b>12</b>公開集合</div>
          <div class="stat"><b>+38</b>本週新增</div>
        </div>
      </div>
      <nav class="ex-tabs">
        <button class="ex-tab" :class="{ 'ex-tab--active': activeTab === 'focus' }" @click="activeTab = 'focus'">Focus<span class="mono">問知識庫</span></button>
        <button class="ex-tab" :class="{ 'ex-tab--active': activeTab === 'surprise' }" @click="activeTab = 'surprise'">Surprise<span class="mono">隨機驚喜</span></button>
        <button class="ex-tab" :class="{ 'ex-tab--active': activeTab === 'browse' }" @click="activeTab = 'browse'">Browse<span class="mono">公開集合</span></button>
      </nav>
    </header>

    <!-- FOCUS -->
    <main v-show="activeTab === 'focus'" class="ex-pane">
      <p class="focus-hint">問你的知識庫一個問題，AI 會從你存過的所有內容中合成回答。</p>
      <div class="focus-input-row">
        <textarea class="focus-input" placeholder="例如：三個月前我存了什麼跟 Karpathy 有關的東西？"></textarea>
        <button class="btn btn--accent focus-submit">探索 →</button>
      </div>
      <div class="focus-chips">
        <button class="chip">三個月前存了什麼？</button>
        <button class="chip">有哪些和 AI 相關？</button>
        <button class="chip">我記得有個日本旅遊的...</button>
        <button class="chip">最常被關聯到的主題</button>
        <button class="chip">這週新增的所有產品策略內容</button>
      </div>

      <div class="focus-loading">
        <div class="pulse-row"><span></span><span></span><span></span><span></span><span></span></div>
        <ul class="focus-loading__steps">
          <li class="done">搜索相關內容（127 筆候選）</li>
          <li class="done">分析語意關聯（5 個主題群）</li>
          <li class="active">整合洞察與摘要...</li>
        </ul>
      </div>

      <article class="synth fadeup">
        <header class="synth__head">
          <span class="synth__badge">AI SYNTHESIS</span>
          <div class="synth__actions">
            <button>複製</button>
            <button>分享</button>
          </div>
        </header>
        <p class="synth__text">
          你過去三個月關於 <em>Karpathy</em> 共存了 5 筆內容，主要圍繞兩個觀點：(1) 軟體 3.0 是 <em>context engineering</em> 而不是 prompt engineering；(2) <em>LLM 作為通用認知層</em>嵌入既有應用會比新建專用模型更有效。其中三筆內容都引用了「<em>The hottest new programming language is English</em>」這句話，並進一步指出真正的工程挑戰是 <em>agent harness</em> 與 evaluation。
          <br><br>
          你也存了 2 筆延伸閱讀討論「為什麼 prompt engineering 是過渡技能」，這個論點和你 8 月存的一篇 Anthropic 文章呼應，建議從那一篇開始重讀。
        </p>
        <div class="synth__sources">
          <span class="label">SOURCES</span>
          <a href="#" class="src-chip">↗ Karpathy on Software 3.0</a>
          <a href="#" class="src-chip">↗ Anthropic reward tuning</a>
          <a href="#" class="src-chip">↗ Latent Space podcast</a>
          <a href="#" class="src-chip">↗ Andrej 的演講筆記 v2</a>
          <a href="#" class="src-chip">↗ Context Engineering blog</a>
        </div>
      </article>

      <header class="result-head">
        <span class="eyebrow">相關內容</span>
        <span class="line"></span>
        <span class="mono" style="font-size:11px; color:var(--text-dim);">5 筆 · 按相似度排序</span>
      </header>
      <div class="result-grid">
        <a href="#" class="rcard"><div class="rcard__thumb"><div class="placeholder placeholder--a"><div class="placeholder__stripes"></div></div><span class="assoc-badge">↗ 91%</span><span class="source-badge">▶</span></div><div class="rcard__body"><h4 class="rcard__title">Karpathy 對軟體 3.0 的看法：當自然語言成為新的程式介面</h4><div class="rcard__foot"><span class="tag-chip tag-chip--a">AI</span><span>30d</span></div></div></a>
        <a href="#" class="rcard"><div class="rcard__thumb"><div class="placeholder placeholder--b"><div class="placeholder__stripes"></div></div><span class="assoc-badge">↗ 87%</span><span class="source-badge">𝕏</span></div><div class="rcard__body"><h4 class="rcard__title">Anthropic 工程師談 Claude 4.5 的 reward model 微調策略</h4><div class="rcard__foot"><span class="tag-chip tag-chip--a">AI</span><span>8d</span></div></div></a>
        <a href="#" class="rcard"><div class="rcard__thumb"><div class="placeholder placeholder--c"><div class="placeholder__stripes"></div></div><span class="assoc-badge">↗ 84%</span><span class="source-badge">Podcast</span></div><div class="rcard__body"><h4 class="rcard__title">Latent Space：開發者如何在 6 個月內被 AI agent 取代或加倍</h4><div class="rcard__foot"><span class="tag-chip tag-chip--a">AI</span><span>28d</span></div></div></a>
        <a href="#" class="rcard"><div class="rcard__thumb"><div class="placeholder placeholder--d"><div class="placeholder__stripes"></div></div><span class="assoc-badge">↗ 76%</span><span class="source-badge">PDF</span></div><div class="rcard__body"><h4 class="rcard__title">Test-time Compute Scaling Laws (Anthropic, 2026)</h4><div class="rcard__foot"><span class="tag-chip tag-chip--a">AI</span><span>12d</span></div></div></a>
        <a href="#" class="rcard"><div class="rcard__thumb"><div class="placeholder placeholder--e"><div class="placeholder__stripes"></div></div><span class="assoc-badge">↗ 71%</span><span class="source-badge">Article</span></div><div class="rcard__body"><h4 class="rcard__title">Context Engineering: The new prompt engineering</h4><div class="rcard__foot"><span class="tag-chip tag-chip--a">AI</span><span>15d</span></div></div></a>
      </div>
    </main>

    <!-- SURPRISE -->
    <main v-show="activeTab === 'surprise'" class="ex-pane">
      <p class="focus-hint">系統主動為你撈出洞察、被遺忘的內容、以及你最近關注的主題趨勢。</p>
      <div class="insights">
        <article class="insight insight--connect">
          <header class="insight__head"><span class="ins-badge ins-badge--b">↗ 意外連結</span><span class="insight__when">剛剛產生</span></header>
          <h3 class="insight__title">這兩件事竟然有關聯</h3>
          <p class="insight__body">你 3 個月前存的「<em style="color:var(--tag-b);font-style:normal;">Notion 的 community-led growth</em>」和上週存的「<em style="color:var(--tag-b);font-style:normal;">Karpathy 對軟體 3.0 的看法</em>」，都引用了同一個觀點：產品的最小單位正在從「功能」變成「會自己跑的代理人」。</p>
          <div class="insight__foot">
            <a class="item-chip" href="#"><span class="item-chip__t"><span class="placeholder placeholder--d"><span class="placeholder__stripes"></span></span></span>Notion 的成長拆解</a>
            <a class="item-chip" href="#"><span class="item-chip__t"><span class="placeholder placeholder--b"><span class="placeholder__stripes"></span></span></span>Karpathy on Software 3.0</a>
            <div class="feedback"><button>👍</button><button>👎</button></div>
          </div>
        </article>

        <article class="insight insight--forgot">
          <header class="insight__head"><span class="ins-badge ins-badge--e">◌ 遺忘中</span><span class="insight__when">11 個月前存入</span></header>
          <h3 class="insight__title">你可能已經忘記這個了</h3>
          <p class="insight__body">去年 6 月你存了「<em style="color:var(--tag-e);font-style:normal;">Kenji 的紐約客版 ramen broth</em>」，看了兩次後就再也沒打開。最近你存了 4 篇日本食譜相關內容，這篇是其中關於高湯比例最詳盡的一份。要不要重看一次？</p>
          <div class="insight__foot">
            <a class="item-chip" href="#"><span class="item-chip__t"><span class="placeholder placeholder--e"><span class="placeholder__stripes"></span></span></span>Kenji 的 ramen broth</a>
            <button class="btn" style="height:30px; padding: 0 14px; font-size:12px; background:var(--warn-dim); color:var(--warn); border-color:var(--warn-bdr);">立即複習 →</button>
            <div class="feedback"><button>👍</button><button>👎</button></div>
          </div>
        </article>

        <article class="insight insight--pattern">
          <header class="insight__head"><span class="ins-badge ins-badge--a">◈ 主題趨勢</span><span class="insight__when">本月分析</span></header>
          <h3 class="insight__title">本月你最關注的三個主題</h3>
          <p class="insight__body">過去 30 天你存了 67 筆內容，主要集中在這三個主題。其中 <em style="color:var(--tag-a);font-style:normal;">AI</em> 的關注度比上個月增加了 42%。</p>
          <div class="topic-bars">
            <div class="topic-bar"><div class="topic-bar__col" data-pct="46" style="height: 80%;"></div><div class="topic-bar__label">AI</div></div>
            <div class="topic-bar"><div class="topic-bar__col" data-pct="28" style="height: 50%; opacity:0.7;"></div><div class="topic-bar__label">產品策略</div></div>
            <div class="topic-bar"><div class="topic-bar__col" data-pct="18" style="height: 32%; opacity:0.5;"></div><div class="topic-bar__label">設計</div></div>
            <div class="topic-bar"><div class="topic-bar__col" data-pct="8" style="height: 16%; opacity:0.35;"></div><div class="topic-bar__label">日本旅遊</div></div>
          </div>
          <div class="insight__foot">
            <span class="mono" style="font-size:11px; color:var(--text-dim);">基於最近 30 天 67 筆內容</span>
            <div class="feedback"><button>👍</button><button>👎</button></div>
          </div>
        </article>

        <article class="insight insight--connect">
          <header class="insight__head"><span class="ins-badge ins-badge--b">↗ 意外連結</span><span class="insight__when">3 小時前</span></header>
          <h3 class="insight__title">這兩篇都在說同一件事</h3>
          <p class="insight__body">「<em style="color:var(--tag-b);font-style:normal;">Linear 重新設計 sidebar 的 12 個版本</em>」和「<em style="color:var(--tag-b);font-style:normal;">Refactoring UI 的 grayscale 第一原則</em>」其實都是同一個訊息：好設計不是加東西，是<em style="color:var(--tag-b);font-style:normal;">敢拿掉的東西</em>。</p>
          <div class="insight__foot">
            <a class="item-chip" href="#"><span class="item-chip__t"><span class="placeholder placeholder--b"><span class="placeholder__stripes"></span></span></span>Linear sidebar 12 版</a>
            <a class="item-chip" href="#"><span class="item-chip__t"><span class="placeholder placeholder--c"><span class="placeholder__stripes"></span></span></span>Refactoring UI grayscale</a>
            <div class="feedback"><button>👍</button><button>👎</button></div>
          </div>
        </article>
      </div>
    </main>

    <!-- BROWSE -->
    <main v-show="activeTab === 'browse'" class="ex-pane">
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
  </div>
</template>

<script setup lang="ts">
const activeTab = ref<'focus' | 'surprise' | 'browse'>('focus')
const browseFilter = ref('all')
</script>

<style>
.ex-head { padding: 24px 32px 0; border-bottom: 1px solid var(--border); max-width: 1400px; margin: 0 auto; }
.ex-head__top { display: flex; align-items: flex-end; gap: 24px; padding-bottom: 14px; }
.ex-head__stats { margin-left: auto; display: flex; gap: 18px; font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); }
.stat b { display: block; color: var(--text); font-size: 16px; font-weight: 500; margin-bottom: 1px; }
.ex-tabs { display: flex; gap: 0; margin-bottom: -1px; }
.ex-tab { padding: 12px 18px 14px; border-bottom: 2px solid transparent; font-family: var(--font-ui); font-size: 13.5px; font-weight: 500; color: var(--text-mid); transition: all .15s ease; }
.ex-tab:hover { color: var(--text); }
.ex-tab--active { color: var(--accent); border-bottom-color: var(--accent); }
.ex-tab .mono { margin-left: 6px; font-size: 10.5px; color: var(--text-dim); }
.ex-tab--active .mono { color: var(--accent); opacity: 0.7; }
.ex-pane { max-width: 1400px; margin: 0 auto; padding: 28px 32px 80px; }

.focus-hint { font-size: 13px; color: var(--text-mid); margin-bottom: 12px; }
.focus-input-row { display: flex; gap: 10px; margin-bottom: 14px; }
.focus-input { flex: 1; background: var(--surface); border: 1px solid var(--border2); border-radius: 12px; padding: 14px 18px; font-family: var(--font-ui); font-size: 14px; color: var(--text); resize: none; outline: none; height: 52px; line-height: 1.5; transition: all .15s ease; }
.focus-input:focus { border-color: var(--accent-bdr); box-shadow: 0 0 0 3px var(--accent-dim); }
.focus-input::placeholder { color: var(--text-dim); }
.focus-submit { flex-shrink: 0; height: 52px; padding: 0 24px; border-radius: 10px; }
.focus-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 28px; }
.focus-chips .chip { font-family: var(--font-mono); font-size: 11.5px; padding: 6px 12px; border-radius: 16px; background: var(--surface2); color: var(--text-mid); border: 1px solid var(--border); cursor: pointer; transition: all .15s ease; }
.focus-chips .chip:hover { background: var(--accent-dim); color: var(--accent); border-color: var(--accent-bdr); }

.focus-loading { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px; margin-bottom: 24px; }
.pulse-row { display: flex; gap: 8px; margin-bottom: 14px; }
.pulse-row span { width: 9px; height: 9px; background: var(--accent); border-radius: 50%; animation: pulse 1.2s infinite; }
.pulse-row span:nth-child(2) { animation-delay: .18s; }
.pulse-row span:nth-child(3) { animation-delay: .36s; }
.pulse-row span:nth-child(4) { animation-delay: .54s; }
.pulse-row span:nth-child(5) { animation-delay: .72s; }
@keyframes pulse { 0%, 100% { transform: scale(1); opacity: 0.5; } 50% { transform: scale(1.5); opacity: 1; } }
.focus-loading__steps { display: flex; flex-direction: column; gap: 8px; font-family: var(--font-mono); font-size: 12px; color: var(--text-mid); padding: 0; margin: 0; }
.focus-loading__steps li { list-style: none; display: flex; align-items: center; gap: 8px; }
.focus-loading__steps li.done { color: var(--accent); }
.focus-loading__steps li.active { color: var(--text); }
.focus-loading__steps li::before { content: '○'; opacity: 0.5; }
.focus-loading__steps li.done::before { content: '✓'; opacity: 1; }
.focus-loading__steps li.active::before { content: '●'; opacity: 1; animation: blink 1s infinite; }
@keyframes blink { 50% { opacity: 0.4; } }

.synth { position: relative; background: var(--surface); border: 1px solid var(--accent-bdr); border-radius: 14px; padding: 22px 24px; margin-bottom: 24px; overflow: hidden; }
.synth::before { content: ''; position: absolute; left: 0; top: 0; width: 70%; height: 2px; background: linear-gradient(90deg, var(--accent), transparent); }
.synth__head { display: flex; align-items: center; margin-bottom: 14px; }
.synth__badge { display: inline-flex; align-items: center; gap: 6px; font-family: var(--font-mono); font-size: 10.5px; font-weight: 500; color: var(--accent); letter-spacing: 0.06em; }
.synth__badge::before { content: ''; width: 6px; height: 6px; background: var(--accent); border-radius: 50%; animation: blink 1.2s infinite; }
.synth__actions { margin-left: auto; display: flex; gap: 6px; }
.synth__actions button { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-mid); padding: 5px 10px; border-radius: 6px; border: 1px solid var(--border); background: transparent; transition: all .15s ease; }
.synth__actions button:hover { color: var(--text); background: var(--surface2); }
.synth__text { font-size: 13.5px; color: var(--text); line-height: 1.85; margin: 0; }
.synth__text em { font-style: normal; color: var(--accent); font-weight: 500; }
.synth__sources { margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border); display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.synth__sources .label { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); margin-right: 4px; }
.synth__sources .src-chip { font-family: var(--font-mono); font-size: 11px; color: var(--text-mid); padding: 4px 10px; background: var(--surface2); border: 1px solid var(--border); border-radius: 6px; transition: all .15s ease; }
.synth__sources .src-chip:hover { color: var(--accent); border-color: var(--accent-bdr); }

.result-head { display: flex; align-items: center; gap: 10px; margin: 18px 0 12px; }
.result-head .eyebrow { color: var(--text-dim); }
.result-head .line { flex: 1; height: 1px; background: var(--border); }
.result-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.rcard { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; transition: all .2s ease; cursor: pointer; }
.rcard:hover { transform: translateY(-3px); border-color: var(--border2); box-shadow: 0 10px 24px -10px var(--shadow); }
.rcard__thumb { height: 88px; position: relative; }
.rcard__thumb .source-badge { position: absolute; right: 8px; bottom: 8px; }
.rcard__thumb .assoc-badge { position: absolute; left: 8px; top: 8px; }
.rcard__body { padding: 11px 13px 13px; display: flex; flex-direction: column; gap: 10px; }
.rcard__title { font-size: 12.5px; font-weight: 500; line-height: 1.45; margin: 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.rcard__foot { display: flex; align-items: center; justify-content: space-between; font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); }

.insights { display: flex; flex-direction: column; gap: 12px; max-width: 920px; }
.insight { position: relative; background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 20px 22px 18px 26px; transition: all .15s ease; }
.insight:hover { transform: translateX(4px); }
.insight::before { content: ''; position: absolute; left: 0; top: 16px; bottom: 16px; width: 3px; border-radius: 2px; }
.insight--connect::before { background: var(--tag-b); }
.insight--connect:hover { border-color: var(--tag-b); }
.insight--forgot::before { background: var(--tag-e); }
.insight--forgot:hover { border-color: var(--tag-e); }
.insight--pattern::before { background: var(--tag-a); }
.insight--pattern:hover { border-color: var(--tag-a); }
.insight__head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.ins-badge { font-family: var(--font-mono); font-size: 10.5px; font-weight: 500; padding: 3px 10px; border-radius: 5px; }
.ins-badge--b { color: var(--tag-b); background: color-mix(in oklab, var(--tag-b) 14%, transparent); }
.ins-badge--e { color: var(--tag-e); background: color-mix(in oklab, var(--tag-e) 14%, transparent); }
.ins-badge--a { color: var(--tag-a); background: color-mix(in oklab, var(--tag-a) 14%, transparent); }
.insight__when { margin-left: auto; font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); }
.insight__title { font-family: var(--font-brand); font-weight: 600; font-size: 16.5px; line-height: 1.4; margin: 0 0 8px; }
.insight__body { font-size: 13px; color: var(--text-mid); line-height: 1.7; margin: 0 0 12px; }
.insight__foot { display: flex; gap: 8px; flex-wrap: wrap; padding-top: 10px; border-top: 1px solid var(--border); align-items: center; }
.feedback { margin-left: auto; display: flex; gap: 8px; font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); }
.feedback button { width: 26px; height: 26px; border-radius: 6px; background: var(--surface2); border: 1px solid var(--border); color: var(--text-mid); transition: all .15s ease; }
.feedback button:hover { color: var(--accent); border-color: var(--accent-bdr); }
.topic-bars { display: flex; align-items: flex-end; gap: 12px; height: 80px; margin: 12px 0 14px; padding: 0 4px; }
.topic-bar { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 6px; }
.topic-bar__col { width: 100%; background: var(--accent); border-radius: 4px 4px 0 0; position: relative; }
.topic-bar__col::after { content: attr(data-pct) '%'; position: absolute; top: -16px; left: 50%; transform: translateX(-50%); font-family: var(--font-mono); font-size: 9.5px; color: var(--accent); }
.topic-bar__label { font-family: var(--font-mono); font-size: 10px; color: var(--text-mid); }
.item-chip { display: inline-flex; align-items: center; gap: 8px; padding: 6px 10px; background: var(--surface2); border: 1px solid var(--border); border-radius: 8px; font-size: 11.5px; transition: all .15s ease; cursor: pointer; }
.item-chip:hover { background: var(--surface3); }
.item-chip__t { width: 24px; height: 18px; border-radius: 3px; overflow: hidden; }

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

@media (max-width: 980px) { .col-grid { grid-template-columns: repeat(2, 1fr); } .ex-head { padding: 18px 16px 0; } .ex-pane { padding: 20px 16px 60px; } }
@media (max-width: 640px) { .col-grid { grid-template-columns: 1fr; } .ex-head__stats { display: none; } .focus-input-row { flex-direction: column; } .focus-submit { width: 100%; } .browse-bar { flex-direction: column; } }
</style>
