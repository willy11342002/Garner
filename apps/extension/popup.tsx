import { useState } from "react"

type Status = "idle" | "loading" | "success" | "error"

export default function Popup() {
  const [status, setStatus] = useState<Status>("idle")

  async function save() {
    setStatus("loading")
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
      const resp = await fetch(`${process.env.PLASMO_PUBLIC_API_BASE_URL}/items/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: tab.url, title: tab.title }),
      })
      setStatus(resp.ok ? "success" : "error")
    } catch {
      setStatus("error")
    }
  }

  return (
    <div style={{ width: 280, padding: 16, fontFamily: "sans-serif" }}>
      <h2 style={{ margin: "0 0 12px" }}>Vela</h2>
      {status === "idle" && <button onClick={save}>Save to Vela</button>}
      {status === "loading" && <p>Saving…</p>}
      {status === "success" && <p>Saved!</p>}
      {status === "error" && <p>Failed. Try again.</p>}
    </div>
  )
}
