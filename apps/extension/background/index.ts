export {}

const API = process.env.PLASMO_PUBLIC_API_BASE_URL!

async function getPat(): Promise<string | null> {
  const data = await chrome.storage.local.get("pat")
  return data["pat"] ?? null
}

async function saveItem(url: string, title: string) {
  const token = await getPat()
  if (!token) {
    await chrome.storage.local.set({ saveStage: "auth_expired" })
    return
  }

  await chrome.storage.local.set({
    saveStage: "fetching_info",
    savedItem: null,
    saveUrl: url,
    saveTitle: title,
  })

  try {
    const createResp = await fetch(`${API}/items/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, "X-Response-Mode": "async" },
      body: JSON.stringify({ url }),
    })
    if (createResp.status === 401) {
      await chrome.storage.local.set({ saveStage: "auth_expired" })
      return
    }
    if (!createResp.ok) {
      await chrome.storage.local.set({ saveStage: "failed" })
      return
    }
    const item = await createResp.json()
    await streamProgress(item.id, token)
  } catch {
    await chrome.storage.local.set({ saveStage: "failed" })
  }
}

async function streamProgress(itemId: string, token: string) {
  const resp = await fetch(`${API}/items/${itemId}/stream`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!resp.ok || !resp.body) {
    await chrome.storage.local.set({ saveStage: "failed" })
    return
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split("\n")
      buffer = lines.pop() ?? ""
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue
        try {
          const data = JSON.parse(line.slice(6))
          if (data.status === "done") {
            await chrome.storage.local.set({ saveStage: "done", savedItem: data.item })
            reader.cancel()
            return
          } else if (data.status === "progress") {
            await chrome.storage.local.set({ saveStage: data.stage })
          } else if (data.status === "failed" || data.status === "timeout") {
            await chrome.storage.local.set({ saveStage: "failed" })
            reader.cancel()
            return
          }
        } catch {}
      }
    }
  } catch {
    await chrome.storage.local.set({ saveStage: "failed" })
  }
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "SAVE_ITEM") {
    saveItem(msg.url, msg.title)
    sendResponse({ ok: true })
  }
})

chrome.runtime.onInstalled.addListener(() => {
  console.log("Garner extension installed")
})
