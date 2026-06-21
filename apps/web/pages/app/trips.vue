<template>
  <div class="trips-app">
    <!-- ===== Sidebar ===== -->
    <aside class="trips-side" :class="{ 'trips-side--hidden-mobile': mobileView === 'detail' }">
      <div class="trips-side__head">
        <span class="trips-side__lbl">{{ t('trips.title') }}</span>
        <span class="trips-side__count">{{ trips.length }}</span>
        <button class="trips-side__newbtn" :title="t('trips.createNewBtn')" :disabled="creating" @click="handleCreate">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
        </button>
      </div>
      <div class="trips-rlist">
        <div v-if="loadingList" class="trips-rlist__loading">{{ t('trips.loading') }}</div>
        <div v-else-if="trips.length === 0" class="trips-rlist__empty">{{ t('trips.empty') }}</div>
        <button
          v-for="trip in trips"
          :key="trip.id"
          class="trips-ritem"
          :class="{ 'is-active': selectedId === trip.id }"
          @click="select(trip.id)"
        >
          <h3 class="trips-ritem__title">{{ trip.title }}</h3>
          <p v-if="trip.summary" class="trips-ritem__desc">{{ trip.summary }}</p>
          <div class="trips-ritem__meta">
            <span v-if="trip.start_date" class="trips-ritem__date">{{ formatDateRange(trip.start_date, trip.end_date) }}</span>
            <span class="trips-ritem__count">{{ t('trips.itemCount', { n: trip.item_count }) }}</span>
            <span v-if="trip.my_role !== 'owner'" :class="`trips-ritem__role trips-ritem__role--${trip.my_role}`">{{ t(`trips.role.${trip.my_role}`) }}</span>
          </div>
        </button>
      </div>
    </aside>

    <!-- ===== Main ===== -->
    <main class="trips-main" :class="{ 'trips-main--hidden-mobile': mobileView === 'list' }">
      <div v-if="!selectedId" class="trips-empty">
        <p>{{ t('trips.selectHint') }}</p>
      </div>

      <template v-else-if="current">
        <div class="trips-scroll">
          <div class="trips-doc">

            <!-- Title row -->
            <div class="trips-doc__top">
              <button class="trips-back-btn" @click="mobileView = 'list'">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="18" height="18"><path d="M15 18l-6-6 6-6"/></svg>
              </button>
              <div class="trips-doc__titlewrap">
                <h1
                  class="trips-doc__title"
                  contenteditable="true"
                  spellcheck="false"
                  ref="titleEl"
                  @blur="onTitleBlur"
                  @keydown.enter.prevent="($event.target as HTMLElement).blur()"
                >{{ current.title }}</h1>
                <div class="trips-doc__sub">
                  {{ t('trips.itemCount', { n: current.items.length }) }}
                  <template v-if="current.start_date"> · {{ formatDateRange(current.start_date, current.end_date) }}</template>
                  <template v-if="current.sources.length">
                    · <button class="trips-doc__srcbtn" @click="sourcesOpen = true">{{ t('trips.sourceCount', { n: current.sources.length }) }}</button>
                  </template>
                  <span :class="`trips-doc__rolebadge trips-doc__rolebadge--${current.my_role}`">{{ t(`trips.role.${current.my_role}`) }}</span>
                </div>
              </div>
              <div class="trips-doc__actions">
                <button v-if="isEditor" class="btn" @click="handleAddItem">{{ t('trips.addCardBtn') }}</button>
                <button class="btn" @click="shareOpen = true">{{ t('trips.shareBtn') }}</button>
                <button v-if="current.my_role === 'owner'" class="btn btn--danger" @click="handleDelete">{{ t('trips.deleteBtn') }}</button>
              </div>
            </div>

            <!-- View switcher -->
            <div class="trips-views">
              <button
                v-for="v in VIEWS"
                :key="v.key"
                class="trips-vtab"
                :class="{ 'is-active': activeView === v.key }"
                @click="activeView = v.key"
              >
                {{ t(`trips.viewLabel.${v.key}`) }}
              </button>
            </div>

            <!-- Board view (by tags) -->
            <div v-show="activeView === 'board'" class="trips-board">
              <div
                v-for="col in boardColumns"
                :key="col.id"
                class="trips-bcol"
                :class="{
                  'is-dragover': dragOverTagId === col.id && dragTagId !== col.id && col.id !== '__none__',
                  'is-dragging': dragTagId === col.id,
                }"
                @dragover.prevent="col.id !== '__none__' && (dragOverTagId = col.id)"
                @dragleave="dragOverTagId === col.id && (dragOverTagId = null)"
                @drop.prevent="col.id !== '__none__' && onTagDrop(col.id)"
              >
                <div
                  class="trips-bcol__head"
                  :class="{ 'trips-bcol__head--drag': col.id !== '__none__' && editingTagId !== col.id }"
                  :draggable="col.id !== '__none__' && editingTagId !== col.id"
                  @dragstart="onTagDragStart(col.id, $event)"
                  @dragend="onTagDragEnd"
                >
                  <!-- Editable tag name (only for real tags, not "無標籤") -->
                  <template v-if="col.id !== '__none__'">
                    <input
                      v-if="editingTagId === col.id"
                      :ref="el => { if (el) tagEditInput = el as HTMLInputElement }"
                      v-model="editingTagName"
                      class="trips-bcol__taginput"
                      @blur="finishEditTag(col.id)"
                      @keydown.enter.prevent="($event.target as HTMLElement).blur()"
                      @keydown.escape="cancelEditTag($event)"
                    />
                    <span
                      v-else
                      class="tag-chip"
                      :class="col.color ? `tag-chip--${col.color}` : 'tag-chip--plain'"
                      :title="t('trips.renameTagTooltip')"
                      @click="startEditTag(col.id, col.name)"
                    >{{ col.name }}</span>
                  </template>
                  <span v-else class="tag-chip tag-chip--plain">{{ t('trips.noTags') }}</span>
                  <span class="trips-colcount">{{ itemsByTag(col.id).length }}</span>
                  <button
                    v-if="col.id !== '__none__' && editingTagId !== col.id"
                    class="trips-bcol__del"
                    :title="t('trips.deleteTagTooltip')"
                    @click.stop="handleDeleteTag(col.id, col.name)"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
                  </button>
                </div>
                <div class="trips-bcol__cards">
                  <div
                    v-for="item in itemsByTag(col.id)"
                    :key="item.id"
                    class="trips-tcard"
                    :class="{ 'is-aiflash': flashIds.has(item.id) }"
                    @click="openItemEditor(item)"
                  >
                    <div class="trips-tcard__name">
                      <span v-if="item.emoji" class="trips-tcard__emoji">{{ item.emoji }}</span>
                      {{ item.title }}
                    </div>
                    <div class="trips-tcard__meta">
                      <span v-if="item.booked" class="trips-booked">{{ t('trips.bookedLabel') }}</span>
                      <span v-if="item.start_date" class="trips-tcard__time">{{ formatDateRange(item.start_date, item.end_date) }}</span>
                      <span v-if="item.start_time" class="trips-tcard__time">{{ item.start_time }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <!-- Add tag column -->
              <div class="trips-bcol trips-bcol--addtag">
                <div v-if="addingBoardTag" class="trips-bcol__head">
                  <input
                    ref="boardTagInputEl"
                    v-model="boardTagName"
                    class="trips-bcol__taginput"
                    :placeholder="t('trips.tagNamePlaceholder')"
                    @blur="confirmBoardTag"
                    @keydown.enter.prevent="($event.target as HTMLElement).blur()"
                    @keydown.escape="cancelBoardTag($event)"
                  />
                </div>
                <button v-else class="trips-addcol-btn" @click="startAddBoardTag">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
                  {{ t('trips.addTagBtn') }}
                </button>
              </div>
            </div>

            <!-- Date view -->
            <div v-show="activeView === 'date'" class="trips-dboard">
              <div class="trips-dcol">
                <div class="trips-dcol__head">
                  <div class="trips-dcol__month">{{ t('trips.unscheduledSection') }}</div>
                  <div class="trips-dcol__d" style="font-size:14px">{{ t('trips.noDateLabel') }}</div>
                </div>
                <div class="trips-dcol__cards">
                  <div
                    v-for="item in unscheduledItems"
                    :key="item.id"
                    class="trips-tcard"
                    :class="{ 'is-aiflash': flashIds.has(item.id) }"
                    @click="openItemEditor(item)"
                  >
                    <div class="trips-tcard__name">
                      <span v-if="item.emoji" class="trips-tcard__emoji">{{ item.emoji }}</span>
                      {{ item.title }}
                    </div>
                    <div class="trips-tcard__meta">
                      <span v-for="tag in item.tags" :key="tag.trip_tag_id" class="tag-chip tag-chip--plain" style="font-size:10px">{{ tag.name }}</span>
                      <span v-if="item.booked" class="trips-booked">{{ t('trips.bookedLabel') }}</span>
                    </div>
                  </div>
                  <div v-if="unscheduledItems.length === 0" class="trips-empty-note">{{  '—' }}</div>
                </div>
              </div>
              <div v-for="day in tripDays" :key="day" class="trips-dcol">
                <div class="trips-dcol__head">
                  <div class="trips-dcol__month">{{ formatMonth(day) }}</div>
                  <div class="trips-dcol__date">
                    <span class="trips-dcol__d">{{ formatDay(day) }}</span>
                    <span class="trips-dcol__dow">{{ formatDow(day) }}</span>
                  </div>
                </div>
                <div class="trips-dcol__cards">
                  <div
                    v-for="item in itemsByDate(day)"
                    :key="item.id"
                    class="trips-tcard"
                    :class="{ 'is-aiflash': flashIds.has(item.id) }"
                    @click="openItemEditor(item)"
                  >
                    <div class="trips-tcard__name">
                      <span v-if="item.emoji" class="trips-tcard__emoji">{{ item.emoji }}</span>
                      {{ item.title }}
                    </div>
                    <div class="trips-tcard__meta">
                      <span v-if="item.booked" class="trips-booked">{{ t('trips.bookedLabel') }}</span>
                      <span v-if="item.start_time" class="trips-tcard__time">{{ item.start_time }}</span>
                    </div>
                  </div>
                  <div v-if="itemsByDate(day).length === 0" class="trips-empty-note">{{ t('trips.freeActivityLabel') }}</div>
                </div>
              </div>
            </div>

          </div>
        </div>
      </template>

      <div v-else-if="loadingDetail" class="trips-empty">{{ t('trips.loading') }}</div>
    </main>

    <!-- ===== Item editor Modal ===== -->
    <Transition name="modal">
      <div v-if="editingItem !== null" class="trips-modal-overlay" @click.self="closeItemEditor">
        <div
          ref="panelRef"
          class="trips-modal"
          @touchstart.passive="(e: TouchEvent) => { _touchStartY = e.touches[0].clientY }"
          @touchmove.passive="onPanelTouchMove"
          @touchend.passive="onPanelTouchEnd"
        >
          <div class="trips-modal__head">
            <!-- Emoji: viewer = static span; editor = clickable button -->
            <button
              v-if="isEditor"
              ref="emojiTriggerEl"
              class="trips-emoji-trigger"
              type="button"
              :title="editForm.emoji ? t('trips.changeEmojiTooltip') : t('trips.selectEmojiTooltip')"
              @click="toggleEmojiPicker"
            >{{ editForm.emoji || '😊' }}</button>
            <span v-else class="trips-emoji-trigger trips-emoji-trigger--ro">{{ editForm.emoji || '😊' }}</span>

            <input
              v-model="editForm.title"
              class="trips-modal__title"
              :class="{ 'trips-modal__title--ro': !isEditor }"
              :placeholder="t('trips.itemNamePlaceholder')"
              :readonly="!isEditor"
              @blur="isEditor ? onTitleCommit() : undefined"
              @keydown.enter.prevent="isEditor && ($event.target as HTMLElement).blur()"
            />
            <button v-if="editingItem?.id && isEditor" class="trips-modal__trash" :disabled="isSaving" @click="handleDeleteItem">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="18" height="18"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
            </button>
          </div>
          <div class="trips-modal__body">
            <!-- 已關聯 -->
            <div v-if="editingItem?.sources?.length" class="trips-linked-row">
              <button
                type="button"
                class="trips-ksrcbtn"
                @click="itemSourcesOpen = true"
              >{{ t('trips.sourcesLinked', { n: editingItem.sources.length }) }}</button>
            </div>

            <!-- 已預定票券 + 票券連結 -->
            <div class="trips-field">
              <span class="trips-field__lbl">{{ t('trips.fieldLabel.ticket') }}</span>

              <!-- viewer: read-only display -->
              <div v-if="!isEditor" class="trips-booked-row">
                <span v-if="editForm.booked" class="trips-booked">{{ t('trips.bookedLabel') }}</span>
                <a v-if="isUrl(editForm.ticket_url)" :href="editForm.ticket_url" target="_blank" rel="noopener" class="btn trips-place-open">{{ t('trips.openTicketBtn') }}</a>
                <span v-if="!editForm.booked && !isUrl(editForm.ticket_url)" class="trips-ro-empty">—</span>
              </div>

              <!-- editor: editable -->
              <div v-else class="trips-booked-row">
                <label class="trips-check">
                  <input type="checkbox" v-model="editForm.booked" @change="saveField('booked')" />
                  <span class="trips-field__lbl">{{ t('trips.fieldLabel.bookedTicket') }}</span>
                </label>
                <div class="trips-ticket">
                  <div v-if="isUrl(editForm.ticket_url) && !editingTicket" class="trips-place-row">
                    <a :href="editForm.ticket_url" target="_blank" rel="noopener" class="btn trips-place-open">{{ t('trips.openTicketBtn') }}</a>
                    <button type="button" class="btn trips-place-edit" @click="editingTicket = true">{{ t('trips.editBtn') }}</button>
                  </div>
                  <input
                    v-else
                    v-model="editForm.ticket_url"
                    type="url"
                    class="trips-field__input"
                    :placeholder="t('trips.ticketUrlPlaceholder')"
                    @keydown.enter.prevent="commitTicket"
                    @blur="commitTicket"
                  />
                </div>
              </div>
            </div>

            <!-- Date + Time combined -->
            <div class="trips-field">
              <span class="trips-field__lbl">{{ t('trips.fieldLabel.time') }}</span>
              <div class="trips-field__timerow">
                <input v-model="editForm.start_date" type="date" class="trips-field__input trips-field__dt" :disabled="!isEditor" @change="saveField('start_date')" />
                <input v-model="editForm.start_time" type="time" class="trips-field__input trips-field__tm" :disabled="!isEditor" @change="saveField('start_time')" />
                <span class="trips-field__sep">{{ t('trips.arrow') }}</span>
                <input v-model="editForm.end_date" type="date" class="trips-field__input trips-field__dt" :disabled="!isEditor" @change="saveField('end_date')" />
                <input v-model="editForm.end_time" type="time" class="trips-field__input trips-field__tm" :disabled="!isEditor" @change="saveField('end_time')" />
              </div>
            </div>

            <!-- Place URL -->
            <div class="trips-field">
              <span class="trips-field__lbl">{{ t('trips.fieldLabel.location') }}</span>

              <!-- viewer: open link only (no edit/input) -->
              <template v-if="!isEditor">
                <a v-if="isUrl(editForm.place_name)" :href="editForm.place_name" target="_blank" rel="noopener" class="btn trips-place-open">{{ t('trips.openMapBtn') }}</a>
                <span v-else class="trips-ro-empty">—</span>
              </template>

              <!-- editor: current behavior -->
              <template v-else>
                <div v-if="isUrl(editForm.place_name) && !editingPlace" class="trips-place-row">
                  <a :href="editForm.place_name" target="_blank" rel="noopener" class="btn trips-place-open">{{ t('trips.openMapBtn') }}</a>
                  <button type="button" class="btn trips-place-edit" @click="editingPlace = true">{{ t('trips.editBtn') }}</button>
                </div>
                <input
                  v-else
                  v-model="editForm.place_name"
                  type="url"
                  class="trips-field__input"
                  :placeholder="t('trips.placeUrlPlaceholder')"
                  @keydown.enter.prevent="commitPlace"
                  @blur="commitPlace"
                />
              </template>
            </div>

            <!-- Tags -->
            <div class="trips-field">
              <span class="trips-field__lbl">{{ t('trips.fieldLabel.tags') }}</span>
              <div class="trips-tags-wrap">

                <!-- viewer: show item's current tags as static chips -->
                <template v-if="!isEditor">
                  <span v-if="!editingItem?.tags?.length" class="trips-ro-empty">—</span>
                  <span
                    v-for="tag in editingItem?.tags ?? []"
                    :key="tag.trip_tag_id"
                    class="trips-pill is-active trips-pill--ro"
                  >{{ tag.name }}</span>
                </template>

                <!-- editor: interactive tag picker -->
                <template v-else>
                  <button
                    v-for="tag in availableTags"
                    :key="tag.id"
                    class="trips-pill"
                    :class="{ 'is-active': editForm.tag_ids.includes(tag.id) }"
                    @click="toggleTag(tag.id)"
                  >{{ tag.name }}</button>
                  <div v-if="addingTag" class="trips-newtag">
                    <input
                      ref="newTagInputEl"
                      v-model="newTagName"
                      class="trips-newtag__input"
                      :placeholder="t('trips.tagNamePlaceholder')"
                      @keydown.enter="confirmNewTag"
                      @keydown.escape="cancelNewTag"
                      @blur="cancelNewTag"
                    />
                  </div>
                  <button v-else class="trips-pill" @click="startAddTag">{{ t('trips.addNewTagBtn') }}</button>
                </template>
              </div>
            </div>

            <!-- Note (Tiptap) -->
            <div class="trips-field trips-field--note">
              <span class="trips-field__lbl">{{ t('trips.fieldLabel.notes') }}</span>
              <div class="trips-tiptap-wrap" :class="{ 'trips-tiptap-wrap--ro': !isEditor }">
                <TiptapEditor v-model="editForm.note" :readonly="!isEditor" />
              </div>
            </div>

          </div>

        </div>
      </div>
    </Transition>

    <!-- ===== AI 修改懸浮球（僅在選定行程且有編輯權限時顯示）===== -->
    <TripAiFab
      v-if="current && isEditor"
      :trip-id="current.id"
      @card-added="onAiCardAdded"
      @card-updated="onAiCardUpdated"
      @card-deleted="onAiCardDeleted"
      @done="onAiDone"
    />

    <!-- ===== Share modal ===== -->
    <TripShareModal
      v-if="current"
      :open="shareOpen"
      :trip="current"
      @close="shareOpen = false"
      @updated="refreshCurrentTrip"
    />

    <!-- Emoji picker (Teleport to body to escape overflow) -->
    <Teleport to="body">
      <div v-if="showEmojiPicker" class="tep" :style="emojiPickerStyle">
        <div class="tep__grid">
          <button
            v-for="e in filteredEmojis"
            :key="e"
            class="tep__btn"
            @click="pickEmoji(e)"
          >{{ e }}</button>
          <div v-if="filteredEmojis.length === 0" class="tep__empty">{{ t('trips.noEmojiResult') }}</div>
        </div>
        <input
          v-model="emojiSearch"
          class="tep__search"
          :placeholder="t('trips.emojiSearchPlaceholder')"
          @keydown.escape="showEmojiPicker = false"
        />
      </div>
    </Teleport>

    <!-- Source list modal（行程層級來源）-->
    <SourceListModal
      :open="sourcesOpen"
      :sources="current?.sources ?? []"
      :title="t('trips.sourceCount', { n: current?.sources.length ?? 0 })"
      @close="sourcesOpen = false"
      @select="onSelectSource"
    />

    <!-- Source list modal（卡片關聯的收藏）-->
    <SourceListModal
      :open="itemSourcesOpen"
      :sources="editingItem?.sources ?? []"
      :title="t('trips.sourcesLinked', { n: editingItem?.sources?.length ?? 0 })"
      @close="itemSourcesOpen = false"
      @select="onSelectItemSource"
    />
  </div>
</template>

<script setup lang="ts">
import type { Trip, TripItem, TripListItem, TripTag } from '~/types/api'

definePageMeta({ ssr: false })
useHead({ title: 'Garner — 旅遊行程' })
const { t, locale } = useI18n()

const { listTrips, getTrip, createTrip, updateTrip, deleteTrip, addItem, updateItem, deleteItem, listTags, createTag, updateTag, deleteTag, joinByToken } = useTrips()
const { open: openItemModal } = useItemModal()
const router = useRouter()

// ── Constants ──────────────────────────────────────────────────────────────
const VIEWS = [
  { key: 'board' as const, n: '1' },
  { key: 'date' as const, n: '2' },
]

const EMOJI_MAP: Array<{ e: string; k: string }> = [
  // 景點
  { e: '🏯', k: '城堡古蹟景點' }, { e: '🗼', k: '塔景點東京' }, { e: '⛩️', k: '鳥居神社景點' },
  { e: '🎡', k: '摩天輪遊樂場景點' }, { e: '🎢', k: '雲霄飛車遊樂場' }, { e: '🏛️', k: '博物館景點' },
  { e: '🗽', k: '自由女神像景點紐約' }, { e: '🏟️', k: '體育場競技場' }, { e: '🌊', k: '海浪海洋' },
  { e: '🏔️', k: '山景點高山' }, { e: '🗻', k: '富士山景點' }, { e: '🌋', k: '火山景點' },
  { e: '🏝️', k: '小島景點' }, { e: '🏖️', k: '海灘沙灘景點' }, { e: '🌅', k: '日出日落景點' },
  { e: '🌉', k: '夜晚橋景點' }, { e: '🌄', k: '山日出景點' }, { e: '🌃', k: '夜景城市景點' },
  // 美食
  { e: '🍜', k: '拉麵麵食美食' }, { e: '🍣', k: '壽司生魚片日本美食' }, { e: '🍱', k: '便當美食' },
  { e: '🍛', k: '咖哩美食' }, { e: '🍲', k: '火鍋鍋物美食' }, { e: '🍤', k: '炸蝦天婦羅美食' },
  { e: '🥘', k: '燉菜美食鍋物' }, { e: '🍷', k: '紅酒葡萄酒' }, { e: '🍻', k: '啤酒' },
  { e: '☕', k: '咖啡飲料' }, { e: '🍰', k: '蛋糕甜點' }, { e: '🍕', k: '披薩美食' },
  { e: '🍔', k: '漢堡美食' }, { e: '🥗', k: '沙拉' }, { e: '🧇', k: '鬆餅早餐' }, { e: '🍦', k: '冰淇淋甜點' },
  // 交通
  { e: '✈️', k: '飛機航班交通' }, { e: '🚂', k: '火車交通' }, { e: '🚌', k: '公車交通' },
  { e: '🚕', k: '計程車Uber交通' }, { e: '🚗', k: '租車自駕交通' }, { e: '🛵', k: '機車摩托車交通' },
  { e: '🚲', k: '腳踏車單車交通' }, { e: '🚢', k: '郵輪船交通' }, { e: '🚁', k: '直升機交通' },
  { e: '⛵', k: '帆船交通' }, { e: '🚐', k: '小巴交通' }, { e: '🛺', k: '嘟嘟車交通' },
  { e: '🏎️', k: '賽車' }, { e: '🛳️', k: '大船郵輪交通' },
  // 住宿
  { e: '🏨', k: '飯店旅館住宿' }, { e: '🏠', k: '民宿家住宿' }, { e: '🛖', k: '小屋住宿' },
  { e: '⛺', k: '露營帳篷住宿' }, { e: '🏕️', k: '露營住宿' }, { e: '🛏️', k: '床睡覺住宿' },
  // 其他
  { e: '📷', k: '相機拍照' }, { e: '🎫', k: '票券門票' }, { e: '🎟️', k: '票券' },
  { e: '🛍️', k: '購物' }, { e: '🎒', k: '背包' }, { e: '🧳', k: '行李箱行李' },
  { e: '🗺️', k: '地圖' }, { e: '🧭', k: '指南針' }, { e: '📍', k: '地標位置' },
  { e: '📌', k: '圖釘標記' }, { e: '❤️', k: '愛心最愛' }, { e: '⭐', k: '星星推薦' },
  { e: '🌸', k: '櫻花花' }, { e: '🎉', k: '慶祝' }, { e: '💡', k: '提示注意' }, { e: '🔑', k: '鑰匙' },
]

// ── State ──────────────────────────────────────────────────────────────────
const trips = ref<TripListItem[]>([])
const loadingList = ref(true)
const selectedId = ref<string | null>(null)
const current = ref<Trip | null>(null)
const loadingDetail = ref(false)
const creating = ref(false)
const activeView = ref<'board' | 'date'>('board')
const titleEl = ref<HTMLElement | null>(null)
const availableTags = ref<TripTag[]>([])
const sourcesOpen = ref(false)
const shareOpen = ref(false)
const mobileView = ref<'list' | 'detail'>('list')

const isEditor = computed(() => current.value?.my_role === 'owner' || current.value?.my_role === 'editor')

async function refreshCurrentTrip() {
  if (!current.value) return
  try {
    current.value = await getTrip(current.value.id)
    // Also refresh sidebar list so member_count etc. stays in sync
    const idx = trips.value.findIndex(t => t.id === current.value!.id)
    if (idx !== -1) {
      trips.value[idx] = {
        ...trips.value[idx],
        member_count: current.value.members.length + 1,
      }
    }
  } catch { /* ignore */ }
}

function onSelectSource(id: string) {
  sourcesOpen.value = false
  openItemModal(id)
}

// 卡片編輯彈窗內「關聯收藏」清單選取 → 開知識詳情
const itemSourcesOpen = ref(false)
function onSelectItemSource(id: string) {
  itemSourcesOpen.value = false
  openItemModal(id)
}

// ── AI 修改懸浮球：逐動作即時套用到畫面 + 綠色閃爍特效 ──────────────────────────
const flashIds = ref<Set<string>>(new Set())

function flashCard(id: string) {
  flashIds.value = new Set(flashIds.value).add(id)
  setTimeout(() => {
    const next = new Set(flashIds.value)
    next.delete(id)
    flashIds.value = next
  }, 1400)
}

function bumpSidebarCount(delta: number) {
  if (!current.value) return
  const idx = trips.value.findIndex(t => t.id === current.value!.id)
  if (idx !== -1) trips.value[idx].item_count += delta
}

function onAiCardAdded(item: TripItem) {
  if (!current.value) return
  if (current.value.items.some(i => i.id === item.id)) return
  current.value.items.push(item)
  bumpSidebarCount(1)
  flashCard(item.id)
}

function onAiCardUpdated(item: TripItem) {
  if (!current.value) return
  const idx = current.value.items.findIndex(i => i.id === item.id)
  if (idx !== -1) current.value.items[idx] = item
  else current.value.items.push(item)
  flashCard(item.id)
}

function onAiCardDeleted(id: string) {
  if (!current.value) return
  const idx = current.value.items.findIndex(i => i.id === id)
  if (idx !== -1) {
    current.value.items.splice(idx, 1)
    bumpSidebarCount(-1)
  }
}

async function onAiDone() {
  // AI 可能因 category 建立了新標籤，重新抓標籤清單並套回排序
  availableTags.value = await listTags()
  applyStoredTagOrder()
}

// Emoji picker
const emojiTriggerEl = ref<HTMLButtonElement | null>(null)
const showEmojiPicker = ref(false)
const emojiSearch = ref('')
const emojiPickerStyle = ref<Record<string, string>>({})

// Board tag editing
const editingTagId = ref<string | null>(null)
const editingTagName = ref('')
const tagEditInput = ref<HTMLInputElement | null>(null)

// Board add tag column
const addingBoardTag = ref(false)
const boardTagName = ref('')
const boardTagInputEl = ref<HTMLInputElement | null>(null)

// Board column drag-reorder（順序記憶在 localStorage）
const TAG_ORDER_KEY = 'trips:tagOrder'
const dragTagId = ref<string | null>(null)
const dragOverTagId = ref<string | null>(null)

// Modal inline tag add
const addingTag = ref(false)
const newTagName = ref('')
const newTagInputEl = ref<HTMLInputElement | null>(null)

// ── Lifecycle ──────────────────────────────────────────────────────────────
async function loadInitialData() {
  loadingList.value = true
  try {
    // Handle join_token before loading list (join first so new trip appears in list)
    const joinToken = useRoute().query.join_token as string | undefined
    if (joinToken) {
      try {
        await joinByToken(joinToken)
        useToast().show(t('trips.share.joinSuccess'), 'success')
      } catch {
        useToast().show(t('trips.share.joinFailed'), 'error')
      }
      router.replace({ query: { ...useRoute().query, join_token: undefined } })
    }

    [trips.value, availableTags.value] = await Promise.all([listTrips(), listTags()])
    const openId = useRoute().query.open as string | undefined
    if (openId && trips.value.some(t => t.id === openId)) {
      select(openId)
    }
    if (availableTags.value.length === 0) {
      const defaults = [
        { name: '景點', color: 'd' }, { name: '美食', color: 'e' },
        { name: '交通', color: 'b' }, { name: '住宿', color: 'a' },
      ]
      for (const d of defaults) {
        try {
          const tag = await createTag(d)
          availableTags.value.push(tag)
        } catch { /* ignore */ }
      }
    }
    applyStoredTagOrder()
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    if (msg === 'Page is not active') {
      // 頁面在背景，等回到前台時重試
      loadingList.value = false
      return
    }
    throw err
  } finally {
    loadingList.value = false
  }
}

function onVisibilityChange() {
  if (!document.hidden && trips.value.length === 0 && !loadingList.value) {
    loadInitialData()
  }
}

onMounted(() => {
  document.addEventListener('click', handleOutsideClick, true)
  document.addEventListener('visibilitychange', onVisibilityChange)
  loadInitialData()
})

onUnmounted(() => {
  document.removeEventListener('click', handleOutsideClick, true)
  document.removeEventListener('visibilitychange', onVisibilityChange)
})

function handleOutsideClick(e: MouseEvent) {
  if (!showEmojiPicker.value) return
  const target = e.target as HTMLElement
  if (target.closest('.tep') || target.closest('.trips-emoji-trigger')) return
  showEmojiPicker.value = false
}

// ── Trip selection ─────────────────────────────────────────────────────────
async function select(id: string) {
  selectedId.value = id
  mobileView.value = 'detail'
  loadingDetail.value = true
  current.value = null
  try {
    current.value = await getTrip(id)
  } finally {
    loadingDetail.value = false
  }
}

async function handleCreate() {
  if (creating.value) return
  creating.value = true
  const tempId = `temp-${Date.now()}`
  const defaultTripName = t('trips.defaultTripName')
  const tempItem: TripListItem = {
    id: tempId, title: defaultTripName, summary: null,
    start_date: null, end_date: null,
    source_count: 0, item_count: 0, member_count: 0, my_role: 'owner',
    last_edited_by: 'user',
    created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
  }
  trips.value.unshift(tempItem)
  selectedId.value = tempId
  mobileView.value = 'detail'
  try {
    const trip = await createTrip({ title: defaultTripName })
    const idx = trips.value.findIndex(t => t.id === tempId)
    if (idx !== -1) trips.value[idx] = { ...tempItem, id: trip.id }
    selectedId.value = trip.id
    current.value = trip
    nextTick(() => titleEl.value?.focus())
  } catch {
    trips.value = trips.value.filter(t => t.id !== tempId)
    selectedId.value = null
  } finally {
    creating.value = false
  }
}

async function handleDelete() {
  if (!current.value) return
  if (!confirm(t('trips.confirm.deleteTrip', { title: current.value.title }))) return
  const deletedId = current.value.id
  const deletedTrip = current.value
  const idx = trips.value.findIndex(t => t.id === deletedId)
  const removed = idx !== -1 ? trips.value[idx] : null
  if (idx !== -1) trips.value.splice(idx, 1)
  selectedId.value = null
  current.value = null
  mobileView.value = 'list'
  try {
    await deleteTrip(deletedId)
  } catch {
    if (removed && idx !== -1) trips.value.splice(idx, 0, removed)
    selectedId.value = deletedId
    current.value = deletedTrip
  }
}

async function onTitleBlur(e: Event) {
  if (!current.value) return
  const newTitle = (e.target as HTMLElement).innerText.trim()
  if (!newTitle || newTitle === current.value.title) return
  const prevTitle = current.value.title
  current.value.title = newTitle
  const idx = trips.value.findIndex(t => t.id === current.value!.id)
  if (idx !== -1) trips.value[idx].title = newTitle
  try {
    await updateTrip(current.value.id, { title: newTitle })
  } catch {
    current.value.title = prevTitle
    if (idx !== -1) trips.value[idx].title = prevTitle
  }
}

// ── Board (by tags) ────────────────────────────────────────────────────────
const boardColumns = computed(() => {
  // Start from the user's own tags (editable columns)
  const cols: Array<{ id: string; name: string; color: string | null }> = [...availableTags.value]
  // For shared trips, the trip owner's tags won't be in availableTags (filtered by user_id).
  // Supplement from the tags actually used on the trip's cards so the board renders correctly.
  if (current.value) {
    for (const item of current.value.items) {
      for (const tag of item.tags) {
        if (!cols.find(c => c.id === tag.trip_tag_id)) {
          cols.push({ id: tag.trip_tag_id, name: tag.name, color: tag.color })
        }
      }
    }
  }
  return [...cols, { id: '__none__', name: '', color: null as string | null }]
})

function itemsByTag(tagId: string) {
  if (!current.value) return []
  const items = current.value.items
  if (tagId === '__none__') {
    return items.filter(i => i.tags.length === 0).sort((a, b) => a.order_index - b.order_index)
  }
  return items
    .filter(i => i.tags.some(t => t.trip_tag_id === tagId))
    .sort((a, b) => a.order_index - b.order_index)
}

// ── Date / Timeline ────────────────────────────────────────────────────────
const tripDays = computed<string[]>(() => {
  if (!current.value) return []
  const days = new Set<string>()
  for (const item of current.value.items) {
    if (item.start_date) days.add(item.start_date)
    if (item.end_date) days.add(item.end_date)
  }
  return [...days].sort()
})

const unscheduledItems = computed(() =>
  (current.value?.items ?? []).filter(i => !i.start_date && !i.end_date).sort((a, b) => a.order_index - b.order_index)
)

function itemsByDate(day: string) {
  return (current.value?.items ?? [])
    .filter(i => i.start_date === day || (i.start_date && i.end_date && i.start_date <= day && i.end_date >= day))
    .sort((a, b) => {
      if (a.start_time && b.start_time) return a.start_time.localeCompare(b.start_time)
      return a.order_index - b.order_index
    })
}


// ── Formatting ─────────────────────────────────────────────────────────────
function formatDateRange(start: string | null, end: string | null) {
  if (!start) return ''
  const s = new Date(start).toLocaleDateString('zh-TW', { month: 'short', day: 'numeric' })
  if (!end || end === start) return s
  const e = new Date(end).toLocaleDateString('zh-TW', { month: 'short', day: 'numeric' })
  return `${s} – ${e}`
}

function formatMonth(d: string) { return new Date(d).toLocaleDateString(locale.value, { month: 'short' }) }
function formatDay(d: string) { return new Date(d).getDate().toString() }
function formatDow(d: string) {
  const locale_str = locale.value === 'en' ? 'en-US' : 'zh-TW'
  return new Date(d).toLocaleDateString(locale_str, { weekday: 'short' }).slice(0, 1)
}
function isUrl(s: string | null | undefined): boolean {
  if (!s) return false
  try { new URL(s); return true } catch { return false }
}

// ── Emoji picker ───────────────────────────────────────────────────────────
const PICKER_W = 320
const PICKER_H = 310

const filteredEmojis = computed(() => {
  const q = emojiSearch.value.trim()
  if (!q) return EMOJI_MAP.map(e => e.e)
  return EMOJI_MAP.filter(({ k }) => k.includes(q)).map(e => e.e)
})

function toggleEmojiPicker() {
  if (showEmojiPicker.value) {
    showEmojiPicker.value = false
    return
  }
  if (!emojiTriggerEl.value) return
  const rect = emojiTriggerEl.value.getBoundingClientRect()
  let top = rect.bottom + 6
  let left = rect.left

  // Clamp horizontally
  if (left + PICKER_W > window.innerWidth - 8) {
    left = window.innerWidth - PICKER_W - 8
  }
  if (left < 8) left = 8

  // Flip upward if not enough space below
  if (top + PICKER_H > window.innerHeight - 8) {
    top = rect.top - PICKER_H - 6
  }

  emojiPickerStyle.value = { top: `${top}px`, left: `${left}px` }
  emojiSearch.value = ''
  showEmojiPicker.value = true
}

function pickEmoji(e: string) {
  editForm.value.emoji = e
  showEmojiPicker.value = false
  saveField('emoji')
}

// ── Item editor ────────────────────────────────────────────────────────────
interface EditForm {
  title: string
  emoji: string
  booked: boolean
  ticket_url: string
  start_date: string
  end_date: string
  start_time: string
  end_time: string
  place_name: string
  note: string
  tag_ids: string[]
}

const editingItem = ref<Partial<TripItem> | null>(null)
const isSaving = ref(false)
const editingPlace = ref(false)  // 地標：有值時預設顯示「開啟地圖」按鈕，按編輯才切成 input
const editingTicket = ref(false) // 票券連結：同地標的切換行為
const editForm = ref<EditForm>({
  title: '', emoji: '', booked: false, ticket_url: '',
  start_date: '', end_date: '', start_time: '', end_time: '',
  place_name: '', note: '', tag_ids: [],
})

// populateForm 期間抑制自動儲存，避免載入卡片時誤觸 PATCH
const suppressAutoSave = ref(false)

function populateForm(item: Partial<TripItem>) {
  suppressAutoSave.value = true
  editingPlace.value = false   // 有地標就先顯示按鈕
  editingTicket.value = false  // 有票券連結就先顯示按鈕
  editForm.value = {
    title: item.title ?? '',
    emoji: item.emoji ?? '',
    booked: item.booked ?? false,
    ticket_url: item.ticket_url ?? '',
    start_date: item.start_date ?? '',
    end_date: item.end_date ?? '',
    start_time: item.start_time ?? '',
    end_time: item.end_time ?? '',
    place_name: item.place_name ?? '',
    note: item.note ?? '',
    tag_ids: (item.tags ?? []).map(t => t.trip_tag_id),
  }
  nextTick(() => { suppressAutoSave.value = false })
}

function openItemEditor(item: TripItem) {
  editingItem.value = item
  populateForm(item)
}

// 新增：直接建立一張空白卡片再開編輯（無儲存按鈕，後續編輯各自 PATCH）
async function handleAddItem() {
  if (!current.value) return
  const tripId = current.value.id
  try {
    const created = await addItem(tripId, { title: t('trips.defaultItemName'), order_index: current.value.items.length })
    current.value.items.push(created)
    sidebarItemCount(tripId, 1)
    openItemEditor(created)
  } catch {
    useToast().show(t('trips.addFailed'), 'error')
  }
}

const panelRef = ref<HTMLElement | null>(null)
let _touchStartY = 0

function doClose(): Promise<void> {
  flushNoteSave()
  editingItem.value = null
  showEmojiPicker.value = false
  return nextTick()
}

function closeItemEditor() {
  doClose()
}

function onPanelTouchMove(e: TouchEvent) {
  const panel = panelRef.value
  if (!panel) return
  
  const deltaY = e.touches[0].clientY - _touchStartY
  
  // 當面板滾動到頂，且用戶向下拖拽時
  if (panel.scrollTop <= 0 && deltaY > 0) {
    panel.style.transition = 'none' // 拖拽時不需要動畫，才能即時跟手
    panel.style.bottom = `-${deltaY}px`
  } else {
    panel.style.transition = ''
    panel.style.bottom = ''
  }
}

function onPanelTouchEnd(e: TouchEvent) {
  const panel = panelRef.value
  if (!panel) return

  const deltaY = e.changedTouches[0].clientY - _touchStartY

  // 判斷是否觸發關閉（向下拖拽超過 80px 且處於頂部）
  if (panel.scrollTop <= 0 && deltaY > 80) {
    // 【方案 A：動畫關閉】
    // 給 bottom 加上平滑動畫，並將其設為 -100vh 移出螢幕外
    panel.style.transition = 'bottom .2s ease-out'
    panel.style.bottom = '-100vh'
    
    // 等 200ms 動畫結束後，執行真正的關閉邏輯與清理
    setTimeout(() => {
      doClose()
    }, 200)

  } else if (deltaY > 0) {
    // 【方案 B：動畫復位】
    // 有被向下拉但沒超過 80px，平滑彈回原本的 bottom: 0
    panel.style.transition = 'bottom .3s cubic-bezier(0.32, 0.72, 0, 1)'
    panel.style.bottom = '0px'
    
    // 動畫結束後清除 transition 恢復乾淨狀態
    setTimeout(() => {
      if (panel) panel.style.transition = ''
    }, 300)
  }
}

function sidebarItemCount(tripId: string, delta: number) {
  const idx = trips.value.findIndex(t => t.id === tripId)
  if (idx !== -1) trips.value[idx].item_count += delta
}

// ── 自動儲存：每個欄位變更各自發送 PATCH ─────────────────────────────────────
async function patchField(patch: Record<string, unknown>, optimistic: Partial<TripItem>) {
  if (!current.value || !editingItem.value?.id) return
  const tripId = current.value.id
  const itemId = editingItem.value.id
  const idx = current.value.items.findIndex(i => i.id === itemId)
  if (idx === -1) return
  const prev = { ...current.value.items[idx] }
  current.value.items[idx] = { ...current.value.items[idx], ...optimistic }
  if (editingItem.value?.id === itemId) editingItem.value = current.value.items[idx]
  try {
    const updated = await updateItem(tripId, itemId, patch)
    const i2 = current.value.items.findIndex(i => i.id === itemId)
    if (i2 !== -1) current.value.items[i2] = updated
    if (editingItem.value?.id === itemId) editingItem.value = updated
  } catch {
    const i2 = current.value.items.findIndex(i => i.id === itemId)
    if (i2 !== -1) current.value.items[i2] = prev
    if (editingItem.value?.id === itemId) editingItem.value = prev
    useToast().show(t('trips.saveFailed'), 'error')
  }
}

type SaveKey = 'title' | 'emoji' | 'booked' | 'ticket_url' | 'place_name'
  | 'start_date' | 'end_date' | 'start_time' | 'end_time' | 'note'

function saveField(key: SaveKey) {
  if (suppressAutoSave.value) return
  let value: unknown = editForm.value[key]
  if (key === 'title') {
    value = (value as string).trim() || t('trips.defaultItemName')
    editForm.value.title = value as string
  } else if (typeof value === 'string') {
    value = value || null
  }
  patchField({ [key]: value }, { [key]: value } as Partial<TripItem>)
}

function saveTags() {
  if (suppressAutoSave.value) return
  const optimisticTags = availableTags.value
    .filter(t => editForm.value.tag_ids.includes(t.id))
    .map(t => ({ trip_tag_id: t.id, name: t.name, color: t.color }))
  patchField({ tag_ids: [...editForm.value.tag_ids] }, { tags: optimisticTags })
}

function onTitleCommit() { saveField('title') }
function commitPlace() { editingPlace.value = false; saveField('place_name') }
function commitTicket() { editingTicket.value = false; saveField('ticket_url') }

// 備註打字頻繁：去抖動後再送，離開卡片時 flush
let noteTimer: ReturnType<typeof setTimeout> | null = null
function flushNoteSave() {
  if (noteTimer) { clearTimeout(noteTimer); noteTimer = null; saveField('note') }
}
watch(() => editForm.value.note, () => {
  if (suppressAutoSave.value) return
  if (noteTimer) clearTimeout(noteTimer)
  noteTimer = setTimeout(() => { noteTimer = null; saveField('note') }, 700)
})

async function handleDeleteItem() {
  if (!current.value || !editingItem.value?.id || isSaving.value) return
  if (!confirm(t('trips.confirm.deleteCard'))) return
  const tripId = current.value.id
  const itemId = editingItem.value.id
  const itemIdx = current.value.items.findIndex(i => i.id === itemId)
  const removed = itemIdx !== -1 ? current.value.items[itemIdx] : null
  if (itemIdx !== -1) current.value.items.splice(itemIdx, 1)
  sidebarItemCount(tripId, -1)
  closeItemEditor()
  try {
    await deleteItem(tripId, itemId)
  } catch {
    if (removed && itemIdx !== -1) current.value.items.splice(itemIdx, 0, removed)
    sidebarItemCount(tripId, 1)
  }
}

function toggleTag(tagId: string) {
  const ids = editForm.value.tag_ids
  const idx = ids.indexOf(tagId)
  if (idx === -1) ids.push(tagId)
  else ids.splice(idx, 1)
  saveTags()
}

// ── Board tag editing ──────────────────────────────────────────────────────
function startEditTag(tagId: string, name: string) {
  editingTagId.value = tagId
  editingTagName.value = name
  nextTick(() => { tagEditInput.value?.select() })
}

async function finishEditTag(tagId: string) {
  if (editingTagId.value === null) return  // cancelled
  const newName = editingTagName.value.trim()
  editingTagId.value = null
  if (!newName) return
  const tag = availableTags.value.find(t => t.id === tagId)
  if (!tag || newName === tag.name) return
  const prevName = tag.name
  tag.name = newName
  try {
    await updateTag(tagId, { name: newName })
  } catch {
    tag.name = prevName
  }
}

function cancelEditTag(e: KeyboardEvent) {
  editingTagId.value = null
  ;(e.target as HTMLElement).blur()
}

// ── Board delete tag ───────────────────────────────────────────────────────
async function handleDeleteTag(tagId: string, name: string) {
  if (!confirm(t('trips.confirm.deleteTag', { name }))) return
  const idx = availableTags.value.findIndex(t => t.id === tagId)
  if (idx === -1) return
  const removed = availableTags.value[idx]
  availableTags.value.splice(idx, 1)
  // 同步把此標籤從目前行程的卡片上移除（後端 delete 會 cascade）
  const detached: Array<{ item: TripItem; pos: number; tag: TripItem['tags'][number] }> = []
  for (const item of current.value?.items ?? []) {
    const ti = item.tags.findIndex(t => t.trip_tag_id === tagId)
    if (ti !== -1) {
      detached.push({ item, pos: ti, tag: item.tags[ti] })
      item.tags.splice(ti, 1)
    }
  }
  saveTagOrder()
  try {
    await deleteTag(tagId)
  } catch {
    availableTags.value.splice(idx, 0, removed)
    for (const d of detached) d.item.tags.splice(d.pos, 0, d.tag)
    saveTagOrder()
  }
}

// ── Board column drag-reorder ──────────────────────────────────────────────
function loadTagOrder(): string[] {
  try {
    const raw = localStorage.getItem(TAG_ORDER_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function saveTagOrder() {
  try {
    localStorage.setItem(TAG_ORDER_KEY, JSON.stringify(availableTags.value.map(t => t.id)))
  } catch { /* ignore */ }
}

function applyStoredTagOrder() {
  const order = loadTagOrder()
  if (!order.length) return
  availableTags.value.sort((a, b) => {
    const ia = order.indexOf(a.id)
    const ib = order.indexOf(b.id)
    if (ia === -1 && ib === -1) return 0
    if (ia === -1) return 1   // 未記錄的（新標籤）排最後
    if (ib === -1) return -1
    return ia - ib
  })
}

function onTagDragStart(tagId: string, e: DragEvent) {
  if (tagId === '__none__' || editingTagId.value === tagId) return
  dragTagId.value = tagId
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', tagId)
  }
}

function onTagDragEnd() {
  dragTagId.value = null
  dragOverTagId.value = null
}

function onTagDrop(targetId: string) {
  const fromId = dragTagId.value
  dragTagId.value = null
  dragOverTagId.value = null
  if (!fromId || fromId === targetId) return
  const arr = availableTags.value
  const fromIdx = arr.findIndex(t => t.id === fromId)
  const toIdx = arr.findIndex(t => t.id === targetId)
  if (fromIdx === -1 || toIdx === -1) return
  const [moved] = arr.splice(fromIdx, 1)
  arr.splice(toIdx, 0, moved)
  saveTagOrder()
}

// ── Board add tag column ───────────────────────────────────────────────────
function startAddBoardTag() {
  addingBoardTag.value = true
  boardTagName.value = ''
  nextTick(() => boardTagInputEl.value?.focus())
}

async function confirmBoardTag() {
  const name = boardTagName.value.trim()
  addingBoardTag.value = false
  boardTagName.value = ''
  if (!name) return
  const tempId = `temp-${Date.now()}`
  availableTags.value.push({ id: tempId, name, color: null })
  try {
    const tag = await createTag({ name })
    const idx = availableTags.value.findIndex(t => t.id === tempId)
    if (idx !== -1) availableTags.value[idx] = tag
  } catch {
    availableTags.value = availableTags.value.filter(t => t.id !== tempId)
  }
}

function cancelBoardTag(e: KeyboardEvent) {
  addingBoardTag.value = false
  boardTagName.value = ''
  ;(e.target as HTMLElement).blur()
}

// ── Modal inline tag add (optimistic) ─────────────────────────────────────
function startAddTag() {
  addingTag.value = true
  newTagName.value = ''
  nextTick(() => newTagInputEl.value?.focus())
}

async function confirmNewTag() {
  const name = newTagName.value.trim()
  addingTag.value = false
  newTagName.value = ''
  if (!name) return
  const tempId = `temp-${Date.now()}`
  availableTags.value.push({ id: tempId, name, color: null })
  editForm.value.tag_ids.push(tempId)
  try {
    const tag = await createTag({ name })
    const idx = availableTags.value.findIndex(t => t.id === tempId)
    if (idx !== -1) availableTags.value[idx] = tag
    const tidIdx = editForm.value.tag_ids.indexOf(tempId)
    if (tidIdx !== -1) editForm.value.tag_ids[tidIdx] = tag.id
    saveTags()  // 用真實 tag id 存到卡片
  } catch {
    availableTags.value = availableTags.value.filter(t => t.id !== tempId)
    editForm.value.tag_ids = editForm.value.tag_ids.filter(id => id !== tempId)
  }
}

function cancelNewTag() {
  addingTag.value = false
  newTagName.value = ''
}
</script>

<style scoped>
.trips-app {
  display: flex;
  height: calc(100vh - 56px);
  overflow: hidden;
}

/* ── Sidebar ── */
.trips-side {
  flex: 0 0 280px;
  border-right: 1px solid var(--border);
  background: color-mix(in oklab, var(--bg) 55%, var(--surface));
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.trips-side__head {
  padding: 18px 18px 12px;
  display: flex;
  align-items: center;
  gap: 9px;
}
.trips-side__lbl { font-family: var(--font-brand); font-weight: 600; font-size: 15px; color: var(--text); }
.trips-side__count {
  font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim);
  background: var(--surface2); border: 1px solid var(--border); padding: 1px 8px; border-radius: 20px;
}
.trips-side__newbtn {
  margin-left: auto; width: 28px; height: 28px; border-radius: 8px;
  display: inline-flex; align-items: center; justify-content: center;
  color: var(--text-dim); border: 1px solid var(--border); background: transparent; transition: all .14s ease;
}
.trips-side__newbtn:hover { color: var(--accent); border-color: var(--accent-bdr); background: var(--accent-dim); }
.trips-side__newbtn svg { width: 14px; height: 14px; }

.trips-rlist {
  flex: 1 1 auto; overflow-y: auto; padding: 4px 10px 18px;
  display: flex; flex-direction: column; gap: 4px;
}
.trips-rlist__loading, .trips-rlist__empty {
  font-size: 12px; color: var(--text-dim); padding: 16px 4px; text-align: center;
}
.trips-ritem {
  display: block; width: 100%; text-align: left; padding: 13px 14px; border-radius: 12px;
  border: 1px solid transparent; cursor: pointer;
  transition: background .14s ease, border-color .14s ease; background: transparent; color: inherit;
}
.trips-ritem:hover { background: var(--surface2); }
.trips-ritem.is-active { background: var(--surface2); border-color: var(--border2); }
.trips-ritem__title {
  font-size: 13.5px; font-weight: 600; line-height: 1.45; color: var(--text); margin: 0 0 5px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.trips-ritem__desc {
  font-size: 11.5px; color: var(--text-mid); line-height: 1.5; margin: 0 0 6px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.trips-ritem__meta { display: flex; align-items: center; gap: 8px; }
.trips-ritem__date { font-family: var(--font-mono); font-size: 10px; color: var(--text-dim); }
.trips-ritem__count { font-family: var(--font-mono); font-size: 10px; color: var(--text-dim); }
.trips-ritem__role {
  font-size: 9.5px; padding: 1px 6px; border-radius: 99px; white-space: nowrap;
}
.trips-ritem__role--editor { background: #dbeafe; color: #1e40af; }
.trips-ritem__role--viewer { background: var(--surface2); color: var(--text-dim); }

/* ── Main ── */
.trips-main { flex: 1 1 auto; display: flex; flex-direction: column; min-width: 0; min-height: 0; }
.trips-scroll { flex: 1 1 auto; overflow: hidden; display: flex; flex-direction: column; }
.trips-doc { flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; max-width: 1280px; width: 100%; margin: 0 auto; padding: 30px 44px 0; }
.trips-empty { display: flex; align-items: center; justify-content: center; flex: 1; color: var(--text-dim); font-size: 14px; }

/* Title row */
.trips-back-btn { display: none; }
.trips-doc__top { display: flex; align-items: flex-start; gap: 16px; margin-bottom: 18px; }
.trips-doc__titlewrap { flex: 1; min-width: 0; }
.trips-doc__title {
  font-family: var(--font-brand); font-weight: 700; font-size: 32px;
  letter-spacing: -0.02em; line-height: 1.15; margin: 0 0 10px; outline: none; border-radius: 6px;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  text-overflow: ellipsis;
  line-clamp: 1;
  -webkit-line-clamp: 1;
  overflow: hidden;
}
.trips-doc__title:focus { background: var(--surface2); }
.trips-doc__sub { font-family: var(--font-mono); font-size: 11.5px; color: var(--text-dim); }
.trips-doc__rolebadge {
  font-size: 10px; padding: 1px 7px; border-radius: 99px; white-space: nowrap;
  display: inline-block; vertical-align: middle; margin-left: 6px;
}
.trips-doc__rolebadge--owner  { background: #fef3c7; color: #92400e; }
.trips-doc__rolebadge--editor { background: #dbeafe; color: #1e40af; }
.trips-doc__rolebadge--viewer { background: var(--surface2); color: var(--text-dim); }
.trips-doc__actions { display: flex; gap: 8px; flex-shrink: 0; padding-top: 6px; }

/* Sources trigger */
.trips-doc__srcbtn {
  font-family: var(--font-mono); font-size: 11.5px; color: var(--text-dim);
  background: none; border: none; padding: 0; cursor: pointer;
  text-decoration: underline; text-underline-offset: 2px; transition: color .14s ease;
}
.trips-doc__srcbtn:hover { color: var(--accent); }

/* Views */
.trips-views { display: flex; align-items: center; gap: 4px; margin-bottom: 22px; border-bottom: 1px solid var(--border); }
.trips-vtab {
  display: inline-flex; align-items: center; gap: 7px; font-size: 13px; font-weight: 500; color: var(--text-mid);
  padding: 9px 13px; border-radius: 9px 9px 0 0; border: 1px solid transparent; border-bottom: none;
  margin-bottom: -1px; cursor: pointer; transition: all .14s ease; position: relative; background: transparent;
}
.trips-vtab:hover { color: var(--text); background: var(--surface2); }
.trips-vtab__n { font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); }
.trips-vtab.is-active { color: var(--text); }
.trips-vtab.is-active::after {
  content: ''; position: absolute; left: 6px; right: 6px; bottom: -1px;
  height: 2px; background: var(--accent); border-radius: 2px;
}

/* Cards */
.trips-tcard {
  display: flex; flex-direction: column; gap: 6px; padding: 11px 13px; border-radius: 11px;
  background: var(--surface); border: 1px solid var(--border); cursor: pointer; transition: all .15s ease;
}
.trips-tcard:hover { border-color: var(--border2); transform: translateY(-2px); box-shadow: 0 10px 26px -14px var(--shadow); }
/* AI 修改後的卡片：綠色閃爍一下 */
.trips-tcard.is-aiflash { animation: trips-aiflash 1.4s ease-out; }
@keyframes trips-aiflash {
  0%   { background: color-mix(in oklab, #34c759 38%, var(--surface)); border-color: #34c759; box-shadow: 0 0 0 3px color-mix(in oklab, #34c759 30%, transparent); }
  60%  { background: color-mix(in oklab, #34c759 18%, var(--surface)); border-color: color-mix(in oklab, #34c759 55%, var(--border)); }
  100% { background: var(--surface); border-color: var(--border); box-shadow: none; }
}
.trips-tcard__name { display: flex; align-items: flex-start; gap: 7px; font-size: 13px; font-weight: 500; color: var(--text); line-height: 1.4; }
.trips-tcard__emoji { flex: 0 0 auto; }
.trips-tcard__meta { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.trips-tcard__time { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); }
.trips-booked {
  display: inline-flex; align-items: center; gap: 3px; font-family: var(--font-mono); font-size: 9.5px; font-weight: 500;
  color: var(--tag-a); background: color-mix(in oklab, var(--tag-a) 14%, transparent);
  border: 1px solid color-mix(in oklab, var(--tag-a) 28%, transparent); padding: 2px 7px; border-radius: 6px;
}
.trips-empty-note { font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); padding: 8px 2px; }

/* Board */
.trips-board {
  flex: 1 1 auto; min-height: 0;
  display: flex; gap: 16px;
  overflow-x: auto; overflow-y: hidden;
  padding-bottom: 16px;
  align-items: stretch;
}
.trips-bcol { flex: 0 0 256px; display: flex; flex-direction: column; min-height: 0; border-radius: 12px; transition: box-shadow .14s ease, opacity .14s ease; }
.trips-bcol.is-dragging { opacity: .4; }
.trips-bcol.is-dragover { box-shadow: inset 3px 0 0 var(--accent); }
.trips-bcol--addtag { flex: 0 0 160px; justify-content: flex-start; padding-top: 2px; }
.trips-bcol__head { display: flex; align-items: center; gap: 9px; padding: 0 2px; margin-bottom: 10px; flex-shrink: 0; }
.trips-bcol__head--drag { cursor: grab; }
.trips-bcol__head--drag:active { cursor: grabbing; }
.trips-bcol__del {
  width: 20px; height: 20px; flex-shrink: 0; border-radius: 6px;
  display: inline-flex; align-items: center; justify-content: center;
  background: transparent; border: none; color: var(--text-dim);
  cursor: pointer; opacity: 0; transition: opacity .12s ease, color .12s ease, background .12s ease;
}
.trips-bcol__del svg { width: 12px; height: 12px; }
.trips-bcol__head:hover .trips-bcol__del { opacity: 1; }
.trips-bcol__del:hover { background: var(--surface2); color: #e85555; }
.trips-bcol__cards { flex: 1 1 auto; overflow-y: auto; min-height: 0; display: flex; flex-direction: column; gap: 8px; padding-bottom: 4px; }
.trips-bcol__taginput {
  flex: 1; min-width: 0;
  background: var(--surface2);
  border: 1px solid var(--accent);
  border-radius: 20px;
  padding: 3px 10px;
  font-size: 12px;
  color: var(--text);
  outline: none;
}
.trips-colcount { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); margin-left: auto; }
.trips-addcol-btn {
  display: flex; align-items: center; gap: 7px;
  padding: 7px 12px; border-radius: 10px;
  border: 1px dashed var(--border2);
  background: transparent; color: var(--text-dim);
  font-size: 12.5px; cursor: pointer;
  transition: all .14s ease; white-space: nowrap;
}
.trips-addcol-btn svg { width: 13px; height: 13px; flex-shrink: 0; }
.trips-addcol-btn:hover { border-color: var(--accent-bdr); color: var(--accent); background: var(--accent-dim); }

/* Date board */
.trips-dboard {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  gap: 16px;
  overflow-x: auto;
  overflow-y: auto;
  padding-bottom: 16px;
  align-items: stretch;
}
.trips-dcol { flex: 0 0 240px; display: flex; flex-direction: column; gap: 10px; }
.trips-dcol__head { padding: 0 2px; margin-bottom: 2px; }
.trips-dcol__month { font-family: var(--font-mono); font-size: 10px; color: var(--text-dim); text-transform: uppercase; letter-spacing: .08em; margin-bottom: 2px; }
.trips-dcol__date { display: flex; align-items: baseline; gap: 6px; }
.trips-dcol__d { font-family: var(--font-brand); font-weight: 700; font-size: 17px; color: var(--text); letter-spacing: -0.01em; }
.trips-dcol__dow { font-family: var(--font-mono); font-size: 10.5px; color: var(--text-dim); }
.trips-dcol__cards { display: flex; flex-direction: column; gap: 8px; }

/* ── Modal ── */
.trips-modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.46); z-index: 200;
  display: flex; align-items: center; justify-content: center; padding: 24px;
}
.trips-modal {
  position: relative;
  width: min(max(70vw, calc(494px + 35.7vw)), 100%);
  max-width: 100vw;
  max-height: 88vh;
  background: var(--bg);
  border: 1px solid var(--border2);
  border-radius: 16px;
  box-shadow: 0 24px 64px -16px rgba(0,0,0,.5);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.trips-modal__head {
  padding: 14px 16px; border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 10px; flex-shrink: 0;
}
.trips-modal__title {
  flex: 1; min-width: 0;
  background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
  padding: 8px 11px; font-size: 15px; font-weight: 600; color: var(--text);
  outline: none; transition: border-color .15s;
}
.trips-modal__title:focus { border-color: var(--accent); }
.trips-modal__trash {
  flex-shrink: 0; background: none; border: none; cursor: pointer; padding: 6px;
  border-radius: 8px; color: var(--text-dim); display: flex; align-items: center; justify-content: center;
  transition: color .14s, background .14s;
}
.trips-modal__trash:hover { background: var(--surface2); color: var(--text); }
.trips-modal__trash:disabled { opacity: .4; cursor: not-allowed; }
.trips-modal__body {
  width: min(max(70%, calc(494px + 35.7%)), 100%);
  margin: auto;
  scrollbar-width: none;
  flex: 1 1 auto;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.trips-modal__foot { padding: 14px 20px; border-top: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-shrink: 0; }

/* Fields */
.trips-field { display: flex; flex-direction: column; gap: 6px; }
.trips-field--note { gap: 8px; }
.trips-field__lbl { font-size: 12px; font-weight: 500; color: var(--text-mid); }
.trips-field__input {
  background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
  padding: 8px 11px; font-size: 13.5px; color: var(--text); outline: none; transition: border-color .15s;
}
.trips-field__input:focus { border-color: var(--accent); }

/* 地標：開啟地圖按鈕 + 編輯 */
.trips-place-row { display: flex; gap: 8px; align-items: center; }
.trips-place-open { flex: 1; text-align: center; text-decoration: none; }
.trips-place-edit { flex: 0 0 auto; }

/* 名稱列的 Emoji 觸發鈕（在 modal head）*/
.trips-emoji-trigger {
  flex: 0 0 auto;
  width: 44px; height: 40px;
  font-size: 22px;
  line-height: 1;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: border-color .15s, background .15s;
}
.trips-emoji-trigger:hover { border-color: var(--accent); background: var(--accent-dim); }

/* Date + time combined */
.trips-field__timerow { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.trips-field__dt { width: 148px; }
.trips-field__tm { width: 138px; }
.trips-field__sep { color: var(--text-dim); font-size: 12px; }

/* Tiptap in modal */
.trips-tiptap-wrap {
  border: 1px solid var(--border); border-radius: 8px; min-height: 100px;
  overflow: hidden; background: var(--surface);
}
.trips-tiptap-wrap:focus-within { border-color: var(--accent); }
.trips-tiptap-wrap :deep(.ProseMirror) {
  padding: 8px 8px 8px 56px;
}

/* Tags */
.trips-linked-row { display: flex; }
/* 已預定票券 + 票券連結 同列 */
.trips-booked-row { display: flex; flex-direction: row; align-items: center; gap: 14px; }
.trips-check { display: flex; align-items: center; gap: 8px; flex-shrink: 0; cursor: pointer; }
.trips-ticket { flex: 1; min-width: 0; }
.trips-ticket .trips-place-open { font-size: 13px; }

/* 關聯知識：文字按鈕（同 doc__srcbtn 風格）*/
.trips-ksrcbtn {
  font-family: var(--font-mono); font-size: 12px; color: var(--text-dim);
  background: none; border: none; padding: 0; cursor: pointer;
  text-decoration: underline; text-underline-offset: 2px; transition: color .14s ease;
}
.trips-ksrcbtn:hover { color: var(--accent); }

.trips-tags-wrap { display: flex; flex-wrap: wrap; gap: 7px; align-items: center; }
.trips-pill {
  padding: 5px 12px; border-radius: 20px; font-size: 12px;
  border: 1px solid var(--border); background: var(--surface); color: var(--text-mid);
  cursor: pointer; transition: all .14s ease;
}
.trips-pill:hover { border-color: var(--border2); color: var(--text); }
.trips-pill.is-active { background: var(--accent-dim); border-color: var(--accent-bdr); color: var(--accent); }
.trips-pill--ro { cursor: default; pointer-events: none; }
.trips-pill--ro:hover { border-color: var(--accent-bdr); }

/* Viewer read-only states */
.trips-emoji-trigger--ro {
  cursor: default; pointer-events: none;
}
.trips-modal__title--ro {
  background: transparent; border-color: transparent; cursor: default;
}
.trips-modal__title--ro:focus { border-color: transparent; }
.trips-tiptap-wrap--ro { background: transparent; border-color: var(--border); }
.trips-tiptap-wrap--ro:focus-within { border-color: var(--border); }
.trips-ro-empty { font-size: 13px; color: var(--text-dim); }
.trips-field__input:disabled { opacity: .55; cursor: not-allowed; }
.trips-newtag { display: inline-flex; align-items: center; }
.trips-newtag__input {
  background: var(--surface); border: 1px solid var(--accent); border-radius: 20px;
  padding: 4px 12px; font-size: 12px; color: var(--text); outline: none; width: 120px;
}

/* Transitions */
.modal-enter-active, .modal-leave-active { transition: opacity .18s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-active .trips-modal, .modal-leave-active .trips-modal { transition: transform .18s ease, opacity .18s ease; }
.modal-enter-from .trips-modal, .modal-leave-to .trips-modal { transform: scale(0.96); opacity: 0; }

@media (max-width: 900px) {
  .trips-app {
    display: block;
    position: relative;
    overflow: hidden;
  }
  .trips-side,
  .trips-main {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    transition: transform .3s cubic-bezier(.4, 0, .2, 1);
    will-change: transform;
  }
  .trips-doc__top { flex-wrap: wrap; align-items: center; }
  .trips-doc__actions { width: 100%; padding-top: 0; }
  .trips-back-btn {
    display: flex; align-items: center; justify-content: center;
    width: 32px; height: 32px; border-radius: 8px; flex-shrink: 0;
    background: none; border: 1px solid var(--border); color: var(--text-mid);
    cursor: pointer; transition: background .14s, color .14s;
  }
  .trips-back-btn:hover { background: var(--surface2); color: var(--text); }
  .trips-side { transform: translateX(0); flex: none; }
  .trips-side--hidden-mobile { transform: translateX(-100%); }
  .trips-main { transform: translateX(100%); flex: none; }
  .trips-main:not(.trips-main--hidden-mobile) { transform: translateX(0); }
  .trips-doc { padding: 22px 18px 0px; }
  .trips-modal-overlay { padding: 0; align-items: flex-end; }
  .trips-modal { width: 100vw; max-width: 100vw; max-height: 92vh; border-radius: 16px 16px 0 0; }

  /* Board: snap one column at a time, each column 90vw centered */
  .trips-board {
    margin-inline: -18px;
    padding-inline: 5vw;
    gap: 10vw;
    scroll-snap-type: x mandatory;
    -webkit-overflow-scrolling: touch;
  }
  .trips-bcol {
    flex: 0 0 90vw;
    scroll-snap-align: center;
  }
  .trips-bcol--addtag {
    flex: 0 0 auto;
    scroll-snap-align: none;
  }

  .trips-board, .trips-bcol__cards {
    list-style: none;
    display: flex;
    gap: 15px;
    overflow-x: auto;
    li {
      flex-shrink: 0;
      width: 90px;
      text-align: center;
      font-size: 18px;
      font-weight: 700;
      padding: 12px 12px;
    }
    .active {
      border-bottom: 4px solid #ff7800;
    }
  }
  .trips-bcol__cards::-webkit-scrollbar,   .trips-board::-webkit-scrollbar {
    display: none;
  }
}
</style>

<!-- Emoji picker: not scoped, teleported to body -->
<style>
.tep {
  position: fixed;
  z-index: 9999;
  background: var(--bg);
  border: 1px solid var(--border2);
  border-radius: 14px;
  padding: 10px 10px 0;
  box-shadow: 0 12px 40px -8px rgba(0,0,0,.55);
  width: 320px;
  display: flex;
  flex-direction: column;
  gap: 0;
}
.tep__grid {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 1px;
  max-height: 240px;
  overflow-y: auto;
}
.tep__btn {
  font-size: 20px;
  line-height: 1;
  padding: 5px 2px;
  border-radius: 7px;
  border: none;
  background: transparent;
  cursor: pointer;
  transition: background .1s ease;
  text-align: center;
}
.tep__btn:hover { background: var(--surface2); }
.tep__empty { font-size: 12px; color: var(--text-dim); padding: 16px; text-align: center; grid-column: 1 / -1; }
.tep__search {
  margin: 8px 0 0;
  padding: 8px 11px;
  background: var(--surface);
  border: none;
  border-top: 1px solid var(--border);
  border-radius: 0 0 12px 12px;
  font-size: 12.5px;
  color: var(--text);
  outline: none;
  width: 100%;
  box-sizing: border-box;
}
.tep__search::placeholder { color: var(--text-dim); }
.tep__search:focus { background: var(--surface2); }
</style>
