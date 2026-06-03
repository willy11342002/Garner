export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  console.error('[error.vue]', JSON.stringify(body))
  return { ok: true }
})
