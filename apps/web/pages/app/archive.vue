<template>
  <main class="shell">
    <header class="arc-head">
      <span class="eyebrow">ARCHIVE</span>
      <h1 class="page-title">封存庫</h1>
      <p>封存的內容不會出現在首頁和搜尋結果，但隨時可以復原。</p>
    </header>

    <div class="banner">
      <span class="banner__icon">📁</span>
      <span>封存內容共 <b>248 筆</b>，不佔用首頁與搜尋結果。</span>
      <a href="#" class="banner__action mono" style="color:var(--text-mid); font-size:11px;">了解封存機制 →</a>
    </div>
    <div class="banner banner--warn">
      <span class="banner__icon">⏳</span>
      <span>有 <b>3 筆</b>內容即將於 24 小時後永久刪除，趕快復原！</span>
      <a href="#danger" class="banner__action mono" style="font-size:11px;">前往查看 →</a>
    </div>

    <div class="toolbar">
      <span class="eyebrow" style="margin-right:4px;">SORT</span>
      <div class="toolbar__group">
        <button class="sort-btn" :class="{ 'sort-btn--active': sortBy === 'date' }" @click="sortBy = 'date'">封存日期</button>
        <button class="sort-btn" :class="{ 'sort-btn--active': sortBy === 'oldest' }" @click="sortBy = 'oldest'">最舊優先</button>
        <button class="sort-btn" :class="{ 'sort-btn--active': sortBy === 'type' }" @click="sortBy = 'type'">來源類型</button>
      </div>
      <div class="toolbar__right">
        <button class="sort-btn" @click="toggleAll">全選</button>
        <span>248 項封存 · 3 待刪除</span>
      </div>
    </div>

    <!-- Selection bar -->
    <div v-if="selectedIds.size > 0" class="selbar">
      <span class="selbar__count">已選 {{ selectedIds.size }} 項</span>
      <button class="btn" style="background:var(--accent-dim); color:var(--accent); border-color:var(--accent-bdr);">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/></svg>
        復原
      </button>
      <button class="btn btn--danger" @click="showConfirm = true">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>
        永久刪除
      </button>
      <div class="spacer"></div>
      <button class="btn btn--ghost" @click="selectedIds.clear()">取消</button>
    </div>

    <!-- Archive items -->
    <div class="alist">
      <div
        v-for="item in items"
        :key="item.id"
        class="aitem"
        :class="{ selected: selectedIds.has(item.id) }"
        @click="toggleItem(item.id, $event)"
      >
        <span class="checkbox">
          <svg v-if="selectedIds.has(item.id)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
        </span>
        <div class="aitem__thumb">
          <div :class="`placeholder placeholder--${item.color}`"><div class="placeholder__stripes"></div></div>
        </div>
        <div class="aitem__main">
          <h3 class="aitem__title">{{ item.title }}</h3>
          <div class="aitem__meta">
            <span>{{ item.source }}</span>
            <span class="aitem__dot"></span>
            <span>{{ item.domain }}</span>
            <span class="aitem__dot"></span>
            <span :class="`tag-chip tag-chip--${item.tagColor}`" style="font-size:9px;padding:1px 7px;">{{ item.tag }}</span>
          </div>
        </div>
        <span class="aitem__when">{{ item.when }}</span>
        <div class="aitem__actions">
          <button class="btn" style="height:30px;padding:0 12px;font-size:12px;" @click.stop>復原</button>
          <button class="btn" style="height:30px;padding:0 10px;font-size:12px;" @click.stop>⋯</button>
        </div>
      </div>
    </div>

    <!-- Danger zone -->
    <header class="danger-head" id="danger">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" style="color:var(--warn)"><path d="M12 9v4M12 17h.01M10.3 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/></svg>
      <span class="mono">即將永久刪除</span>
      <span class="danger-head__count">3 筆 · 24 小時後從系統清除</span>
    </header>

    <div class="alist">
      <div v-for="item in dangerItems" :key="item.id" class="aitem aitem--danger">
        <span class="checkbox"></span>
        <div class="aitem__thumb"><div :class="`placeholder placeholder--${item.color}`"><div class="placeholder__stripes"></div></div></div>
        <div class="aitem__main">
          <h3 class="aitem__title">{{ item.title }}</h3>
          <div class="aitem__meta">
            <span class="countdown">剩 {{ item.countdown }}</span>
            <span class="aitem__dot"></span>
            <span>{{ item.source }} · {{ item.when }}</span>
          </div>
        </div>
        <span class="aitem__when"></span>
        <div class="aitem__actions"><button class="btn btn--warn" @click.stop>復原</button></div>
      </div>
    </div>
  </main>

  <!-- Confirm modal -->
  <div v-if="showConfirm" class="modal-mask" @click.self="showConfirm = false">
    <div class="modal">
      <h2>確認永久刪除</h2>
      <p>這個動作<b style="color:var(--danger)">無法復原</b>。以下內容將從你的知識庫中完全移除，包含摘要與關聯資料。</p>
      <div class="modal__list">
        <div class="modal__list-item">Substack：The Cold Start Problem</div>
        <div class="modal__list-item">YouTube：Andrew Ng 在 Jupyter 講課</div>
      </div>
      <div class="modal__actions">
        <button class="btn btn--danger" style="flex:1;">永久刪除（{{ selectedIds.size }} 筆）</button>
        <button class="btn" @click="showConfirm = false">取消</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const sortBy = ref('date')
const showConfirm = ref(false)
const selectedIds = reactive(new Set<number>())

const items = [
  { id: 1, title: 'Substack 文章：The Cold Start Problem — Reid Hoffman 對網路效應的拆解', source: 'Article', domain: 'substack.com', tag: '產品策略', tagColor: 'd', color: 'a', when: '封存於 3 天前' },
  { id: 2, title: 'YouTube：Andrew Ng 為什麼還在用 Jupyter 講課（30 分鐘）', source: '▶ YouTube', domain: 'youtube.com', tag: 'AI', tagColor: 'a', color: 'b', when: '封存於 8 天前' },
  { id: 3, title: '京都祇園夜間步行路線 — 一張地圖告訴你 7:30pm 之後該怎麼走', source: 'Article', domain: 'blog.gaijinpot.com', tag: '日本旅遊', tagColor: 'c', color: 'c', when: '封存於 12 天前' },
  { id: 4, title: "Kenji 的紐約客版 ramen broth — 為什麼鍋蓋一定要打開煮", source: 'Article', domain: 'seriouseats.com', tag: '食譜', tagColor: 'e', color: 'e', when: '封存於 18 天前' },
  { id: 5, title: 'Twitter 串：為什麼大部分 design system 第二年就死了（22 則）', source: '𝕏 Post', domain: 'twitter.com', tag: '設計', tagColor: 'b', color: 'd', when: '封存於 24 天前' },
  { id: 6, title: 'Paper：Mixture-of-Experts vs Dense Transformer 在小資源下的對比 (2025)', source: 'PDF', domain: 'arxiv.org', tag: 'AI', tagColor: 'a', color: 'a', when: '封存於 31 天前' },
]

const dangerItems = [
  { id: 'd1', title: '舊書評：《Hooked》— 為什麼上癮模型在 2026 年已經不成立', source: 'Article', when: '一年前封存', countdown: '18:42:33', color: 'd' },
  { id: 'd2', title: 'YouTube 看到一半的 React 18 Suspense 講座 (45 分鐘)', source: '▶ YouTube', when: '14 個月前封存', countdown: '12:08:47', color: 'b' },
  { id: 'd3', title: '過期的旅遊 deal：2024 北海道 4 天 3 夜 hahn air 機票', source: 'Article', when: '18 個月前封存', countdown: '04:21:09', color: 'e' },
]

selectedIds.add(1)
selectedIds.add(2)

function toggleItem(id: number, e: MouseEvent) {
  if ((e.target as HTMLElement).closest('.btn')) return
  if (selectedIds.has(id)) selectedIds.delete(id)
  else selectedIds.add(id)
}

function toggleAll() {
  if (selectedIds.size === items.length) selectedIds.clear()
  else items.forEach(i => selectedIds.add(i.id))
}
</script>

<style>
.arc-head { margin: 24px 0 16px; }
.arc-head h1 { margin: 4px 0 6px; }
.arc-head p { color: var(--text-mid); font-size: 13px; margin: 0; }

.banner { display: flex; align-items: center; gap: 14px; padding: 14px 18px; border-radius: 12px; margin-bottom: 12px; border: 1px solid var(--border); background: var(--surface2); font-size: 13px; }
.banner__icon { width: 28px; height: 28px; border-radius: 8px; display: inline-flex; align-items: center; justify-content: center; background: var(--surface3); color: var(--text-mid); font-size: 14px; }
.banner--warn { background: var(--warn-dim); border-color: var(--warn-bdr); color: var(--warn); }
.banner--warn .banner__icon { background: rgba(245,158,11,0.18); color: var(--warn); }
.banner b { color: var(--text); font-weight: 600; }
.banner--warn b { color: var(--warn); }
.banner__action { margin-left: auto; }

.toolbar { display: flex; align-items: center; gap: 8px; padding: 14px 0 12px; border-bottom: 1px solid var(--border); margin: 18px 0 14px; }
.toolbar__group { display: flex; gap: 6px; }
.sort-btn { font-family: var(--font-mono); font-size: 11.5px; color: var(--text-mid); padding: 6px 10px; border-radius: 8px; border: 1px solid transparent; transition: all .15s ease; }
.sort-btn:hover { background: var(--surface2); color: var(--text); }
.sort-btn--active { background: var(--surface2); color: var(--text); border-color: var(--border2); }
.toolbar__right { margin-left: auto; display: flex; align-items: center; gap: 12px; color: var(--text-mid); font-family: var(--font-mono); font-size: 11.5px; }

.selbar { position: sticky; top: 60px; z-index: 10; margin: 0 0 14px; padding: 12px 16px; background: var(--surface); border: 1px solid var(--border2); border-radius: 12px; display: flex; align-items: center; gap: 10px; box-shadow: 0 8px 24px -12px var(--shadow); backdrop-filter: blur(12px); }
.selbar__count { font-family: var(--font-mono); font-size: 12px; color: var(--accent); padding: 5px 10px; background: var(--accent-dim); border-radius: 6px; border: 1px solid var(--accent-bdr); }

.alist { display: flex; flex-direction: column; gap: 8px; }
.aitem { display: grid; grid-template-columns: 28px 84px 1fr auto auto; gap: 14px; align-items: center; padding: 12px 14px; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; opacity: 0.88; transition: all .15s ease; cursor: pointer; }
.aitem:hover { opacity: 1; background: var(--surface2); transform: translateY(-1px); }
.aitem.selected { border-color: var(--accent-bdr); background: var(--accent-dim); opacity: 1; }
.checkbox { width: 18px; height: 18px; border-radius: 5px; border: 1.5px solid var(--border2); background: var(--surface); display: inline-flex; align-items: center; justify-content: center; transition: all .15s ease; flex-shrink: 0; margin: 0 auto; }
.aitem.selected .checkbox { background: var(--accent); border-color: var(--accent); color: var(--accent-fg); }
.checkbox svg { width: 12px; height: 12px; }
.aitem__thumb { width: 84px; height: 56px; border-radius: 6px; overflow: hidden; filter: grayscale(35%); flex-shrink: 0; }
.aitem__main { min-width: 0; display: flex; flex-direction: column; gap: 6px; }
.aitem__title { font-size: 13.5px; font-weight: 500; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin: 0; }
.aitem__meta { display: flex; align-items: center; gap: 8px; font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); }
.aitem__dot { width: 2px; height: 2px; background: var(--text-dim); border-radius: 50%; }
.aitem__when { font-family: var(--font-mono); font-size: 11.5px; color: var(--text-mid); white-space: nowrap; }
.aitem__actions { display: flex; gap: 6px; }

.danger-head { margin: 36px 0 14px 0; display: flex; align-items: center; gap: 12px; padding-bottom: 10px; border-bottom: 1px solid var(--warn-bdr); }
.danger-head .mono { color: var(--warn); font-size: 11.5px; letter-spacing: 0.06em; text-transform: uppercase; }
.danger-head__count { margin-left: auto; font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); }
.aitem--danger { background: rgba(239,68,68,0.04); border-color: var(--danger-bdr); opacity: 0.95; }
.aitem--danger:hover { background: rgba(239,68,68,0.07); }
.countdown { font-family: var(--font-mono); font-size: 10.5px; font-weight: 500; color: var(--danger); padding: 4px 8px; border: 1px solid var(--danger-bdr); border-radius: 6px; background: rgba(239,68,68,0.06); white-space: nowrap; }

.modal-mask { position: fixed; inset: 0; z-index: 200; background: rgba(0,0,0,0.6); backdrop-filter: blur(6px); display: flex; align-items: center; justify-content: center; padding: 20px; }
.modal { width: 100%; max-width: 420px; background: var(--surface); border: 1px solid var(--border2); border-radius: 16px; padding: 28px 30px; box-shadow: 0 24px 64px -20px var(--shadow); }
.modal h2 { font-family: var(--font-brand); font-weight: 600; font-size: 19px; margin: 0 0 10px; }
.modal p { color: var(--text-mid); font-size: 13px; line-height: 1.65; margin: 0 0 18px; }
.modal__list { background: var(--surface2); border-radius: 10px; padding: 12px 14px; margin-bottom: 22px; border: 1px solid var(--border); display: flex; flex-direction: column; gap: 6px; }
.modal__list-item { font-size: 12.5px; color: var(--text-mid); display: flex; align-items: center; gap: 8px; }
.modal__list-item::before { content: '•'; color: var(--text-dim); }
.modal__actions { display: flex; gap: 10px; }

@media (max-width: 768px) {
  .aitem { grid-template-columns: 22px 64px 1fr; grid-template-areas: "chk thumb main" "chk thumb actions"; gap: 10px; }
  .aitem__thumb { width: 64px; height: 48px; }
  .aitem__main { grid-area: main; }
  .aitem__when { display: none; }
  .aitem__actions { grid-area: actions; }
  .selbar { flex-wrap: wrap; }
  .banner { flex-wrap: wrap; }
  .banner__action { margin-left: 0; }
}
</style>
