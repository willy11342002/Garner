<template>
  <main class="login">
    <div class="login__card">
      <p class="login__sub">{{ t('confirm.verifying') }}</p>
    </div>
  </main>
</template>

<script setup lang="ts">
definePageMeta({ layout: false })
useHead({ title: 'Garner — 登入中' })

const { t } = useI18n()
const route = useRoute()
const client = useSupabaseClient()

const code = route.query.code as string | undefined

if (code) {
  const { error } = await client.auth.exchangeCodeForSession(code)
  if (error) {
    await navigateTo('/login')
  } else {
    await navigateTo('/app')
  }
} else {
  await navigateTo('/login')
}
</script>
