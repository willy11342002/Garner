<template>
  <main class="login">
    <div class="login__card">
      <h1 class="login__logo">Vela</h1>
      <p class="login__sub">被動建立的個人知識庫</p>

      <div class="login__actions">
        <button class="btn btn--oauth" :disabled="loading" @click="signIn('google')">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
            <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z" fill="#34A853"/>
            <path d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
            <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
          </svg>
          使用 Google 登入
        </button>

        <button class="btn btn--oauth" :disabled="loading" @click="signIn('github')">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/>
          </svg>
          使用 GitHub 登入
        </button>
      </div>

      <p v-if="error" class="login__error">{{ error }}</p>
    </div>
  </main>
</template>

<script setup lang="ts">
definePageMeta({ layout: false })

const client = useSupabaseClient()
const user = useSupabaseUser()
const loading = ref(false)
const error = ref('')

if (user.value) {
  await navigateTo('/app')
}

watch(user, (u) => {
  if (u) navigateTo('/app')
})

async function signIn(provider: 'google' | 'github') {
  loading.value = true
  error.value = ''
  const { error: err } = await client.auth.signInWithOAuth({
    provider,
    options: { redirectTo: `${window.location.origin}/confirm` },
  })
  if (err) {
    error.value = err.message
    loading.value = false
  }
}
</script>

<style scoped>
.login {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.login__card {
  width: 100%;
  max-width: 360px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 40px 32px;
  text-align: center;
}

.login__logo {
  font-family: var(--font-brand);
  font-size: 32px;
  font-weight: 700;
  letter-spacing: -0.03em;
  margin: 0 0 8px;
}

.login__sub {
  font-size: 13px;
  color: var(--text-mid);
  margin: 0 0 32px;
}

.login__actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.btn--oauth {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  padding: 11px 16px;
  font-size: 14px;
  font-family: var(--font-ui);
  font-weight: 500;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  color: var(--text);
}

.btn--oauth:hover:not(:disabled) {
  border-color: var(--text-mid);
  background: var(--surface);
}

.btn--oauth:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.login__error {
  margin: 16px 0 0;
  font-size: 12px;
  color: #e85555;
}
</style>
