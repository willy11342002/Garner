import React, { useEffect, useRef, useState } from "react"
import { clearStoredSession, getFreshToken, getStoredSession } from "./lib/auth"

const API = process.env.PLASMO_PUBLIC_API_BASE_URL!
const WEB = process.env.PLASMO_PUBLIC_WEB_URL!
const GREEN = "#4effc8"

type Stage =
  | "idle"
  | "fetching_info"
  | "fetching_content"
  | "understanding"
  | "analyzing"
  | "embedding"
  | "validating"
  | "done"
  | "failed"
  | "duplicate"
  | "auth_expired"

const STAGE_LABEL: Record<string, string> = {
  fetching_info: "讀取頁面資訊…",
  fetching_content: "擷取內容…",
  understanding: "解析內容…",
  analyzing: "AI 分析中…",
  embedding: "建立語意索引…",
  validating: "驗證結果…",
}

const STAGE_PROGRESS: Record<string, number> = {
  fetching_info: 15,
  fetching_content: 30,
  understanding: 50,
  analyzing: 65,
  embedding: 85,
  validating: 95,
  done: 100,
}

const PROGRESS_STAGES = new Set([
  "fetching_info", "fetching_content", "understanding",
  "analyzing", "embedding", "validating",
])

// 無法注入 content script 的頁面，不可存入
function isUnsavableUrl(url: string): boolean {
  return (
    !url ||
    url.startsWith("chrome://") ||
    url.startsWith("chrome-extension://") ||
    url.startsWith("about:") ||
    url.startsWith("edge://") ||
    url.startsWith("devtools://")
  )
}

type SaveEntry = {
  key: string   // React key，用 url + timestamp
  url: string
  title: string
  stage: Stage
  item?: any
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

export default function SidePanel() {
  const dark = useTheme()
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null)
  const [authExpired, setAuthExpired] = useState(false)
  const [currentTab, setCurrentTab] = useState<{ url: string; title: string } | null>(null)
  const [entries, setEntries] = useState<SaveEntry[]>([])

  const bg = dark ? "#0a0a0a" : "#ffffff"
  const fg = dark ? "#e8e8e8" : "#111111"
  const cardBg = dark ? "#141414" : "#f4f4f4"
  const subFg = dark ? "#555" : "#888"
  const borderColor = dark ? "#222" : "#e0e0e0"
  const dividerColor = dark ? "#1a1a1a" : "#ebebeb"

  // ── 初始化：讀取登入狀態 ──────────────────────────────────
  useEffect(() => {
    document.body.style.margin = "0"
    document.body.style.padding = "0"
    document.body.style.backgroundColor = bg

    getStoredSession().then((s) => setLoggedIn(!!s))

    chrome.storage.onChanged.addListener((changes) => {
      if ("pat" in changes || "access_token" in changes) {
        getStoredSession().then((s) => setLoggedIn(!!s))
      }
    })
  }, [bg])

  // ── 監聽目前 Tab ──────────────────────────────────────────
  useEffect(() => {
    function updateCurrentTab(tabId?: number) {
      const query = tabId
        ? new Promise<chrome.tabs.Tab[]>((resolve) =>
            chrome.tabs.get(tabId, (t) => resolve([t]))
          )
        : new Promise<chrome.tabs.Tab[]>((resolve) =>
            chrome.tabs.query({ active: true, currentWindow: true }, resolve)
          )
      query.then(([tab]) => {
        if (tab?.url && tab?.title) {
          setCurrentTab({ url: tab.url, title: tab.title })
        } else {
          setCurrentTab(null)
        }
      })
    }

    updateCurrentTab()

    const onActivated = (info: chrome.tabs.TabActiveInfo) => updateCurrentTab(info.tabId)
    const onUpdated = (
      _tabId: number,
      changeInfo: chrome.tabs.TabChangeInfo,
      tab: chrome.tabs.Tab
    ) => {
      if (!tab.active) return
      if (changeInfo.status === "complete" || changeInfo.title || changeInfo.url) {
        setCurrentTab(tab.url && tab.title ? { url: tab.url, title: tab.title } : null)
      }
    }

    chrome.tabs.onActivated.addListener(onActivated)
    chrome.tabs.onUpdated.addListener(onUpdated)
    return () => {
      chrome.tabs.onActivated.removeListener(onActivated)
      chrome.tabs.onUpdated.removeListener(onUpdated)
    }
  }, [])

  // ── 存入邏輯（直接在 Side Panel 做 stream）───────────────
  function updateEntry(key: string, patch: Partial<SaveEntry>) {
    setEntries((prev) =>
      prev.map((e) => (e.key === key ? { ...e, ...patch } : e))
    )
  }

  async function handleSave() {
    if (!currentTab) return
    const { url, title } = currentTab

    const token = await getFreshToken()
    if (!token) {
      setAuthExpired(true)
      return
    }

    const key = `${url}__${Date.now()}`
    const newEntry: SaveEntry = { key, url, title, stage: "fetching_info" }
    setEntries((prev) => [newEntry, ...prev])

    try {
      const createResp = await fetch(`${API}/items/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          "X-Response-Mode": "async",
        },
        body: JSON.stringify({ url }),
      })

      if (createResp.status === 401) {
        setAuthExpired(true)
        updateEntry(key, { stage: "auth_expired" })
        return
      }
      if (createResp.status === 409) {
        updateEntry(key, { stage: "duplicate" })
        return
      }
      if (!createResp.ok) {
        updateEntry(key, { stage: "failed" })
        return
      }

      const item = await createResp.json()
      await streamProgress(key, item.id, token)
    } catch {
      updateEntry(key, { stage: "failed" })
    }
  }

  async function streamProgress(key: string, itemId: string, token: string) {
    try {
      const resp = await fetch(`${API}/items/${itemId}/stream`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!resp.ok || !resp.body) {
        updateEntry(key, { stage: "failed" })
        return
      }

      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""

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
              updateEntry(key, { stage: "done", item: data.item })
              reader.cancel()
              return
            } else if (data.status === "progress") {
              updateEntry(key, { stage: data.stage })
            } else if (data.status === "failed" || data.status === "timeout") {
              updateEntry(key, { stage: "failed" })
              reader.cancel()
              return
            }
          } catch {}
        }
      }
    } catch {
      updateEntry(key, { stage: "failed" })
    }
  }

  // ── 樣式 ─────────────────────────────────────────────────
  const primaryBtn: React.CSSProperties = {
    backgroundColor: GREEN,
    color: "#000",
    border: "none",
    borderRadius: 8,
    padding: "9px 16px",
    fontSize: 13,
    fontWeight: 700,
    cursor: "pointer",
    flexShrink: 0,
  }

  const disabledBtn: React.CSSProperties = {
    ...primaryBtn,
    backgroundColor: dark ? "#1e1e1e" : "#e0e0e0",
    color: subFg,
    cursor: "not-allowed",
  }

  // ── 現在頁面的狀態 ────────────────────────────────────────
  const currentUrlUnsavable = !currentTab || isUnsavableUrl(currentTab.url)
  const currentSaving = currentTab
    ? entries.find(
        (e) => e.url === currentTab.url && PROGRESS_STAGES.has(e.stage)
      )
    : null

  // ── Auth 未登入 / 過期畫面 ────────────────────────────────
  if (loggedIn === null) {
    return (
      <div style={{ ...shell(bg, fg), display: "flex", alignItems: "center", justifyContent: "center" }}>
        <p style={{ color: subFg, fontSize: 13 }}>載入中…</p>
      </div>
    )
  }

  if (!loggedIn || authExpired) {
    return (
      <div style={shell(bg, fg)}>
        <Header dark={dark} GREEN={GREEN} borderColor={borderColor} />
        <div style={{ padding: "24px 16px", display: "flex", flexDirection: "column", gap: 8 }}>
          <p style={{ color: subFg, fontSize: 13, margin: 0 }}>
            {authExpired ? "登入已過期，請重新登入" : "請先在 Garner 網頁版登入"}
          </p>
          <button
            style={{ ...primaryBtn, width: "100%" }}
            onClick={async () => {
              if (authExpired) {
                await clearStoredSession()
                setAuthExpired(false)
                setLoggedIn(false)
              } else {
                chrome.tabs.create({ url: WEB + "/app/connected" })
              }
            }}>
            {authExpired ? "重新登入" : "前往登入"}
          </button>
        </div>
      </div>
    )
  }

  // ── 主畫面 ────────────────────────────────────────────────
  return (
    <div style={shell(bg, fg)}>
      <Header dark={dark} GREEN={GREEN} borderColor={borderColor} />

      {/* 目前頁面 + 存入按鈕 */}
      <div style={{
        padding: "12px 16px",
        borderBottom: `1px solid ${dividerColor}`,
        display: "flex",
        gap: 10,
        alignItems: "center",
      }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          {currentTab ? (
            <>
              <p style={{ margin: 0, fontSize: 13, fontWeight: 500, color: fg, lineHeight: 1.4, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {currentTab.title}
              </p>
              <p style={{ margin: "3px 0 0", fontSize: 11, color: subFg, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {currentTab.url}
              </p>
            </>
          ) : (
            <p style={{ margin: 0, fontSize: 13, color: subFg }}>無法偵測目前頁面</p>
          )}
        </div>
        <button
          style={currentUrlUnsavable || !!currentSaving ? disabledBtn : primaryBtn}
          disabled={currentUrlUnsavable || !!currentSaving}
          onClick={handleSave}>
          {currentSaving ? "處理中…" : "存入"}
        </button>
      </div>

      {/* 清單 */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        {entries.length === 0 ? (
          <p style={{ color: subFg, fontSize: 12, textAlign: "center", padding: "32px 16px", margin: 0 }}>
            尚未存入任何頁面
          </p>
        ) : (
          entries.map((entry) => (
            <EntryRow
              key={entry.key}
              entry={entry}
              dark={dark}
              fg={fg}
              subFg={subFg}
              cardBg={cardBg}
              borderColor={dividerColor}
              GREEN={GREEN}
              onViewItem={(id) => chrome.tabs.create({ url: `${WEB}/app/item/${id}` })}
              onRemove={(key) => setEntries((prev) => prev.filter((e) => e.key !== key))}
            />
          ))
        )}
      </div>
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────

function shell(bg: string, fg: string): React.CSSProperties {
  return {
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    backgroundColor: bg,
    color: fg,
    boxSizing: "border-box",
  }
}

function Header({ dark, GREEN, borderColor }: { dark: boolean; GREEN: string; borderColor: string }) {
  return (
    <div style={{
      padding: "14px 16px 12px",
      borderBottom: `1px solid ${borderColor}`,
      display: "flex",
      alignItems: "center",
    }}>
      <span style={{ fontSize: 16, fontWeight: 700, color: GREEN, letterSpacing: "-0.3px" }}>
        Garner ✦
      </span>
    </div>
  )
}

type EntryRowProps = {
  entry: SaveEntry
  dark: boolean
  fg: string
  subFg: string
  cardBg: string
  borderColor: string
  GREEN: string
  onViewItem: (id: string) => void
  onRemove: (key: string) => void
}

function EntryRow({ entry, dark, fg, subFg, cardBg, borderColor, GREEN, onViewItem, onRemove }: EntryRowProps) {
  const { stage, title, item, key } = entry

  const rowStyle: React.CSSProperties = {
    padding: "12px 16px",
    borderBottom: `1px solid ${borderColor}`,
    display: "flex",
    flexDirection: "column",
    gap: 6,
  }

  const titleStyle: React.CSSProperties = {
    margin: 0,
    fontSize: 13,
    fontWeight: 500,
    color: fg,
    lineHeight: 1.4,
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  }

  const subStyle: React.CSSProperties = { margin: 0, fontSize: 11, color: subFg }

  const smallBtnBase: React.CSSProperties = {
    border: "none",
    borderRadius: 6,
    padding: "5px 10px",
    fontSize: 11,
    cursor: "pointer",
    fontWeight: 600,
  }

  if (PROGRESS_STAGES.has(stage)) {
    return (
      <div style={rowStyle}>
        <p style={titleStyle}>{title}</p>
        <div style={{ backgroundColor: dark ? "#1a1a1a" : "#e8e8e8", borderRadius: 3, height: 3, overflow: "hidden" }}>
          <div style={{
            backgroundColor: GREEN, height: "100%", borderRadius: 3,
            transition: "width 0.6s ease", width: `${STAGE_PROGRESS[stage] ?? 10}%`,
          }} />
        </div>
        <p style={{ ...subStyle, color: subFg }}>{STAGE_LABEL[stage] ?? "處理中…"}</p>
      </div>
    )
  }

  if (stage === "done") {
    const displayTitle = item?.title || title
    return (
      <div style={rowStyle}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
          <span style={{ color: GREEN, fontSize: 14, marginTop: 1, flexShrink: 0 }}>✓</span>
          <p style={titleStyle}>{displayTitle}</p>
        </div>
        {item?.tags?.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
            {item.tags.slice(0, 4).map((t: any) => (
              <span key={t.id} style={{ backgroundColor: cardBg, color: subFg, borderRadius: 4, padding: "2px 7px", fontSize: 10 }}>
                {t.name}
              </span>
            ))}
          </div>
        )}
        <div style={{ display: "flex", gap: 6, flexWrap: "nowrap" }}>
          <button
            style={{ ...smallBtnBase, backgroundColor: GREEN, color: "#000", whiteSpace: "nowrap" }}
            onClick={() => onViewItem(item.id)}>
            查看 →
          </button>
          <button
            style={{ ...smallBtnBase, backgroundColor: dark ? "#1e1e1e" : "#ebebeb", color: subFg, whiteSpace: "nowrap" }}
            onClick={() => onRemove(key)}>
            關閉
          </button>
        </div>
      </div>
    )
  }

  if (stage === "duplicate") {
    return (
      <div style={rowStyle}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
          <span style={{ color: subFg, fontSize: 14, flexShrink: 0 }}>—</span>
          <p style={{ ...titleStyle, color: subFg }}>{title}</p>
        </div>
        <p style={subStyle}>已存在於知識庫</p>
        <button
          style={{ ...smallBtnBase, backgroundColor: dark ? "#1e1e1e" : "#ebebeb", color: subFg, alignSelf: "flex-start" }}
          onClick={() => onRemove(key)}>
          關閉
        </button>
      </div>
    )
  }

  if (stage === "failed" || stage === "auth_expired") {
    return (
      <div style={rowStyle}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
          <span style={{ color: "#f87171", fontSize: 14, flexShrink: 0 }}>✕</span>
          <p style={{ ...titleStyle, color: "#f87171" }}>{title}</p>
        </div>
        <p style={subStyle}>{stage === "auth_expired" ? "登入已過期" : "處理失敗"}</p>
        <button
          style={{ ...smallBtnBase, backgroundColor: dark ? "#1e1e1e" : "#ebebeb", color: subFg, alignSelf: "flex-start" }}
          onClick={() => onRemove(key)}>
          關閉
        </button>
      </div>
    )
  }

  return null
}
