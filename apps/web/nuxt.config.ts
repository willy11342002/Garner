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
        { name: 'viewport', content: 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no' },
        { name: 'google-site-verification', content: 'mn4FALR8YfPLHEDiknxZhOmqff6_ArRkz3m73epDvow' },
      ],
      link: [
        { rel: 'icon', type: 'image/png', href: '/favicon.png' },
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
    '~/assets/css/chat.css',
  ],

  modules: ['@nuxtjs/supabase', '@pinia/nuxt', '@nuxtjs/i18n', '@vite-pwa/nuxt'],

  pwa: {
    registerType: 'autoUpdate',
    manifest: {
      name: 'Garner',
      short_name: 'Garner',
      description: '被動建立的個人知識庫',
      theme_color: '#1a1a1a',
      background_color: '#1a1a1a',
      display: 'standalone',
      orientation: 'portrait',
      scope: '/',
      start_url: '/app',
      icons: [
        { src: '/icons/pwa-192x192.png', sizes: '192x192', type: 'image/png' },
        { src: '/icons/pwa-512x512.png', sizes: '512x512', type: 'image/png' },
        { src: '/icons/pwa-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
      ],
    },
    workbox: {
      navigateFallback: null,
      globPatterns: ['**/*.{js,css,html,png,svg,ico,woff,woff2}'],
      runtimeCaching: [
        {
          urlPattern: /^https:\/\/fonts\.(googleapis|gstatic)\.com\/.*/i,
          handler: 'CacheFirst',
          options: { cacheName: 'google-fonts', expiration: { maxEntries: 10, maxAgeSeconds: 60 * 60 * 24 * 365 } },
        },
        // Items list: GET /items/?page=...
        {
          urlPattern: /\/items\/(?:\?|$)/,
          handler: 'NetworkFirst',
          options: {
            cacheName: 'api-items-list',
            networkTimeoutSeconds: 5,
            expiration: { maxEntries: 50, maxAgeSeconds: 60 * 60 * 24 * 7 },
            cacheableResponse: { statuses: [0, 200] },
          },
        },
        // Item detail: GET /items/{id}
        {
          urlPattern: /\/items\/[\w-]+$/,
          handler: 'NetworkFirst',
          options: {
            cacheName: 'api-items-detail',
            networkTimeoutSeconds: 5,
            expiration: { maxEntries: 200, maxAgeSeconds: 60 * 60 * 24 * 7 },
            cacheableResponse: { statuses: [0, 200] },
          },
        },
        // Tags list: GET /tags/
        {
          urlPattern: /\/tags\/(?:\?|$)/,
          handler: 'NetworkFirst',
          options: {
            cacheName: 'api-tags',
            networkTimeoutSeconds: 5,
            expiration: { maxEntries: 10, maxAgeSeconds: 60 * 60 * 24 * 7 },
            cacheableResponse: { statuses: [0, 200] },
          },
        },
      ],
    },
    devOptions: {
      enabled: false,
    },
  },

  routeRules: {
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