<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="open" class="trips-modal-overlay" @click.self="$emit('close')">
        <div class="trips-modal trips-share-modal">
          <div class="trips-modal__head">
            <span class="trips-share-modal__title">{{ t('trips.share.title') }}</span>
            <button class="trips-modal__close" @click="$emit('close')">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M18 6 6 18M6 6l12 12"/></svg>
            </button>
          </div>

          <div class="trips-modal__body trips-share-modal__body">

            <!-- ── Members list ─────────────────────────────────────────── -->
            <section class="tsm-section">
              <h3 class="tsm-section__label">{{ t('trips.share.membersSection') }}</h3>

              <!-- Owner row -->
              <div class="tsm-member-row">
                <div class="tsm-avatar">{{ ownerInitial }}</div>
                <div class="tsm-member-info">
                  <span class="tsm-member-email">{{ ownerEmail || t('trips.role.owner') }}</span>
                </div>
                <span class="tsm-role-badge tsm-role-badge--owner">{{ t('trips.role.owner') }}</span>
              </div>

              <!-- Member rows -->
              <div v-for="member in trip.members" :key="member.id" class="tsm-member-row">
                <div class="tsm-avatar">{{ initial(member.display_name || member.email) }}</div>
                <div class="tsm-member-info">
                  <span class="tsm-member-email">{{ member.email }}</span>
                  <span v-if="member.display_name" class="tsm-member-name">{{ member.display_name }}</span>
                </div>
                <template v-if="isOwner">
                  <select
                    class="tsm-role-select"
                    :value="member.role"
                    :disabled="savingMemberId === member.id"
                    @change="onRoleChange(member, ($event.target as HTMLSelectElement).value as 'editor' | 'viewer')"
                  >
                    <option value="editor">{{ t('trips.role.editor') }}</option>
                    <option value="viewer">{{ t('trips.role.viewer') }}</option>
                  </select>
                  <button
                    class="tsm-remove-btn"
                    :disabled="savingMemberId === member.id"
                    @click="onRemoveMember(member)"
                  >{{ t('trips.share.removeMember') }}</button>
                </template>
                <template v-else-if="member.member_user_id === currentUserId">
                  <button class="tsm-remove-btn tsm-remove-btn--leave" @click="onLeave(member)">
                    {{ t('trips.share.leaveTrip') }}
                  </button>
                </template>
                <template v-else>
                  <span :class="`tsm-role-badge tsm-role-badge--${member.role}`">{{ t(`trips.role.${member.role}`) }}</span>
                </template>
              </div>
            </section>

            <!-- ── Invite by email (owner only) ───────────────────────── -->
            <section v-if="isOwner" class="tsm-section">
              <h3 class="tsm-section__label">{{ t('trips.share.inviteSection') }}</h3>
              <div class="tsm-invite-row">
                <input
                  v-model="inviteEmail"
                  class="tsm-input"
                  type="email"
                  :placeholder="t('trips.share.emailPlaceholder')"
                  @keydown.enter.prevent="onInvite"
                />
                <select v-model="inviteRole" class="tsm-role-select">
                  <option value="viewer">{{ t('trips.role.viewer') }}</option>
                  <option value="editor">{{ t('trips.role.editor') }}</option>
                </select>
                <button class="btn" :disabled="inviting || !inviteEmail.trim()" @click="onInvite">
                  {{ inviting ? t('trips.share.inviting') : t('trips.share.inviteBtn') }}
                </button>
              </div>
              <p v-if="inviteError" class="tsm-error">{{ inviteError }}</p>
            </section>

            <!-- ── Invite link (owner only) ────────────────────────────── -->
            <section v-if="isOwner" class="tsm-section">
              <h3 class="tsm-section__label">{{ t('trips.share.linkSection') }}</h3>
              <div class="tsm-link-row">
                <select v-model="linkRole" class="tsm-role-select" :disabled="!!trip.invite_token">
                  <option value="viewer">{{ t('trips.role.viewer') }}</option>
                  <option value="editor">{{ t('trips.role.editor') }}</option>
                </select>
                <template v-if="trip.invite_token">
                  <button class="btn" @click="onCopyLink">{{ copied ? t('trips.share.copied') : t('trips.share.copyLink') }}</button>
                  <button class="btn btn--danger" @click="onRevokeLink">{{ t('trips.share.revokeLink') }}</button>
                </template>
                <button v-else class="btn" :disabled="generatingLink" @click="onGenerateLink">
                  {{ generatingLink ? t('trips.share.generating') : t('trips.share.generateLink') }}
                </button>
              </div>
              <p v-if="trip.invite_token" class="tsm-link-preview">{{ inviteUrl }}</p>
            </section>

          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import type { Trip, TripMember } from '~/types/api'

const props = defineProps<{ open: boolean; trip: Trip }>()
const emit = defineEmits<{ close: []; updated: [] }>()

const { t } = useI18n()
const { inviteMember, updateMemberRole, removeMember, generateInviteLink, revokeInviteLink } = useTrips()
const authStore = useAuthStore()
const toast = useToast()

const isOwner = computed(() => props.trip.my_role === 'owner')
const currentUserId = computed(() => authStore.user?.id ?? '')

// Owner 資訊：owner 看自己時用真實 email；非 owner 時僅顯示 placeholder
const ownerEmail = computed(() => isOwner.value ? (authStore.user?.email ?? '') : '')
const ownerInitial = computed(() => isOwner.value ? initial(authStore.user?.username || authStore.user?.email || '?') : '👑')

function initial(str: string) {
  return (str.trim()[0] ?? '?').toUpperCase()
}

// ── Invite by email ───────────────────────────────────────────────────────────
const inviteEmail = ref('')
const inviteRole = ref<'editor' | 'viewer'>('viewer')
const inviting = ref(false)
const inviteError = ref('')

async function onInvite() {
  const email = inviteEmail.value.trim()
  if (!email) return
  inviting.value = true
  inviteError.value = ''
  try {
    await inviteMember(props.trip.id, { email, role: inviteRole.value })
    inviteEmail.value = ''
    emit('updated')
  } catch {
    inviteError.value = t('trips.share.inviteFailed')
  } finally {
    inviting.value = false
  }
}

// ── Role change / remove ──────────────────────────────────────────────────────
const savingMemberId = ref<string | null>(null)

async function onRoleChange(member: TripMember, role: 'editor' | 'viewer') {
  savingMemberId.value = member.id
  try {
    await updateMemberRole(props.trip.id, member.id, { role })
    emit('updated')
  } catch {
    toast.show(t('trips.share.removeFailed'), 'error')
  } finally {
    savingMemberId.value = null
  }
}

async function onRemoveMember(member: TripMember) {
  savingMemberId.value = member.id
  try {
    await removeMember(props.trip.id, member.id)
    emit('updated')
  } catch {
    toast.show(t('trips.share.removeFailed'), 'error')
  } finally {
    savingMemberId.value = null
  }
}

async function onLeave(member: TripMember) {
  if (!confirm(t('trips.share.leaveConfirm', { title: props.trip.title }))) return
  try {
    await removeMember(props.trip.id, member.id)
    emit('updated')
    emit('close')
  } catch {
    toast.show(t('trips.share.removeFailed'), 'error')
  }
}

// ── Invite link ───────────────────────────────────────────────────────────────
const linkRole = ref<'editor' | 'viewer'>(props.trip.invite_role as 'editor' | 'viewer' || 'viewer')
const generatingLink = ref(false)
const copied = ref(false)

const inviteUrl = computed(() => {
  if (!props.trip.invite_token) return ''
  const base = window.location.origin
  return `${base}/app/trips?join_token=${props.trip.invite_token}`
})

async function onGenerateLink() {
  generatingLink.value = true
  try {
    await generateInviteLink(props.trip.id, { role: linkRole.value })
    emit('updated')
  } catch {
    toast.show(t('trips.share.removeFailed'), 'error')
  } finally {
    generatingLink.value = false
  }
}

async function onCopyLink() {
  try {
    await navigator.clipboard.writeText(inviteUrl.value)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch {
    // fallback: show the URL for manual copy
  }
}

async function onRevokeLink() {
  if (!confirm(t('trips.share.revokeConfirm'))) return
  try {
    await revokeInviteLink(props.trip.id)
    emit('updated')
  } catch {
    toast.show(t('trips.share.removeFailed'), 'error')
  }
}
</script>

<style scoped>
/* ── Overlay / modal shell (mirrors trips.vue — Teleport escapes scoped CSS) ── */
.trips-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.46);
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.trips-modal {
  position: relative;
  background: var(--bg);
  border: 1px solid var(--border2);
  border-radius: 16px;
  box-shadow: 0 24px 64px -16px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  max-height: 88vh;
}
.trips-modal__head {
  padding: 14px 16px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.trips-modal__body {
  flex: 1 1 auto;
  overflow-y: auto;
  padding: 20px;
  scrollbar-width: none;
}
/* Transition */
.modal-enter-active,
.modal-leave-active { transition: opacity 0.18s ease; }
.modal-enter-from,
.modal-leave-to { opacity: 0; }
.modal-enter-active .trips-modal,
.modal-leave-active .trips-modal { transition: transform 0.18s ease, opacity 0.18s ease; }
.modal-enter-from .trips-modal,
.modal-leave-to .trips-modal { transform: scale(0.96); opacity: 0; }

/* ── Share modal specific ── */
.trips-share-modal {
  max-width: 480px;
  width: 100%;
}

.trips-modal__close {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-dim);
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
}

.trips-modal__close:hover {
  color: var(--text);
  background: var(--surface2);
}

.trips-share-modal__title {
  font-weight: 600;
  font-size: 15px;
}

.trips-share-modal__body {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.tsm-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tsm-section__label {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-dim);
  margin: 0;
}

.tsm-member-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.tsm-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--surface2);
  color: var(--text-dim);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.tsm-member-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.tsm-member-email {
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tsm-member-name {
  font-size: 11px;
  color: var(--text-dim);
}

.tsm-role-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 99px;
  white-space: nowrap;
  flex-shrink: 0;
}

.tsm-role-badge--owner  { background: #fef3c7; color: #92400e; }
.tsm-role-badge--editor { background: #dbeafe; color: #1e40af; }
.tsm-role-badge--viewer { background: var(--surface2); color: var(--text-dim); }

.tsm-role-select {
  font-size: 12px;
  padding: 3px 6px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text);
  cursor: pointer;
  flex-shrink: 0;
  outline: none;
}

.tsm-remove-btn {
  font-size: 12px;
  padding: 3px 8px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: none;
  color: var(--text-dim);
  cursor: pointer;
  flex-shrink: 0;
  white-space: nowrap;
}

.tsm-remove-btn:hover { background: var(--surface2); }
.tsm-remove-btn--leave { color: #e85555; }

.tsm-invite-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tsm-input {
  flex: 1;
  min-width: 180px;
  padding: 7px 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 13px;
  background: var(--surface);
  color: var(--text);
  outline: none;
  transition: border-color .15s;
}
.tsm-input:focus { border-color: var(--accent); }

.tsm-error {
  font-size: 12px;
  color: #e85555;
  margin: 0;
}

.tsm-link-row {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.tsm-link-preview {
  font-size: 11px;
  color: var(--text-dim);
  word-break: break-all;
  margin: 0;
  padding: 6px 8px;
  background: var(--surface2);
  border-radius: 6px;
}
</style>
