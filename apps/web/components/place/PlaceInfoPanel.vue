<script setup lang="ts">
interface PlaceReview {
  author: string | null
  author_photo: string | null
  rating: number | null
  text: string | null
  relative_time: string | null
}

interface PlaceDetails {
  place_id: string
  name: string | null
  rating: number | null
  reviews: PlaceReview[] | null
  photos: string[] | null
  address: string | null
  phone: string | null
  opening_hours: { open_now: boolean; weekday_descriptions: string[] } | null
  maps_url: string | null
}

const props = defineProps<{
  placeData: PlaceDetails | null
  placeLoading: boolean
  placeError: string
  showDelete?: boolean
}>()

defineEmits<{ delete: [] }>()

const config = useRuntimeConfig()
const apiBase = config.public.apiBase as string

const hoursExpanded = ref(false)

watch(() => props.placeData, () => { hoursExpanded.value = false })

function photoUrl(ref: string) {
  return `${apiBase}/places/photo?ref=${encodeURIComponent(ref)}&max_width=400`
}

function ratingStars(rating: number | null): string {
  if (!rating) return ''
  const full = Math.round(rating)
  return '★'.repeat(full) + '☆'.repeat(5 - full)
}

const todayHours = computed(() => {
  const descs = props.placeData?.opening_hours?.weekday_descriptions
  if (!descs?.length) return null
  const idx = (new Date().getDay() + 6) % 7
  return descs[idx] ?? null
})
</script>

<template>
  <div class="pip">
    <!-- Loading -->
    <div v-if="placeLoading" class="pip__state">
      <span class="pip__spinner" />
      <span>載入地點資訊…</span>
    </div>

    <!-- Error -->
    <div v-else-if="placeError" class="pip__state pip__state--err">{{ placeError }}</div>

    <!-- Not found -->
    <div v-else-if="!placeData" class="pip__state">找不到 Google 地點資訊</div>

    <!-- Content -->
    <template v-else>

      <!-- Photos -->
      <div v-if="placeData.photos?.length" class="pip__photos">
        <img
          v-for="ref in placeData.photos.slice(0, 6)"
          :key="ref"
          :src="photoUrl(ref)"
          class="pip__photo"
          alt=""
        />
      </div>

      <!-- Rating -->
      <div v-if="placeData.rating" class="pip__rating">
        <span class="pip__rating-num">{{ placeData.rating.toFixed(1) }}</span>
        <span class="pip__stars">{{ ratingStars(placeData.rating) }}</span>
      </div>

      <!-- Info rows -->
      <div class="pip__info">
        <div v-if="placeData.address" class="pip__info-row">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="10" r="3"/><path d="M12 2a8 8 0 0 0-8 8c0 5.25 8 14 8 14s8-8.75 8-14a8 8 0 0 0-8-8z"/></svg>
          <span>{{ placeData.address }}</span>
        </div>
        <div v-if="placeData.phone" class="pip__info-row">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 1.25h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.84a16 16 0 0 0 5.83 5.83l.96-.96a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 21.73 16a2 2 0 0 1 .27.92z"/></svg>
          <a :href="`tel:${placeData.phone}`" class="pip__phone">{{ placeData.phone }}</a>
        </div>
        <div v-if="placeData.opening_hours" class="pip__info-row pip__hours-row" @click="hoursExpanded = !hoursExpanded">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          <span
            class="pip__open-status"
            :class="placeData.opening_hours.open_now ? 'pip__open-status--open' : 'pip__open-status--closed'"
          >{{ placeData.opening_hours.open_now ? '目前營業中' : '目前休息中' }}</span>
          <span v-if="todayHours && !hoursExpanded" class="pip__hours-today">
            · {{ todayHours.split(':').slice(1).join(':').trim() }}
          </span>
          <svg class="pip__hours-caret" :class="{ 'pip__hours-caret--open': hoursExpanded }" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="6 9 12 15 18 9"/></svg>
        </div>
        <div v-if="hoursExpanded && placeData.opening_hours?.weekday_descriptions" class="pip__hours-list">
          <div v-for="(day, i) in placeData.opening_hours.weekday_descriptions" :key="i" class="pip__hours-day">{{ day }}</div>
        </div>
      </div>

      <!-- Reviews -->
      <div v-if="placeData.reviews?.length" class="pip__reviews">
        <div class="pip__section-title">評論</div>
        <div v-for="(rev, i) in placeData.reviews" :key="i" class="pip__review">
          <div class="pip__review-header">
            <img v-if="rev.author_photo" :src="rev.author_photo" class="pip__review-avatar" alt="" referrerpolicy="no-referrer" />
            <div v-else class="pip__review-avatar pip__review-avatar--empty" />
            <div class="pip__review-meta">
              <span class="pip__review-author">{{ rev.author || '匿名' }}</span>
              <span class="pip__review-time">{{ rev.relative_time }}</span>
            </div>
          </div>
          <div class="pip__review-stars">{{ ratingStars(rev.rating) }}</div>
          <p v-if="rev.text" class="pip__review-text">{{ rev.text }}</p>
        </div>
      </div>

      <!-- Footer: Maps link + delete -->
      <div class="pip__footer">
        <a
          v-if="placeData.maps_url"
          :href="placeData.maps_url"
          target="_blank"
          rel="noopener noreferrer"
          class="pip__maps-link"
        >
          在 Google Maps 查看
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
        </a>
        <button v-if="showDelete" class="pip__delete" @click="$emit('delete')">刪除地標</button>
      </div>

    </template>
  </div>
</template>

<style scoped>
.pip {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.pip__state {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-mid);
  padding: 8px 0;
}
.pip__state--err { color: #dc2626; }

.pip__spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--border2);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: pip-spin 0.7s linear infinite;
  flex-shrink: 0;
}
@keyframes pip-spin { to { transform: rotate(360deg); } }

/* Photos */
.pip__photos {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  scrollbar-width: none;
}
.pip__photos::-webkit-scrollbar { display: none; }
.pip__photo {
  width: 80px;
  height: 64px;
  object-fit: cover;
  border-radius: 6px;
  flex-shrink: 0;
  background: var(--surface2);
}

/* Rating */
.pip__rating {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.pip__rating-num {
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
  line-height: 1;
}
.pip__stars {
  font-size: 13px;
  color: #f59e0b;
  letter-spacing: 1px;
}

/* Info rows */
.pip__info {
  display: flex;
  flex-direction: column;
  gap: 7px;
  border-top: 1px solid var(--border);
  padding-top: 10px;
}
.pip__info-row {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  font-size: 12.5px;
  color: var(--text);
}
.pip__info-row svg { flex-shrink: 0; margin-top: 1px; color: var(--text-mid); }
.pip__phone { color: var(--accent); text-decoration: none; }
.pip__phone:hover { text-decoration: underline; }

.pip__hours-row { cursor: pointer; align-items: center; }
.pip__open-status--open { color: #059669; font-weight: 500; }
.pip__open-status--closed { color: #dc2626; font-weight: 500; }
.pip__hours-today { color: var(--text-mid); }
.pip__hours-caret {
  margin-left: auto;
  transition: transform 0.18s;
  flex-shrink: 0;
  color: var(--text-mid);
}
.pip__hours-caret--open { transform: rotate(180deg); }
.pip__hours-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-left: 20px;
}
.pip__hours-day {
  font-size: 11.5px;
  color: var(--text-mid);
  line-height: 1.5;
}

/* Reviews */
.pip__reviews {
  display: flex;
  flex-direction: column;
  gap: 10px;
  border-top: 1px solid var(--border);
  padding-top: 10px;
}
.pip__section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-mid);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.pip__review {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}
.pip__review:last-child { border-bottom: none; padding-bottom: 0; }
.pip__review-header { display: flex; align-items: center; gap: 8px; }
.pip__review-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}
.pip__review-avatar--empty { background: var(--surface2); }
.pip__review-meta { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.pip__review-author {
  font-size: 12px;
  font-weight: 600;
  color: var(--text);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.pip__review-time { font-size: 11px; color: var(--text-mid); }
.pip__review-stars { font-size: 11px; color: #f59e0b; letter-spacing: 1px; }
.pip__review-text {
  font-size: 12px;
  color: var(--text);
  margin: 0;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Footer */
.pip__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid var(--border);
  padding-top: 10px;
  margin-top: 2px;
  gap: 8px;
}
.pip__maps-link {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 500;
  color: var(--accent);
  text-decoration: none;
}
.pip__maps-link:hover { text-decoration: underline; }

.pip__delete {
  font-size: 11.5px;
  font-weight: 500;
  padding: 4px 10px;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid rgba(239, 68, 68, 0.2);
  background: rgba(239, 68, 68, 0.08);
  color: #dc2626;
  transition: opacity 0.12s;
  flex-shrink: 0;
}
.pip__delete:hover { opacity: 0.8; }
</style>
