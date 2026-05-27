<template>
  <div :class="{ 'pick-mode': pickMode }">
    <section class="ch-wrap">
      <div class="ch-mosaic">
        <div class="tile"><div class="placeholder placeholder--c"><div class="placeholder__stripes"></div><div class="placeholder__label">[ KYOTO TEMPLE ]</div></div></div>
        <div class="tile"><div class="placeholder placeholder--a"><div class="placeholder__stripes"></div></div></div>
        <div class="tile"><div class="placeholder placeholder--e"><div class="placeholder__stripes"></div></div></div>
        <div class="tile"><div class="placeholder placeholder--b"><div class="placeholder__stripes"></div><div class="placeholder__label">[ OSAKA NIGHT ]</div></div></div>
        <div class="tile"><div class="placeholder placeholder--d"><div class="placeholder__stripes"></div></div></div>
      </div>
      <div class="ch-content">
        <div class="ch-author">
          <span class="ch-author__av">YK</span>
          <span class="ch-author__name">@yuki_travels</span>
          <span class="ch-author__suffix">的公開集合</span>
        </div>
        <h1 class="ch-title">京都・大阪深度 14 天</h1>
        <p class="ch-desc">從早晨的清水寺路線到深夜的法善寺横丁，含 4 家不收訂金的隱藏 sushi。整理自我去年自己 14 天的行程。</p>
        <div class="ch-stats">
          <span class="ch-stat"><b>42</b> 件內容</span>
          <span class="ch-stat"><b>184</b> 次 Fork</span>
          <span class="ch-stat">建立於 6 天前</span>
          <span class="ch-stat">⭐ 1.2k stars</span>
        </div>
      </div>
    </section>

    <div class="cta-bar">
      <span class="ch-author__av" style="width:28px;height:28px;font-size:10px;">YK</span>
      <span class="cta-bar__title">京都・大阪深度 14 天</span>
      <span class="cta-bar__sub">42 件 · @yuki_travels</span>
      <div class="cta-bar__actions">
        <button class="btn" @click="pickMode = !pickMode">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
          {{ pickMode ? `已選 ${selectedCards.size} 件` : '挑選 Fork' }}
        </button>
        <button class="btn btn--accent">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="6" cy="3" r="2"/><circle cx="6" cy="21" r="2"/><circle cx="18" cy="12" r="2"/><path d="M6 5v6a4 4 0 0 0 4 4h6M6 13v6"/></svg>
          全部 Fork (42)
        </button>
      </div>
    </div>

    <section class="content-grid">
      <div
        v-for="item in items"
        :key="item.id"
        class="icard"
        :class="{ sel: selectedCards.has(item.id) }"
        @click="handleItemClick($event, item.id)"
      >
        <span class="icard__check">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
        </span>
        <div class="icard__thumb">
          <div :class="`placeholder placeholder--${item.color}`"><div class="placeholder__stripes"></div><div v-if="item.thumbLabel" class="placeholder__label">{{ item.thumbLabel }}</div></div>
          <span class="source-badge">{{ item.source }}</span>
        </div>
        <div class="icard__body">
          <h3 class="icard__title">{{ item.title }}</h3>
          <div class="icard__foot">
            <span :class="`tag-chip tag-chip--${item.tagColor}`">{{ item.tag }}</span>
            <a href="#" @click.stop>↗ {{ item.sourceLabel }}</a>
          </div>
        </div>
      </div>
    </section>

    <section class="rec-section">
      <header class="rec-head">
        <span class="eyebrow">你可能也喜歡</span>
        <span class="line"></span>
        <NuxtLink to="/app/explore" class="mono" style="font-size:11px; color:var(--text-mid);">查看全部 →</NuxtLink>
      </header>
      <div class="rec-scroll">
        <NuxtLink v-for="rec in recs" :key="rec.slug" class="rec-card" :to="`/share/${rec.slug}`">
          <div class="rec-card__cover">
            <div class="t"><div :class="`placeholder placeholder--${rec.c1}`"><div class="placeholder__stripes"></div></div></div>
            <div class="t"><div :class="`placeholder placeholder--${rec.c2}`"><div class="placeholder__stripes"></div></div></div>
          </div>
          <div class="rec-card__body">
            <h4 class="rec-card__title">{{ rec.title }}</h4>
            <div class="rec-card__meta">{{ rec.meta }}</div>
          </div>
        </NuxtLink>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
useHead({ title: '京都・大阪深度 14 天 — Vela' })

const pickMode = ref(false)
const selectedCards = reactive(new Set<number>())

const handleItemClick = (e: MouseEvent, id: number) => {
  if (!pickMode.value) return
  e.preventDefault()
  if (selectedCards.has(id)) {
    selectedCards.delete(id)
  } else {
    selectedCards.add(id)
  }
}

const items = [
  { id: 1,  color: 'c', thumbLabel: '[ 嵐山竹林 ]', source: 'Article',    title: '京都嵐山竹林 7am 完全沒人的拍照路線（含 GPS）',         tag: '日本旅遊', tagColor: 'c', sourceLabel: '原文' },
  { id: 2,  color: 'a', thumbLabel: null,             source: 'Maps',       title: '大阪 18 家不需訂位但值得一吃的居酒屋（含營業時間）',     tag: '美食',     tagColor: 'e', sourceLabel: 'Maps' },
  { id: 3,  color: 'b', thumbLabel: null,             source: '▶ YouTube', title: '京都市巴士萬用攻略：1 日券 vs 地下鐵 1 日券',           tag: '交通',     tagColor: 'c', sourceLabel: '影片' },
  { id: 4,  color: 'd', thumbLabel: null,             source: 'IG',         title: '京都和服體驗：四條河原町站 5 分鐘的 3 家比較',           tag: '日本旅遊', tagColor: 'c', sourceLabel: 'IG' },
  { id: 5,  color: 'e', thumbLabel: null,             source: 'Article',    title: '大阪燒 vs 廣島燒：給觀光客的 5 分鐘區別指南',           tag: '美食',     tagColor: 'e', sourceLabel: '原文' },
  { id: 6,  color: 'c', thumbLabel: null,             source: 'Maps',       title: '京都祇園夜間步行路線：7:30pm 後該怎麼走',               tag: '日本旅遊', tagColor: 'c', sourceLabel: 'Maps' },
  { id: 7,  color: 'a', thumbLabel: null,             source: '𝕏 Post',    title: '大阪到名古屋的新幹線最便宜訂票時段',                     tag: '交通',     tagColor: 'c', sourceLabel: 'Twitter' },
  { id: 8,  color: 'b', thumbLabel: null,             source: 'Article',    title: '京都 4 家不收訂金的隱藏 omakase（含老闆 IG）',          tag: '美食',     tagColor: 'e', sourceLabel: '原文' },
  { id: 9,  color: 'd', thumbLabel: null,             source: 'Note',       title: '14 天 vs 10 天行程取捨：我會砍掉哪些景點',              tag: '行程',     tagColor: 'c', sourceLabel: 'Note' },
  { id: 10, color: 'c', thumbLabel: null,             source: '▶ YouTube', title: '奈良公園鹿的 5 個冷知識（為什麼牠們會鞠躬）',            tag: '日本旅遊', tagColor: 'c', sourceLabel: '影片' },
  { id: 11, color: 'e', thumbLabel: null,             source: 'Article',    title: '大阪心齋橋一蘭凌晨 23:00 後變半小時的時段',             tag: '美食',     tagColor: 'e', sourceLabel: '原文' },
  { id: 12, color: 'accent', thumbLabel: null,        source: 'Note',       title: '便利商店早餐排行：711 vs Lawson vs Family Mart',         tag: '美食',     tagColor: 'e', sourceLabel: 'Note' },
]

const recs = [
  { slug: 'tokyo-local',  title: '東京 7 天 — 在地人路線',      c1: 'a', c2: 'b', meta: '@tk_local · 28 items · ⑂ 256' },
  { slug: 'okinawa',      title: '沖繩離島跳島 9 天',            c1: 'c', c2: 'e', meta: '@ocean_runner · 36 items · ⑂ 142' },
  { slug: 'kanazawa',     title: '北陸新幹線開通後的金澤行程',   c1: 'd', c2: 'a', meta: '@yuki_travels · 22 items · ⑂ 89' },
  { slug: 'kyoto-hidden', title: '京都祕境 — 不在 Google Maps 的 12 個地點', c1: 'b', c2: 'c', meta: '@hiddenkyoto · 18 items · ⑂ 67' },
]
</script>

<style>
/* Shares the same CSS as app/collection/[id].vue — kept local to avoid flash */
.ch-wrap {
  position: relative;
  height: 320px;
  margin-bottom: 0;
  overflow: hidden;
}
.ch-mosaic {
  position: absolute; inset: 0;
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 2fr;
  grid-template-rows: 1fr 1fr;
  gap: 2px;
}
.ch-mosaic .tile { overflow: hidden; }
.ch-mosaic .tile:nth-child(1) { grid-row: 1 / span 2; }
.ch-mosaic .tile:nth-child(4) { grid-column: 4; grid-row: 1 / span 2; }
.ch-mosaic::after {
  content: '';
  position: absolute; inset: 0;
  background: linear-gradient(180deg, transparent 30%, var(--bg) 95%);
}
.ch-content {
  position: absolute;
  left: 32px; right: 32px;
  bottom: 28px;
  z-index: 2;
  max-width: 720px;
}
.ch-author {
  display: inline-flex; align-items: center; gap: 10px;
  margin-bottom: 12px;
}
.ch-author__av {
  width: 36px; height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--tag-c), var(--tag-a));
  color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
  font-family: var(--font-mono); font-size: 12px; font-weight: 500;
  border: 1px solid var(--border2);
}
.ch-author__name { font-weight: 500; font-size: 13.5px; }
.ch-author__suffix { font-family: var(--font-mono); font-size: 11px; color: var(--text-mid); margin-left: 4px; }
.ch-title {
  font-family: var(--font-brand);
  font-weight: 700;
  font-size: 36px;
  letter-spacing: -0.02em;
  margin: 0 0 10px;
  line-height: 1.15;
  text-wrap: balance;
}
.ch-desc {
  color: var(--text-mid);
  font-size: 14px;
  line-height: 1.6;
  margin: 0 0 14px;
  max-width: 580px;
}
.ch-stats {
  display: flex; gap: 14px; flex-wrap: wrap;
  font-family: var(--font-mono); font-size: 11.5px;
  color: var(--text-mid);
}
.ch-stats b { color: var(--text); font-weight: 500; }
.ch-stat::after { content: '·'; margin-left: 14px; color: var(--text-dim); }
.ch-stat:last-child::after { display: none; }
.cta-bar {
  position: sticky; top: 52px;
  z-index: 30;
  padding: 12px 32px;
  background: var(--nav-bg);
  backdrop-filter: blur(18px);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 12px;
}
.cta-bar__title { font-family: var(--font-brand); font-weight: 600; font-size: 14px; }
.cta-bar__sub { margin-left: 12px; font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); }
.cta-bar__actions { margin-left: auto; display: flex; gap: 8px; }
.content-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
  padding: 28px 32px 48px;
  max-width: 1400px;
  margin: 0 auto;
}
.icard {
  position: relative;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all .2s ease;
}
.icard:hover { transform: translateY(-3px); border-color: var(--border2); box-shadow: 0 12px 28px -12px var(--shadow); }
.icard__check {
  position: absolute; top: 10px; left: 10px;
  z-index: 3;
  width: 22px; height: 22px;
  border-radius: 6px;
  background: rgba(0,0,0,0.55);
  border: 1.5px solid #fff;
  backdrop-filter: blur(4px);
  display: none; align-items: center; justify-content: center;
  color: #fff;
}
.pick-mode .icard__check { display: inline-flex; }
.icard.sel .icard__check { background: var(--accent); border-color: var(--accent); color: var(--accent-fg); }
.icard__check svg { width: 14px; height: 14px; }
.icard__thumb { height: 130px; position: relative; }
.icard__thumb .source-badge { position: absolute; right: 8px; bottom: 8px; }
.icard__body { padding: 12px 14px 14px; display: flex; flex-direction: column; gap: 10px; }
.icard__title {
  font-size: 13px; font-weight: 500;
  line-height: 1.45; margin: 0;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.icard__foot { display: flex; align-items: center; justify-content: space-between; }
.icard__foot a { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); transition: color .15s ease; }
.icard__foot a:hover { color: var(--accent); }
.rec-section { border-top: 1px solid var(--border); padding: 30px 32px 60px; max-width: 1400px; margin: 0 auto; }
.rec-head { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.rec-head .line { flex: 1; height: 1px; background: var(--border); }
.rec-scroll { display: flex; gap: 14px; overflow-x: auto; padding-bottom: 8px; scrollbar-width: none; }
.rec-scroll::-webkit-scrollbar { display: none; }
.rec-card {
  flex: 0 0 240px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; overflow: hidden;
  transition: all .2s ease; text-decoration: none; color: inherit;
}
.rec-card:hover { transform: translateY(-3px); border-color: var(--border2); }
.rec-card__cover { height: 100px; display: grid; grid-template-columns: 2fr 1fr; gap: 2px; }
.rec-card__cover .t { overflow: hidden; }
.rec-card__body { padding: 12px 14px 14px; }
.rec-card__title { font-family: var(--font-brand); font-weight: 600; font-size: 14px; margin: 0 0 6px; line-height: 1.3; }
.rec-card__meta { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-mid); }
@media (max-width: 768px) {
  .ch-content { left: 18px; right: 18px; bottom: 18px; }
  .ch-title { font-size: 24px; }
  .cta-bar { padding: 10px 16px; flex-wrap: wrap; }
  .cta-bar__actions { width: 100%; }
  .content-grid { padding: 20px 16px 40px; gap: 10px; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); }
  .rec-section { padding: 24px 16px 40px; }
}
</style>
