// @ts-check
// ESLint 9+ flat config。規則本體由 @nuxt/eslint 在 `nuxt prepare` 時產生到
// .nuxt/eslint.config.mjs，這裡只負責接上去並做專案層級的覆寫。
//
// 因此 package.json 的 postinstall 必須跑 `nuxt prepare`，否則乾淨環境
// （CI / Docker）install 完直接 lint 會找不到 ./.nuxt/eslint.config.mjs。
import withNuxt from './.nuxt/eslint.config.mjs'

export default withNuxt(
  {
    name: 'garner/ignores',
    ignores: ['.nuxt/**', '.output/**', '.vercel/**', 'dist/**', 'public/**'],
  },
  {
    name: 'garner/vue3-not-vue2',
    rules: {
      // 以下三條是 eslint-plugin-vue 的 **Vue 2** 規則，被 @nuxt/eslint-config
      // 一併打開了。本專案是 Vue 3，三條全部誤報，逐條驗證過：
      //
      // - no-multiple-template-root：Vue 3 支援 fragment，多個根節點是合法的
      //   （archive / chat / index / reports / settings 五頁都是這樣寫）。
      // - valid-template-root：pages/app/item/[slug].vue 是純轉址頁，
      //   邏輯全在 definePageMeta 的 middleware，空 template 是刻意的。
      // - no-deprecated-filter：誤把 template 內的 TS union 型別斷言
      //   （`quota?.plan as 'free' | 'pro' | undefined`）當成 Vue 2 的 filter 語法。
      'vue/no-multiple-template-root': 'off',
      'vue/valid-template-root': 'off',
      'vue/no-deprecated-filter': 'off',
    },
  },
  {
    name: 'garner/formatting',
    rules: {
      // 這條規則的 autofix 會把第一個屬性換行後放在第 0 欄（因為沒同時開 html-indent），
      // 結果比原本更難讀。純排版議題，關掉。
      'vue/first-attribute-linebreak': 'off',
    },
  },
  {
    name: 'garner/legacy-baseline',
    rules: {
      // 這個 codebase 到 2026-08 才第一次真的跑 lint（在那之前 `pnpm lint`
      // 因為缺 eslint.config.mjs 直接 exit 2）。存量的 30 處 `any` 集中在
      // types/api.ts 與 chat SSE 的事件負載，逐一補型別是獨立工作，
      // 先降成 warn 讓 CI 能守住「新增的錯誤」，存量另案清。
      '@typescript-eslint/no-explicit-any': 'warn',
    },
  },
)
