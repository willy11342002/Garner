export function stripMarkdown(md: string, maxLength = 120): string {
  return md
    .split('\n')
    .map(line => line
      .replace(/^#{1,6}\s+/, '')   // headings
      .replace(/^[-*]\s+/, '')     // bullet points
      .replace(/\*\*(.*?)\*\*/g, '$1') // bold
      .replace(/\*(.*?)\*/g, '$1')     // italic
      .trim()
    )
    .filter(Boolean)
    .join(' ')
    .slice(0, maxLength)
}
