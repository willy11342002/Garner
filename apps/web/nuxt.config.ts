export default defineNuxtConfig({
  compatibilityDate: '2024-11-01',
  devtools: { enabled: false },

  app: {
    head: {
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
      ],
    },
  },

  css: [
    '~/assets/css/vela.css',
    '~/assets/css/selbar.css',
    '~/assets/css/home.css',
    '~/assets/css/archive.css',
    '~/assets/css/item-detail.css',
    '~/assets/css/tag.css',
    '~/assets/css/collection-view.css',
  ],

  modules: ['@nuxtjs/supabase', '@pinia/nuxt', '@nuxtjs/i18n'],

  routeRules: {
    '/explore/**': { ssr: true },
    '/share/**': { ssr: true },
    '/app/**': { ssr: false },
    '/app/explore': { redirect: '/app/explore/surprise' },
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