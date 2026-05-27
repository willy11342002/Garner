<template>
  <main class="share-shell">
    <span class="eyebrow">SHARE COLLECTION</span>
    <h1 class="page-title" style="margin:6px 0 24px;">分享一個集合</h1>

    <!-- Stepper -->
    <div class="stepper" :data-step="currentStep">
      <div class="step" :class="{ 'step--done': currentStep > 1, 'step--current': currentStep === 1 }">
        <span class="step__circle">
          <template v-if="currentStep > 1">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
          </template>
          <template v-else>1</template>
        </span>
        <span class="step__label">1. 選擇來源</span>
      </div>
      <div class="step" :class="{ 'step--done': currentStep > 2, 'step--current': currentStep === 2 }">
        <span class="step__circle">
          <template v-if="currentStep > 2">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
          </template>
          <template v-else>2</template>
        </span>
        <span class="step__label">2. 微調內容</span>
      </div>
      <div class="step" :class="{ 'step--current': currentStep === 3 }">
        <span class="step__circle">3</span>
        <span class="step__label">3. 設定公開</span>
      </div>
    </div>

    <!-- Step 1 — Tag picker -->
    <section class="step-section" :class="{ 'is-disabled': currentStep > 1 }">
      <span class="step-section__num">STEP 1 · {{ currentStep > 1 ? '已完成' : '進行中' }}</span>
      <h2>從哪個標籤建立集合？</h2>
      <p class="desc">系統會把這個標籤底下的所有內容帶入集合，下一步可以微調。</p>
      <div class="tag-grid">
        <button
          v-for="tag in tags"
          :key="tag.name"
          class="tag-pick"
          :class="{ sel: selectedTag === tag.name }"
          @click="selectedTag = tag.name"
        >
          <span class="dot" :style="{ background: `var(--tag-${tag.color})` }"></span>
          <span class="name">{{ tag.name }}</span>
          <span class="count">{{ tag.count }} 筆</span>
          <span class="thumbs">
            <span v-for="c in tag.thumbColors" :key="c" class="t">
              <span :class="`placeholder placeholder--${c}`"><span class="placeholder__stripes"></span></span>
            </span>
          </span>
          <span class="check" v-if="selectedTag === tag.name">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
          </span>
        </button>
      </div>
      <div class="step-foot">
        <span class="spacer"></span>
        <button class="btn btn--accent" @click="currentStep = 2" :disabled="!selectedTag">下一步 →</button>
      </div>
    </section>

    <!-- Step 2 — Content picker -->
    <section class="step-section" :class="{ 'is-disabled': currentStep < 2 }">
      <span class="step-section__num">STEP 2 · {{ currentStep < 2 ? '待完成' : currentStep > 2 ? '已完成' : '進行中' }}</span>
      <h2>選擇要包含哪些內容</h2>
      <p class="desc">預設全選，點擊取消勾選你不想公開的項目。</p>

      <div class="select-all">
        <button class="pill" @click="toggleAllItems">{{ selectedItems.size === contentItems.length ? '取消全選' : '全選' }}</button>
        <span class="spacer" style="flex:1;"></span>
        <span>共 {{ contentItems.length }} 筆 · 已選 {{ selectedItems.size }}</span>
      </div>

      <div class="clist">
        <div
          v-for="item in contentItems"
          :key="item.id"
          class="citem"
          :class="{ unsel: !selectedItems.has(item.id) }"
          @click="toggleItem(item.id)"
        >
          <span class="checkbox">
            <svg v-if="selectedItems.has(item.id)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
          </span>
          <div class="citem__thumb">
            <div :class="`placeholder placeholder--${item.color}`"><div class="placeholder__stripes"></div></div>
          </div>
          <div class="citem__main">
            <h4 class="citem__title">{{ item.title }}</h4>
            <div class="citem__meta">
              <span :class="`tag-chip tag-chip--${item.tagColor}`">{{ item.tag }}</span>
              <span>{{ item.src }} · {{ item.age }}</span>
            </div>
          </div>
          <span class="citem__src">{{ item.srcLabel }}</span>
        </div>
      </div>

      <div class="step-foot">
        <span class="mono" style="color:var(--accent);">已選 {{ selectedItems.size }} / {{ contentItems.length }} 筆</span>
        <span class="spacer"></span>
        <button class="btn" @click="currentStep = 1">← 上一步</button>
        <button class="btn btn--accent" @click="currentStep = 3">下一步 →</button>
      </div>
    </section>

    <!-- Step 3 — Visibility -->
    <section class="step-section" :class="{ 'is-disabled': currentStep < 3 }">
      <span class="step-section__num">STEP 3 · {{ currentStep < 3 ? '待完成' : '預覽' }}</span>
      <h2>設定這個集合的公開程度</h2>
      <p class="desc">你可以隨時改變公開設定，原本 Fork 過的人不會被回收。</p>

      <div class="vis-row">
        <div>
          <div class="vis-options">
            <label v-for="opt in visOptions" :key="opt.value" class="vis-opt" :class="{ sel: visibility === opt.value }" @click="visibility = opt.value">
              <div class="vis-opt__head">
                <span>{{ opt.icon }}</span>
                <span class="vis-opt__title">{{ opt.label }}</span>
                <span class="radio"></span>
              </div>
              <p class="vis-opt__desc">{{ opt.desc }}</p>
              <div v-if="opt.value === 'public' && visibility === 'public'" class="link-box">
                <span>vela.app/c/</span>
                <code>chenli/kyoto-osaka-14d</code>
                <button class="btn" style="height:24px; padding:0 8px; font-size:11px;" @click.stop>複製</button>
              </div>
            </label>
          </div>

          <div class="form-row">
            <label>集合標題</label>
            <input class="input" v-model="collectionTitle" />
          </div>
          <div class="form-row">
            <label>集合描述（選填）</label>
            <textarea class="input" v-model="collectionDesc" placeholder="告訴別人這個集合在說什麼..."></textarea>
          </div>
        </div>

        <div>
          <div class="preview-card">
            <header class="preview-card__head">即時預覽</header>
            <div class="preview-card__cover">
              <div class="t"><div class="placeholder placeholder--c"><div class="placeholder__stripes"></div></div></div>
              <div class="t"><div class="placeholder placeholder--a"><div class="placeholder__stripes"></div></div></div>
              <div class="t"><div class="placeholder placeholder--e"><div class="placeholder__stripes"></div></div></div>
            </div>
            <div class="preview-card__body">
              <h3 class="preview-card__title">{{ collectionTitle || '（無標題）' }}</h3>
              <p class="preview-card__desc">{{ collectionDesc || '尚未填寫描述' }}</p>
              <div class="preview-card__user">
                <span class="preview-card__avatar">CL</span>
                <span>@chenli · 剛剛建立</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="step-foot">
        <button class="btn" @click="currentStep = 2">← 上一步</button>
        <span class="spacer"></span>
        <button class="btn btn--accent btn--lg" @click="publish">建立並分享 →</button>
      </div>
    </section>

    <!-- Success Toast -->
    <aside v-if="showToast" class="toast">
      <div class="toast__head">
        <span class="ico">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"><polyline points="5 12 10 17 19 7"/></svg>
        </span>
        <span class="toast__title">集合已建立</span>
        <span style="flex:1;"></span>
        <button style="color:var(--text-dim); font-size:14px;" @click="showToast = false">×</button>
      </div>
      <div class="toast__link">
        <span>🔗</span>
        <code>vela.app/c/chenli/kyoto-osaka-14d</code>
      </div>
      <div class="toast__actions">
        <button class="btn" @click="copyLink">複製連結</button>
        <NuxtLink to="/app/collection/1" class="btn btn--accent">前往查看 →</NuxtLink>
      </div>
    </aside>
  </main>
</template>

<script setup lang="ts">
const currentStep = ref(2)
const selectedTag = ref('日本旅遊')
const visibility = ref<'private' | 'link' | 'public'>('public')
const collectionTitle = ref('京都・大阪深度 14 天')
const collectionDesc = ref('從早晨的清水寺到深夜的法善寺横丁，含 4 家不需要訂金的隱藏 sushi。整理自我去年自己 14 天的行程。')
const showToast = ref(false)

const tags = [
  { name: 'AI',     color: 'a', count: 142, thumbColors: ['a', 'b', 'c'] },
  { name: '設計',   color: 'b', count: 87,  thumbColors: ['b', 'c', 'a'] },
  { name: '日本旅遊', color: 'c', count: 34, thumbColors: ['c', 'a', 'b'] },
  { name: '產品策略', color: 'd', count: 56, thumbColors: ['d', 'a', 'b'] },
  { name: '食譜',   color: 'e', count: 23,  thumbColors: ['e', 'c', 'a'] },
  { name: '遠端工作', color: 'b', count: 19, thumbColors: ['b', 'd', 'c'] },
]

const contentItems = [
  { id: 1, color: 'c', title: '京都嵐山竹林 7am 完全沒人的拍照路線',             tag: '日本旅遊', tagColor: 'c', src: 'IG',      age: '1d ago',  srcLabel: 'IG' },
  { id: 2, color: 'a', title: '金澤 vs 富山：北陸新幹線開通後的客流量轉移',       tag: '日本旅遊', tagColor: 'c', src: 'Article', age: '6d ago',  srcLabel: 'Note' },
  { id: 3, color: 'b', title: '心齋橋一蘭凌晨 23:00 後排隊時間：個人經驗',       tag: '日本旅遊', tagColor: 'c', src: 'TikTok', age: '11d ago', srcLabel: 'TikTok' },
  { id: 4, color: 'd', title: '東京：18 家不需訂位但值得一吃的居酒屋清單',        tag: '日本旅遊', tagColor: 'c', src: 'Maps',   age: '19d ago', srcLabel: 'Maps' },
  { id: 5, color: 'e', title: '京都祇園夜間步行路線 — 一張地圖告訴你 7:30pm 之後該怎麼走', tag: '日本旅遊', tagColor: 'c', src: 'Article', age: '22d ago', srcLabel: 'Article' },
  { id: 6, color: 'c', title: '[個人筆記] 我的 JR Pass 行程草稿 v3（不適合公開）', tag: '日本旅遊', tagColor: 'c', src: 'Note',   age: '28d ago', srcLabel: 'Note' },
  { id: 7, color: 'a', title: '大阪到名古屋的新幹線最便宜訂票時段（每月 25 號後）', tag: '日本旅遊', tagColor: 'c', src: 'Twitter', age: '34d ago', srcLabel: '𝕏' },
]

const selectedItems = reactive(new Set<number>([1, 2, 4, 5, 7]))

const toggleItem = (id: number) => {
  if (selectedItems.has(id)) {
    selectedItems.delete(id)
  } else {
    selectedItems.add(id)
  }
}

const toggleAllItems = () => {
  if (selectedItems.size === contentItems.length) {
    selectedItems.clear()
  } else {
    contentItems.forEach(i => selectedItems.add(i.id))
  }
}

const visOptions = [
  { value: 'private', icon: '🔒', label: '私人',    desc: '只有你自己看得到，連結分享也無效。' },
  { value: 'link',    icon: '🔗', label: '連結分享', desc: '知道連結的人可以查看與 Fork，但不會被搜尋到。' },
  { value: 'public',  icon: '🌐', label: '公開',    desc: '任何人都能搜尋與 Fork。會出現在 Browse、Google 結果中。' },
]

const publish = () => {
  showToast.value = true
  currentStep.value = 3
}

const copyLink = () => {
  navigator.clipboard?.writeText('https://vela.app/c/chenli/kyoto-osaka-14d')
}
</script>

<style>
.share-shell { max-width: 980px; margin: 0 auto; padding: 28px 32px 80px; }

.stepper {
  display: grid; grid-template-columns: 1fr 1fr 1fr;
  align-items: center; margin: 14px 0 36px; position: relative;
}
.step { display: flex; flex-direction: column; align-items: center; gap: 10px; position: relative; }
.step__circle {
  width: 32px; height: 32px; border-radius: 50%;
  background: var(--surface3); border: 1.5px solid var(--border2);
  display: inline-flex; align-items: center; justify-content: center;
  font-family: var(--font-mono); font-size: 12.5px; font-weight: 500;
  color: var(--text-mid); position: relative; z-index: 2;
}
.step--done .step__circle { background: var(--accent); color: var(--accent-fg); border-color: var(--accent); }
.step--current .step__circle { border-color: var(--accent); color: var(--accent); background: var(--bg); box-shadow: 0 0 0 4px var(--accent-dim); }
.step__label { font-family: var(--font-mono); font-size: 11.5px; color: var(--text-mid); letter-spacing: 0.03em; }
.step--current .step__label { color: var(--text); }
.stepper::before {
  content: ''; position: absolute;
  left: 16.67%; right: 16.67%; top: 16px;
  height: 1.5px; background: var(--border2); z-index: 1;
}
.stepper[data-step="1"]::after { display: none; }
.stepper[data-step="2"]::after {
  content: ''; position: absolute;
  left: 16.67%; top: 16px; width: 33.33%;
  height: 1.5px; background: var(--accent); z-index: 1;
}
.stepper[data-step="3"]::after {
  content: ''; position: absolute;
  left: 16.67%; top: 16px; width: 66.66%;
  height: 1.5px; background: var(--accent); z-index: 1;
}

.step-section {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 16px; padding: 28px 32px 24px; margin-bottom: 18px;
}
.step-section.is-disabled { opacity: 0.45; pointer-events: none; }
.step-section h2 { font-family: var(--font-brand); font-weight: 600; font-size: 21px; letter-spacing: -0.01em; margin: 0 0 6px; }
.step-section .desc { color: var(--text-mid); font-size: 13.5px; margin: 0 0 22px; }
.step-section__num { display: inline-block; font-family: var(--font-mono); font-size: 11px; color: var(--accent); margin-bottom: 6px; letter-spacing: 0.08em; }

.tag-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.tag-pick {
  display: flex; align-items: center; gap: 10px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; padding: 14px 16px; cursor: pointer;
  transition: all .15s ease; position: relative;
}
.tag-pick:hover { border-color: var(--border2); transform: translateY(-2px); }
.tag-pick.sel { background: var(--accent-dim); border-color: var(--accent-bdr); }
.tag-pick .dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.tag-pick .name { font-size: 13.5px; font-weight: 500; }
.tag-pick .count { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); margin-left: auto; }
.tag-pick .thumbs { display: flex; gap: 2px; margin-left: 8px; flex-shrink: 0; }
.tag-pick .thumbs .t { width: 22px; height: 16px; border-radius: 3px; overflow: hidden; border: 1px solid var(--border); }
.tag-pick .check {
  position: absolute; right: 12px; top: 12px;
  width: 18px; height: 18px; border-radius: 50%;
  background: var(--accent); color: var(--accent-fg);
  display: inline-flex; align-items: center; justify-content: center;
}
.step-foot {
  display: flex; align-items: center;
  margin-top: 22px; padding-top: 18px; border-top: 1px solid var(--border); gap: 10px;
}
.step-foot .spacer { flex: 1; }
.step-foot .mono { font-family: var(--font-mono); font-size: 12px; }

.clist { display: flex; flex-direction: column; gap: 6px; }
.citem {
  display: grid; grid-template-columns: 22px 70px 1fr auto;
  gap: 12px; align-items: center;
  padding: 10px 12px; background: var(--surface);
  border: 1px solid var(--border); border-radius: 10px;
  cursor: pointer; transition: all .15s ease;
}
.citem:hover { background: var(--surface2); }
.citem.unsel { opacity: 0.45; }
.citem .checkbox {
  width: 18px; height: 18px; border-radius: 5px;
  border: 1.5px solid var(--border2); background: var(--surface);
  display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.citem:not(.unsel) .checkbox { background: var(--accent); border-color: var(--accent); color: var(--accent-fg); }
.citem .checkbox svg { width: 12px; height: 12px; }
.citem__thumb { width: 70px; height: 44px; border-radius: 5px; overflow: hidden; }
.citem__main { min-width: 0; }
.citem__title { font-size: 13px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin: 0 0 3px; }
.citem__meta { display: flex; gap: 8px; align-items: center; font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); }
.citem__src { font-family: var(--font-mono); font-size: 10px; color: var(--text-dim); }

.select-all {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 12px; margin-bottom: 10px; border-radius: 8px;
  font-family: var(--font-mono); font-size: 12px; color: var(--text-mid);
}
.select-all .pill {
  cursor: pointer; padding: 5px 12px;
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 6px; transition: all .15s ease;
}
.select-all .pill:hover { color: var(--text); }

.vis-row { display: grid; grid-template-columns: 1fr 360px; gap: 24px; align-items: flex-start; }
.vis-options { display: flex; flex-direction: column; gap: 10px; margin-bottom: 22px; }
.vis-opt {
  position: relative; background: var(--surface2);
  border: 1px solid var(--border); border-radius: 12px;
  padding: 14px 18px 14px 22px; cursor: pointer; transition: all .15s ease;
}
.vis-opt:hover { background: var(--surface3); }
.vis-opt.sel { background: var(--accent-dim); border-color: var(--accent-bdr); }
.vis-opt.sel::before {
  content: ''; position: absolute; left: 0; top: 12px; bottom: 12px;
  width: 3px; background: var(--accent); border-radius: 2px;
}
.vis-opt__head { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
.vis-opt__title { font-size: 14px; font-weight: 500; }
.vis-opt__desc { color: var(--text-mid); font-size: 12.5px; line-height: 1.55; margin: 0; }
.vis-opt .radio {
  margin-left: auto; width: 16px; height: 16px;
  border-radius: 50%; border: 1.5px solid var(--border2); flex-shrink: 0; position: relative;
}
.vis-opt.sel .radio { border-color: var(--accent); }
.vis-opt.sel .radio::after { content: ''; position: absolute; inset: 3px; background: var(--accent); border-radius: 50%; }
.link-box {
  display: flex; align-items: center; gap: 8px; margin-top: 12px;
  padding: 8px 10px; background: var(--bg); border: 1px solid var(--border);
  border-radius: 8px; font-family: var(--font-mono); font-size: 11.5px; color: var(--text-mid);
}
.link-box code { color: var(--accent); }

.form-row { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
.form-row label { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.06em; }
.input {
  background: var(--surface2); border: 1px solid var(--border2);
  border-radius: 10px; padding: 11px 14px; font-size: 13.5px; color: var(--text);
  outline: none; transition: all .15s ease; font-family: var(--font-ui); width: 100%; box-sizing: border-box;
}
.input:focus { border-color: var(--accent-bdr); box-shadow: 0 0 0 3px var(--accent-dim); }
textarea.input { resize: vertical; min-height: 80px; line-height: 1.55; }

.preview-card { background: var(--surface2); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; }
.preview-card__head {
  padding: 8px 12px; border-bottom: 1px solid var(--border);
  font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); letter-spacing: 0.06em;
  display: flex; align-items: center; gap: 6px;
}
.preview-card__head::before { content: ''; width: 8px; height: 8px; border-radius: 50%; background: var(--accent); }
.preview-card__cover { height: 120px; display: grid; grid-template-columns: 2fr 1fr; grid-template-rows: 1fr 1fr; gap: 2px; }
.preview-card__cover .t { overflow: hidden; }
.preview-card__cover .t:first-child { grid-row: 1 / span 2; }
.preview-card__body { padding: 12px 14px 16px; }
.preview-card__title { font-family: var(--font-brand); font-weight: 600; font-size: 14.5px; margin: 0 0 5px; }
.preview-card__desc { font-size: 11.5px; color: var(--text-mid); margin: 0 0 10px; line-height: 1.5; }
.preview-card__user { display: flex; align-items: center; gap: 6px; font-family: var(--font-mono); font-size: 10.5px; color: var(--text-mid); }
.preview-card__avatar {
  width: 18px; height: 18px; border-radius: 50%;
  background: linear-gradient(135deg, var(--tag-d), var(--tag-b));
  color: #fff; display: inline-flex; align-items: center; justify-content: center; font-size: 8px;
}

.toast {
  position: fixed; right: 24px; bottom: 24px; z-index: 50;
  width: 340px; background: var(--surface); border: 1px solid var(--accent-bdr);
  border-radius: 14px; padding: 14px 16px;
  box-shadow: 0 20px 48px -16px var(--shadow);
  animation: slideIn .35s cubic-bezier(.34,1.4,.64,1) both;
}
@keyframes slideIn { from { transform: translateX(20px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
.toast__head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.toast__head .ico {
  width: 22px; height: 22px; border-radius: 50%;
  background: var(--accent); color: var(--accent-fg);
  display: inline-flex; align-items: center; justify-content: center;
}
.toast__title { font-size: 13px; font-weight: 500; }
.toast__link {
  display: flex; gap: 6px; align-items: center;
  padding: 6px 10px; background: var(--surface2);
  border-radius: 6px; font-family: var(--font-mono); font-size: 11px; color: var(--text-mid); margin-bottom: 8px;
}
.toast__link code { color: var(--accent); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.toast__actions { display: flex; gap: 6px; }
.toast__actions .btn { height: 30px; padding: 0 12px; font-size: 12px; flex: 1; justify-content: center; }

@media (max-width: 880px) {
  .tag-grid { grid-template-columns: 1fr 1fr; }
  .vis-row { grid-template-columns: 1fr; }
  .step-section { padding: 22px 18px 18px; }
}
@media (max-width: 580px) {
  .share-shell { padding: 20px 16px 60px; }
  .tag-grid { grid-template-columns: 1fr; }
  .stepper { gap: 8px; }
  .step__label { display: none; }
  .toast { left: 16px; right: 16px; bottom: 16px; width: auto; }
}
</style>
