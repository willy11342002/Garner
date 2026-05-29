<template>
  <main class="ex-pane">
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
</template>

<style>
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
</style>
