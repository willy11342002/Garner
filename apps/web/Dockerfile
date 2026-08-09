FROM node:22-alpine AS builder
# 只 enable，不指定版本：pnpm 版本由 package.json 的 packageManager 欄位決定。
# 原本是 corepack prepare pnpm@latest，等於每次建置抓當下最新版，行為會飄。
RUN corepack enable
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
WORKDIR /app
# pnpm-workspace.yaml 一定要一起複製：onlyBuiltDependencies 設定在裡面，
# 少了它 install 會以 ERR_PNPM_IGNORED_BUILDS 中止。
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
# nuxt.config.ts 釘的是 preset: 'vercel'（生產走 Vercel），那會產出 .vercel/output，
# 而這個映像要的是 .output。用 NITRO_PRESET 在建置時覆寫，不動 nuxt.config.ts。
ENV NITRO_PRESET=node-server
RUN pnpm build

FROM node:22-alpine
WORKDIR /app
COPY --from=builder /app/.output ./.output
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
