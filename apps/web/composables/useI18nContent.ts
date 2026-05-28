export const useI18nContent = () => {
  const { locale } = useI18n()

  function localize(
    i18n: Record<string, string> | null | undefined,
    fallback: string | null | undefined,
  ): string | null {
    if (i18n) {
      return i18n[locale.value] ?? i18n['zh-TW'] ?? i18n['en'] ?? fallback ?? null
    }
    return fallback ?? null
  }

  return { localize }
}
