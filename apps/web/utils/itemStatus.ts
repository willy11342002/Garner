import type { Item } from '~/types/api'

const STALL_THRESHOLD_MS = 5 * 60 * 1000

/** Item's ingest pipeline hasn't been touched in 5+ minutes and never
 * finished — likely means the API process died mid-run. Resumable via
 * POST /items/{id}/resume (LangGraph checkpoint resume). */
export function isStalled(item: Item): boolean {
  if (item.parsed_at) return false
  if (!item.updated_at) return false
  return Date.now() - new Date(item.updated_at).getTime() > STALL_THRESHOLD_MS
}

/** A pipeline stage exhausted its retries and recorded an error. Also
 * resumable via POST /items/{id}/resume — it re-attempts from that stage. */
export function isFailed(item: Item): boolean {
  return [item.fetch_status, item.assets_status, item.note_status, item.embedding_status, item.landmarks_status]
    .some(s => s === 'error')
}

export function needsRetry(item: Item): boolean {
  return isStalled(item) || isFailed(item)
}
