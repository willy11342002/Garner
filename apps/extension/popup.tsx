import React, { useEffect, useState } from "react"
import { clearStoredSession, getFreshToken, getStoredSession } from "./lib/auth"

const API = process.env.PLASMO_PUBLIC_API_BASE_URL!
const WEB = process.env.PLASMO_PUBLIC_WEB_URL!
const GREEN = "#4effc8"

type Stage =
  | "idle"
  | "fetching_info"
  | "fetching_content"
  | "analyzing"
  | "embedding"
  | "done"
  | "failed"
  | "auth_expired"

const STAGE_LABEL: Record<string, string> = {
  fetching_info: "讀取頁面資訊…",
  fetching_content: "擷取內容…",
  analyzing: "AI 分析中…",
  embedding: "建立語意索引…",
}

const STAGE_PROGRESS: Record<string, number> = {
  fetching_info: 15,
  fetching_content: 35,
  analyzing: 60,
  embedding: 85,
  done: 100,
}

function useTheme() {
  const [dark, setDark] = useState(() =>
    window.matchMedia("(prefers-color-scheme: dark)").matches
  )
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)")
    const handler = (e: MediaQueryListEvent) => setDark(e.matches)
    mq.addEventListener("change", handler)
    return () => mq.removeEventListener("change", handler)
  }, [])
  return dark
}

export default function Popup() {
  const dark = useTheme()
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null)
  const [stage, setStage] = useState<Stage>("idle")
  const [savedItem, setSavedItem] = useState<any>(null)
  const [currentTab, setCurrentTab] = useState<{ url: string; title: string } | null>(null)

  const bg = dark ? "#0a0a0a" : "#ffffff"
  const fg = dark ? "#e8e8e8" : "#111111"
  const cardBg = dark ? "#141414" : "#f4f4f4"
  const subFg = dark ? "#555" : "#888"
  const borderColor = dark ? "#222" : "#e0e0e0"

  // 消除外框：讓 body 背景色跟 popup 一致
  useEffect(() => {
    document.body.style.margin = "0"
    document.body.style.padding = "0"
    document.body.style.backgroundColor = bg
  }, [bg])

  useEffect(() => {
    chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
      if (tab?.url && tab?.title) setCurrentTab({ url: tab.url, title: tab.title })
    })
    getStoredSession().then((s) => setLoggedIn(!!s))
  }, [])

  async function handleSave() {
    if (!currentTab) return
    const token = await getFreshToken()
    if (!token) { setStage("auth_expired"); return }

    setStage("fetching_info")
    setSavedItem(null)

    try {
      const createResp = await fetch(`${API}/items/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ url: currentTab.url }),
      })
      if (!createResp.ok) { setStage("failed"); return }
      const item = await createResp.json()
      await streamProgress(item.id, token)
    } catch {
      setStage("failed")
    }
  }

  async function streamProgress(itemId: string, token: string) {
    const resp = await fetch(`${API}/items/${itemId}/stream`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!resp.ok || !resp.body) { setStage("failed"); return }

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
              setSavedItem(data.item); setStage("done"); reader.cancel(); return
            } else if (data.status === "progress") {
              setStage(data.stage as Stage)
            } else if (data.status === "failed" || data.status === "timeout") {
              setStage("failed"); reader.cancel(); return
            }
          } catch {}
        }
      }
    } catch {
      setStage("failed")
    }
  }

  function openGarner(path = "") {
    chrome.tabs.create({ url: WEB + path })
  }

  const primaryBtn: React.CSSProperties = {
    backgroundColor: GREEN,
    color: "#000",
    border: "none",
    borderRadius: 8,
    padding: "10px 16px",
    fontSize: 13,
    fontWeight: 700,
    cursor: "pointer",
    width: "100%",
  }

  const secondaryBtn: React.CSSProperties = {
    backgroundColor: "transparent",
    color: subFg,
    border: `1px solid ${borderColor}`,
    borderRadius: 8,
    padding: "8px 16px",
    fontSize: 12,
    cursor: "pointer",
    width: "100%",
  }

  function renderContent() {
    if (loggedIn === null) {
      return <p style={{ color: subFg, fontSize: 13, margin: 0 }}>載入中…</p>
    }

    if (!loggedIn) {
      return (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <p style={{ color: subFg, fontSize: 13, margin: "0 0 4px" }}>請先在 Garner 網頁版登入</p>
          <button style={primaryBtn} onClick={() => openGarner()}>前往登入</button>
        </div>
      )
    }

    if (stage === "auth_expired") {
      return (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <p style={{ color: subFg, fontSize: 13, margin: "0 0 4px" }}>登入已過期，請重新登入</p>
          <button style={primaryBtn} onClick={async () => {
            await clearStoredSession()
            setLoggedIn(false)
            setStage("idle")
            openGarner()
          }}>重新登入</button>
        </div>
      )
    }

    if (stage === "idle") {
      return (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {currentTab && (
            <div style={{ backgroundColor: cardBg, borderRadius: 8, padding: "10px 12px", marginBottom: 2 }}>
              <p style={{ margin: 0, fontSize: 13, fontWeight: 500, color: fg, lineHeight: 1.4 }} title={currentTab.title}>
                {currentTab.title.length > 52 ? currentTab.title.slice(0, 49) + "…" : currentTab.title}
              </p>
              <p style={{ margin: "4px 0 0", fontSize: 11, color: subFg }}>{new URL(currentTab.url).hostname}</p>
            </div>
          )}
          <button style={primaryBtn} onClick={handleSave}>儲存到 Garner</button>
        </div>
      )
    }

    if (stage === "done") {
      return (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{
            width: 36, height: 36, borderRadius: "50%",
            backgroundColor: dark ? "#0a2a1a" : "#e6fff8",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 16, color: GREEN, margin: "0 auto 4px",
          }}>✓</div>
          <p style={{ textAlign: "center", fontSize: 14, fontWeight: 600, margin: 0, color: fg }}>已儲存！</p>
          {savedItem?.title && (
            <p style={{ fontSize: 12, color: subFg, textAlign: "center", margin: 0, lineHeight: 1.4 }}>
              {savedItem.title.length > 52 ? savedItem.title.slice(0, 49) + "…" : savedItem.title}
            </p>
          )}
          {savedItem?.tags?.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4, justifyContent: "center", marginBottom: 2 }}>
              {savedItem.tags.slice(0, 5).map((t: any) => (
                <span key={t.id} style={{ backgroundColor: cardBg, color: subFg, borderRadius: 4, padding: "2px 8px", fontSize: 11 }}>
                  {t.name}
                </span>
              ))}
            </div>
          )}
          <button style={primaryBtn} onClick={() => openGarner(`/app/item/${savedItem.id}`)}>在 Garner 查看 →</button>
          <button style={secondaryBtn} onClick={() => { setStage("idle"); setSavedItem(null) }}>再存一頁</button>
        </div>
      )
    }

    if (stage === "failed") {
      return (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <p style={{ color: "#f87171", fontSize: 13, margin: "0 0 4px", textAlign: "center" }}>處理失敗，請稍後再試</p>
          <button style={primaryBtn} onClick={() => setStage("idle")}>重試</button>
        </div>
      )
    }

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <div style={{ backgroundColor: cardBg, borderRadius: 4, height: 3, overflow: "hidden", marginBottom: 2 }}>
          <div style={{
            backgroundColor: GREEN, height: "100%", borderRadius: 4,
            transition: "width 0.6s ease", width: `${STAGE_PROGRESS[stage] ?? 10}%`,
          }} />
        </div>
        <p style={{ color: subFg, fontSize: 12, margin: 0, textAlign: "center" }}>
          {STAGE_LABEL[stage] ?? "處理中…"}
        </p>
      </div>
    )
  }

  return (
    <div style={{
      width: 300,
      padding: "16px",
      fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      backgroundColor: bg,
      color: fg,
      minHeight: 120,
      boxSizing: "border-box",
    }}>
      <div style={{ display: "flex", alignItems: "center", marginBottom: 14 }}>
        <span style={{ fontSize: 17, fontWeight: 700, color: GREEN, letterSpacing: "-0.3px" }}>
          Garner ✦
        </span>
      </div>
      {renderContent()}
    </div>
  )
}
