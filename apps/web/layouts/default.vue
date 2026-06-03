<template>
  <div>
    <LayoutAppNav v-if="isLoggedIn" />
    <LayoutGuestNav v-else />
    <slot />
  </div>
</template>

<script setup lang="ts">
const supabaseUser = useSupabaseUser()
const isLoggedIn = computed(() => !!supabaseUser.value)
</script>

<style>
.nav__tab-group {
  position: relative;
  display: inline-flex;
}

.nav__tab-group:hover .nav__explore-menu {
  pointer-events: auto;
}

.nav__tab-group:hover .nav__explore-menu-inner {
  opacity: 1;
  transform: translateY(0);
}

.nav__explore-menu {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  padding-top: 6px;
  width: 160px;
  z-index: 200;
  pointer-events: none;
}

.nav__explore-menu-inner {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  padding: 4px;
  opacity: 0;
  transform: translateY(-4px);
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.nav__explore-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  font-size: 13px;
  font-family: var(--font-ui);
  color: var(--text-mid);
  border-radius: 7px;
  transition: background 0.1s, color 0.1s;
}

.nav__explore-item:hover {
  background: var(--bg);
  color: var(--text);
}

.nav__explore-item--active {
  color: var(--accent);
}

.nav__explore-item svg {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.nav__user {
  position: relative;
}

.nav__avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  overflow: hidden;
  border: 1.5px solid var(--border);
  background: var(--surface);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  font-family: var(--font-mono);
  color: var(--text);
  padding: 0;
  transition: border-color 0.15s;
}

.nav__avatar:hover {
  border-color: var(--text-mid);
}

.nav__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.nav__menu {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  width: 220px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  z-index: 200;
  overflow: hidden;
  padding: 6px;
}

.nav__menu-header {
  padding: 10px 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav__menu-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nav__menu-email {
  font-size: 11px;
  color: var(--text-dim);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nav__menu-divider {
  height: 1px;
  background: var(--border);
  margin: 4px 0;
}

.nav__menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 12px;
  font-size: 13px;
  font-family: var(--font-ui);
  color: var(--text);
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  text-align: left;
  transition: background 0.12s;
}

.nav__menu-item:hover {
  background: var(--bg);
}

.nav__menu-item svg {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
  color: var(--text-mid);
}

.nav__menu-item--danger {
  color: #e85555;
}

.nav__menu-item--danger svg {
  color: #e85555;
}

.nav__menu-item--chevron {
  justify-content: flex-start;
}

.nav__menu-chevron {
  width: 14px !important;
  height: 14px !important;
  margin-left: auto;
  color: var(--text-dim) !important;
  flex-shrink: 0;
}

.nav__menu-back {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 600;
  font-family: var(--font-ui);
  color: var(--text);
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
}

.nav__menu-back svg {
  width: 15px;
  height: 15px;
  color: var(--text-mid);
  flex-shrink: 0;
}

.nav__menu-back:hover {
  color: var(--text);
}

.nav__menu-item--check {
  gap: 10px;
}

.nav__check-icon {
  width: 14px !important;
  height: 14px !important;
  color: var(--accent) !important;
  flex-shrink: 0;
}

.nav__check-placeholder {
  display: inline-block;
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.nav__menu-item--checked {
  color: var(--accent);
}

.nav__icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-mid);
  cursor: pointer;
  transition: background 0.12s, color 0.12s, border-color 0.12s;
  flex-shrink: 0;
}

.nav__icon-btn:hover {
  background: var(--surface);
  color: var(--text);
  border-color: var(--text-dim);
}

.nav__icon-btn svg {
  width: 15px;
  height: 15px;
}

.nav__lang-btn {
  font-size: 11px;
  font-weight: 600;
  font-family: var(--font-mono);
  letter-spacing: 0.02em;
}

.nav__backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
}

/* 新增 URL modal */
.add-overlay {
  position: fixed;
  inset: 0;
  z-index: 300;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.add-modal {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
  width: 100%;
  max-width: 540px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: 0 16px 48px rgba(0,0,0,0.18);
}

.add-modal__label {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 0;
}

.add-modal__row {
  display: flex;
  gap: 8px;
}

.add-modal__input {
  flex: 1;
  background: var(--bg);
  border: 1px solid var(--border2);
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 13px;
  color: var(--text);
  font-family: var(--font-ui);
  outline: none;
  transition: border-color .15s ease;
  min-width: 0;
}
.add-modal__input:focus { border-color: var(--accent-bdr); }
.add-modal__input::placeholder { color: var(--text-dim); }
.add-modal__input:disabled { opacity: 0.5; }

.add-modal__error {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 11.5px;
  color: var(--danger);
}

.add-modal__processing {
  display: flex;
  align-items: center;
  gap: 10px;
}

.add-modal__processing-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 6px var(--accent);
  flex-shrink: 0;
  animation: pulse 1.5s ease-in-out infinite;
}

.add-modal__processing-text {
  margin: 0;
  font-family: var(--font-ui);
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
}

.add-modal__hint {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 11.5px;
  color: var(--text-dim);
}

.add-modal__row--end {
  justify-content: flex-end;
}

.add-modal__steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.add-modal__step {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: var(--font-ui);
  font-size: 13px;
  color: var(--text-dim);
  transition: color 0.2s ease;
}

.add-modal__step--active {
  color: var(--text);
  font-weight: 500;
}

.add-modal__step--done {
  color: var(--text-dim);
}

.add-modal__step-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.add-modal__step-icon svg {
  width: 14px;
  height: 14px;
  stroke: var(--accent);
}

.add-modal__step-spinner {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid var(--border2);
  border-top-color: var(--accent);
  animation: spin 0.7s linear infinite;
}

.add-modal__step-idle {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--border2);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.modal-enter-active, .modal-leave-active {
  transition: opacity 0.15s ease;
}
.modal-enter-active .add-modal, .modal-leave-active .add-modal {
  transition: transform 0.15s ease, opacity 0.15s ease;
}
.modal-enter-from, .modal-leave-to {
  opacity: 0;
}
.modal-enter-from .add-modal, .modal-leave-to .add-modal {
  transform: scale(0.96);
  opacity: 0;
}

.menu-enter-active,
.menu-leave-active {
  transition: opacity 0.12s, transform 0.12s;
}

.menu-enter-from,
.menu-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* 通知鈴鐺 */
.nav__notif {
  position: relative;
}

.nav__notif-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-mid);
  cursor: pointer;
  transition: background 0.12s, color 0.12s, border-color 0.12s;
  flex-shrink: 0;
}

.nav__notif-btn:hover {
  background: var(--surface);
  color: var(--text);
  border-color: var(--text-dim);
}

.nav__notif-btn svg {
  width: 15px;
  height: 15px;
}

.nav__notif-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 16px;
  height: 16px;
  padding: 0 3px;
  border-radius: 8px;
  background: var(--accent);
  color: #fff;
  font-size: 9px;
  font-weight: 700;
  font-family: var(--font-mono);
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.nav__notif-panel {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  width: 300px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  z-index: 200;
  overflow: hidden;
}

.nav__notif-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px 8px;
  font-size: 12px;
  font-weight: 600;
  font-family: var(--font-ui);
  color: var(--text);
  border-bottom: 1px solid var(--border);
}

.nav__notif-readall {
  font-size: 11px;
  font-family: var(--font-ui);
  color: var(--accent);
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
}

.nav__notif-readall:hover {
  opacity: 0.8;
}

.nav__notif-list {
  max-height: 320px;
  overflow-y: auto;
  padding: 4px;
}

.nav__notif-empty {
  padding: 20px 14px;
  text-align: center;
  font-size: 12px;
  color: var(--text-dim);
  font-family: var(--font-ui);
}

.nav__notif-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
  transition: background 0.1s;
}

.nav__notif-item:hover {
  background: var(--bg);
}

.nav__notif-item--unread {
  background: color-mix(in srgb, var(--accent) 6%, transparent);
}

.nav__notif-item--unread:hover {
  background: color-mix(in srgb, var(--accent) 10%, transparent);
}

.nav__notif-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 4px;
  background: transparent;
}

.nav__notif-dot--visible {
  background: var(--accent);
}

.nav__notif-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.nav__notif-text {
  font-size: 12.5px;
  font-family: var(--font-ui);
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 220px;
}

.nav__notif-time {
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--text-dim);
}

@media (max-width: 720px) {
  .nav__notif-panel {
    position: fixed;
    top: 56px;
    right: 12px;
    left: auto;
    width: calc(100vw - 24px);
    max-width: 320px;
  }
}

/* 手機版搜尋 icon button */
.nav__search-btn {
  display: none;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 50%;
  color: var(--text-mid);
  cursor: pointer;
  transition: background .12s, color .12s, border-color .12s;
}
.nav__search-btn:hover { background: var(--surface); color: var(--text); border-color: var(--text-dim); }

@media (max-width: 768px) {
  .nav__search-btn { display: flex; }
}

/* 搜尋 modal 內部樣式 */
.search-modal { padding: 16px; max-width: 480px; }

.search-modal__input-row {
  position: relative;
  display: flex;
  align-items: center;
}
.search-modal__icon {
  position: absolute;
  left: 10px;
  color: var(--text-dim);
  flex-shrink: 0;
}
.search-modal__input { padding-left: 34px !important; }

.search-modal__state {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-dim);
  padding: 8px 4px;
}

.search-modal__item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px;
  border-radius: 8px;
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
  transition: background .12s ease;
}
.search-modal__item:hover { background: var(--surface2); }

.search-modal__thumb {
  width: 44px;
  height: 44px;
  border-radius: 6px;
  overflow: hidden;
  flex-shrink: 0;
  background: var(--surface2);
}
.search-modal__thumb img { width: 100%; height: 100%; object-fit: cover; }

.search-modal__info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.search-modal__title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.search-modal__meta {
  font-size: 11px;
  color: var(--text-dim);
}
</style>
