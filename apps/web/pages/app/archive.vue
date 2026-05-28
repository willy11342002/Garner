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
