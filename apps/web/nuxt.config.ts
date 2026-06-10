export default defineNuxtConfig({
  compatibilityDate: '2024-11-01',
  devtools: { enabled: false },

  nitro: {
    preset: 'vercel',
  },

  app: {
    head: {
      title: 'Garner',
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'google-site-verification', content: 'mn4FALR8YfPLHEDiknxZhOmqff6_ArRkz3m73epDvow' },
      ],
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
      ],
    },
  },

  css: [
    '~/assets/css/garner.css',
    '~/assets/css/selbar.css',
    '~/assets/css/home.css',
    '~/assets/css/archive.css',
    '~/assets/css/item-detail.css',
    '~/assets/css/tag.css',
    '~/assets/css/collection-view.css',
    '~/assets/css/chat.css',
  ],

  modules: ['@nuxtjs/supabase', '@pinia/nuxt', '@nuxtjs/i18n'],

  routeRules: {
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
      cookieKey: 'garner-locale',
      alwaysRedirect: false,
    },
  },
})