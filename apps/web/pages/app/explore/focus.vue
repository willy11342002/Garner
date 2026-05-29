<template>
  <main class="ex-pane">
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
</template>

<style>
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

@media (max-width: 640px) { .focus-input-row { flex-direction: column; } .focus-submit { width: 100%; } }
</style>
