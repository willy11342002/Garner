export default defineNuxtConfig({
  compatibilityDate: '2024-11-01',
  devtools: { enabled: false },

  css: ['~/assets/css/vela.css'],

  modules: ['@nuxtjs/supabase', '@pinia/nuxt', '@nuxtjs/i18n'],

  routeRules: {
    '/explore/**': { ssr: true },
    '/share/**': { ssr: true },
    '/app/**': { ssr: false },
  },

  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE ?? 'http://localhost:8000',
    },
  },

  supabase: {
    redirect: false,
  },

  i18n: {
    strategy: 'no_prefix',
    defaultLocale: 'zh-TW',
    locales: [
      { code: 'zh-TW', name: '繁體中文', file: 'zh-TW.json' },
      { code: 'en', name: 'English', file: 'en.json' },
    ],
    detectBrowserLanguage: {
      useCookie: true,
      cookieKey: 'vela-locale',
      alwaysRedirect: false,
    },
  },
})