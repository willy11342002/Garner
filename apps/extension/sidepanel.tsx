import React, { useEffect, useState } from "react"
import { clearStoredSession, getFreshToken, getStoredSession } from "./lib/auth"

const API = process.env.PLASMO_PUBLIC_API_BASE_URL!
const WEB = process.env.PLASMO_PUBLIC_WEB_URL!
const GREEN = "#4effc8"

// ── 翻譯 ─────────────────────────────────────────────────
const T = {
  zh: {
    loading: "載入中…",
    loginPrompt: "請先在 Garner 網頁版登入",
    authExpired: "登入已過期，請重新登入",
    goLogin: "前往登入",
    reLogin: "重新登入",
    capture: "擷取",
    currentTab: "目前分頁",
    pasteUrl: "貼上網址",
    currentTabLabel: "目前分頁",
    redetect: "重新偵測",
    noTab: "無法偵測目前頁面",
    saveBtn: "存入目前分頁",
    saving: "處理中…",
    pasteLabel: "輸入或貼上任意網址",
    pastePlaceholder: "https://...",
    recentlySaved: "最近存入",
    savedBadge: "已存入",
    justNow: "剛剛",
    dismiss: "關閉",
    view: "查看 →",
    alreadyExists: "已存在於知識庫",
    failed: "處理失敗",
    authExpiredShort: "登入已過期",
    quotaExceeded: "本月存入次數已達上限",
    aiCredits: (n: number) => `本月剩餘 ${n} 次 AI`,
    saved: (n: number) => `${n.toLocaleString()} 篇`,
    stageLabel: {
      fetch:      "取得資料…",
      assets:     "讀取媒體…",
      note:       "AI 分析筆記…",
      landmarks:  "解析地標…",
      embedding:  "建立語意索引…",
    },
  },
  en: {
    loading: "Loading…",
    loginPrompt: "Please log in to Garner first",
    authExpired: "Session expired, please log in again",
    goLogin: "Go to Login",
    reLogin: "Log in again",
    capture: "CAPTURE",
    currentTab: "Current Tab",
    pasteUrl: "Paste URL",
    currentTabLabel: "CURRENT TAB",
    redetect: "Re-detect",
    noTab: "Cannot detect current page",
    saveBtn: "Save current tab",
    saving: "Saving…",
    pasteLabel: "ENTER OR PASTE ANY URL",
    pastePlaceholder: "https://...",
    recentlySaved: "RECENTLY SAVED",
    savedBadge: "Saved",
    justNow: "just now",
    dismiss: "Dismiss",
    view: "View →",
    alreadyExists: "Already in your library",
    failed: "Processing failed",
    authExpiredShort: "Session expired",
    quotaExceeded: "Monthly save limit reached",
    aiCredits: (n: number) => `${n} AI credits left this month`,
    saved: (n: number) => `${n.toLocaleString()} saved`,
    stageLabel: {
      fetch:      "Fetching data…",
      assets:     "Loading media…",
      note:       "AI analyzing…",
      landmarks:  "Resolving locations…",
      embedding:  "Building index…",
    },
  },
} as const

type Lang = "zh" | "en"

// ── Types ─────────────────────────────────────────────────
type Stage =
  | "idle" | "fetch" | "assets" | "note" | "landmarks" | "embedding"
  | "done" | "failed" | "duplicate" | "auth_expired" | "quota_exceeded"

const STAGE_PROGRESS: Record<string, number> = {
  fetch: 10, assets: 30, note: 55, landmarks: 70, embedding: 85, done: 100,
}

const PROGRESS_STAGES = new Set([
  "fetch", "assets", "note", "landmarks", "embedding",
])

type SaveEntry = { key: string; url: string; title: string; stage: Stage; item?: any }

function isUnsavableUrl(url: string): boolean {
  return !url || ["chrome://", "chrome-extension://", "about:", "edge://", "devtools://"]
    .some((p) => url.startsWith(p))
}

// ── Main Component ────────────────────────────────────────
export default function SidePanel() {
  const [dark, setDark] = useState(false)
  const [lang, setLang] = useState<Lang>("zh")
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null)
  const [authExpired, setAuthExpired] = useState(false)
  const [currentTab, setCurrentTab] = useState<{ url: string; title: string } | null>(null)
  const [entries, setEntries] = useState<SaveEntry[]>([])
  const [entriesLoaded, setEntriesLoaded] = useState(false)
  const [activeTab, setActiveTab] = useState<"current" | "paste">("current")
  const [pasteUrl, setPasteUrl] = useState("")
  const [itemCount, setItemCount] = useState<number | null>(null)
  const [aiCredits, setAiCredits] = useState<number | null>(null)

  const t = T[lang]

  // 初始化深色模式（用 useEffect 確保 window 已 ready）
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)")
    setDark(mq.matches)
  }, [])

  // 從 storage 還原 entries，進行中的標為失敗（stream 已斷）
  useEffect(() => {
    chrome.storage.local.get("sidepanel_entries", (result) => {
      if (result.sidepanel_entries) {
        const restored: SaveEntry[] = result.sidepanel_entries.map((e: SaveEntry) =>
          PROGRESS_STAGES.has(e.stage) ? { ...e, stage: "failed" as Stage } : e
        )
        setEntries(restored)
      }
      setEntriesLoaded(true)
    })
  }, [])

  // entries 變動時同步寫入 storage（只在載入後才寫，避免初始空陣列覆蓋）
  useEffect(() => {
    if (!entriesLoaded) return
    chrome.storage.local.set({ sidepanel_entries: entries.slice(0, 20) })
  }, [entries, entriesLoaded])

  // 套用背景色到 body（讓整個 panel 背景一致）
  const bg = dark ? "#0a0a0a" : "#ffffff"
  useEffect(() => {
    document.body.style.margin = "0"
    document.body.style.padding = "0"
    document.body.style.backgroundColor = bg
  }, [bg])

  const fg = dark ? "#e8e8e8" : "#111111"
  const cardBg = dark ? "#141414" : "#f4f4f4"
  const subFg = dark ? "#666" : "#888"
  const borderColor = dark ? "#1e1e1e" : "#e0e0e0"
  const tabBg = dark ? "#111" : "#f0f0f0"
  const tabActiveBg = dark ? "#1e1e1e" : "#ffffff"
  const inputBg = dark ? "#111" : "#f7f7f7"

  useEffect(() => {
    getStoredSession().then((s) => setLoggedIn(!!s))
    chrome.storage.onChanged.addListener((changes) => {
      if ("pat" in changes || "access_token" in changes)
        getStoredSession().then((s) => setLoggedIn(!!s))
    })
  }, [])

  useEffect(() => {
    function updateCurrentTab(tabId?: number) {
      const query = tabId
        ? new Promise<chrome.tabs.Tab[]>((r) => chrome.tabs.get(tabId, (t) => r([t])))
        : new Promise<chrome.tabs.Tab[]>((r) => chrome.tabs.query({ active: true, currentWindow: true }, r))
      query.then(([tab]) =>
        setCurrentTab(tab?.url && tab?.title ? { url: tab.url, title: tab.title } : null)
      )
    }
    updateCurrentTab()
    const onActivated = (info: chrome.tabs.TabActiveInfo) => updateCurrentTab(info.tabId)
    const onUpdated = (_id: number, change: chrome.tabs.TabChangeInfo, tab: chrome.tabs.Tab) => {
      if (!tab.active) return
      if (change.status === "complete" || change.title || change.url)
        setCurrentTab(tab.url && tab.title ? { url: tab.url, title: tab.title } : null)
    }
    chrome.tabs.onActivated.addListener(onActivated)
    chrome.tabs.onUpdated.addListener(onUpdated)
    return () => {
      chrome.tabs.onActivated.removeListener(onActivated)
      chrome.tabs.onUpdated.removeListener(onUpdated)
    }
  }, [])

  useEffect(() => {
    async function loadStats() {
      const token = await getFreshToken()
      if (!token) return
      try {
        const r = await fetch(`${API}/quota/me`, { headers: { Authorization: `Bearer ${token}` } })
        if (r.ok) {
          const d = await r.json()
          setItemCount(d.saves?.used ?? null)
          setAiCredits(d.chat?.limit !== null ? (d.chat.limit - d.chat.used) : null)
        }
      } catch {}
    }
    loadStats()
  }, [loggedIn])

  function updateEntry(key: string, patch: Partial<SaveEntry>) {
    setEntries((prev) => prev.map((e) => (e.key === key ? { ...e, ...patch } : e)))
  }

  async function handleSave(url: string, title: string) {
    const token = await getFreshToken()
    if (!token) { setAuthExpired(true); return }
    const key = `${url}__${Date.now()}`
    setEntries((prev) => [{ key, url, title, stage: "fetch" }, ...prev])
    if (activeTab === "paste") setPasteUrl("")
    try {
      const resp = await fetch(`${API}/items/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, "X-Response-Mode": "async" },
        body: JSON.stringify({ url }),
      })
      if (resp.status === 401) { setAuthExpired(true); updateEntry(key, { stage: "auth_expired" }); return }
      if (resp.status === 409) { updateEntry(key, { stage: "duplicate" }); return }
      if (resp.status === 429) { updateEntry(key, { stage: "quota_exceeded" }); return }
      if (!resp.ok) { updateEntry(key, { stage: "failed" }); return }
      const item = await resp.json()
      await streamProgress(key, item.id, token)
    } catch { updateEntry(key, { stage: "failed" }) }
  }

  async function streamProgress(key: string, itemId: string, token: string) {
    try {
      const resp = await fetch(`${API}/items/${itemId}/stream`, { headers: { Authorization: `Bearer ${token}` } })
      if (!resp.ok || !resp.body) { updateEntry(key, { stage: "failed" }); return }
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
              setItemCount((n) => (n !== null ? n + 1 : null))
              reader.cancel(); return
            } else if (data.status === "progress") {
              updateEntry(key, { stage: data.stage })
            } else if (data.status === "failed" || data.status === "timeout") {
              updateEntry(key, { stage: "failed" }); reader.cancel(); return
            }
          } catch {}
        }
      }
    } catch { updateEntry(key, { stage: "failed" }) }
  }

  const primaryBtn: React.CSSProperties = {
    backgroundColor: GREEN, color: "#000", border: "none", borderRadius: 8,
    padding: "10px 16px", fontSize: 13, fontWeight: 700, cursor: "pointer", width: "100%",
  }
  const disabledBtn: React.CSSProperties = {
    ...primaryBtn, backgroundColor: dark ? "#1a1a1a" : "#e0e0e0", color: subFg, cursor: "not-allowed",
  }

  const currentUrlUnsavable = !currentTab || isUnsavableUrl(currentTab.url)
  const currentSaving = currentTab
    ? entries.find((e) => e.url === currentTab.url && PROGRESS_STAGES.has(e.stage))
    : null

  const headerProps = { dark, setDark, lang, setLang, fg, subFg, borderColor, itemCount, t }

  if (loggedIn === null) {
    return (
      <div style={shell(bg, fg)}>
        <p style={{ color: subFg, fontSize: 13, margin: "auto" }}>{t.loading}</p>
      </div>
    )
  }

  if (!loggedIn || authExpired) {
    return (
      <div style={shell(bg, fg)}>
        <Header {...headerProps} />
        <div style={{ padding: "24px 16px", display: "flex", flexDirection: "column", gap: 8 }}>
          <p style={{ color: subFg, fontSize: 13, margin: 0 }}>
            {authExpired ? t.authExpired : t.loginPrompt}
          </p>
          <button style={primaryBtn} onClick={async () => {
            if (authExpired) { await clearStoredSession(); setAuthExpired(false); setLoggedIn(false) }
            else chrome.tabs.create({ url: WEB + "/app/connected" })
          }}>
            {authExpired ? t.reLogin : t.goLogin}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div style={shell(bg, fg)}>
      <Header {...headerProps} />

      <div style={{ padding: "16px 16px 0" }}>
        <p style={sectionLabel(subFg)}>{t.capture}</p>

        {/* Tab 切換 */}
        <div style={{ display: "flex", backgroundColor: tabBg, borderRadius: 8, padding: 3, marginBottom: 12 }}>
          {(["current", "paste"] as const).map((tab) => (
            <button key={tab} onClick={() => setActiveTab(tab)} style={{
              flex: 1, border: "none", borderRadius: 6, padding: "6px 0",
              fontSize: 12, fontWeight: 600, cursor: "pointer",
              backgroundColor: activeTab === tab ? tabActiveBg : "transparent",
              color: activeTab === tab ? fg : subFg,
              transition: "background 0.15s",
              boxShadow: activeTab === tab ? (dark ? "0 1px 3px rgba(0,0,0,0.4)" : "0 1px 3px rgba(0,0,0,0.08)") : "none",
            }}>
              {tab === "current" ? t.currentTab : t.pasteUrl}
            </button>
          ))}
        </div>

        {activeTab === "current" && (
          <div>
            <p style={sectionLabel(subFg)}>{t.currentTabLabel}</p>
            <div style={{ backgroundColor: cardBg, borderRadius: 8, padding: "10px 12px", marginBottom: 10, display: "flex", alignItems: "flex-start", gap: 10 }}>
              {currentTab ? (
                <>
                  <div style={{ width: 28, height: 28, borderRadius: 6, backgroundColor: dark ? "#1e1e1e" : "#e8e8e8", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, fontSize: 13 }}>▶</div>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <p style={{ margin: 0, fontSize: 13, fontWeight: 500, color: fg, lineHeight: 1.4, overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>
                      {currentTab.title}
                    </p>
                    <p style={{ margin: "3px 0 0", fontSize: 11, color: subFg, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {(() => { try { return new URL(currentTab.url).hostname } catch { return currentTab.url } })()}
                    </p>
                  </div>
                </>
              ) : (
                <p style={{ margin: 0, fontSize: 13, color: subFg }}>{t.noTab}</p>
              )}
            </div>
            <button
              style={currentUrlUnsavable || !!currentSaving ? disabledBtn : primaryBtn}
              disabled={currentUrlUnsavable || !!currentSaving}
              onClick={() => currentTab && handleSave(currentTab.url, currentTab.title)}>
              {currentSaving ? t.saving : t.saveBtn}
            </button>
          </div>
        )}

        {activeTab === "paste" && (
          <div>
            <p style={sectionLabel(subFg)}>{t.pasteLabel}</p>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 8, backgroundColor: inputBg, border: `1px solid ${borderColor}`, borderRadius: 8, padding: "8px 12px" }}>
                <span style={{ color: subFg, fontSize: 13, flexShrink: 0 }}>🔗</span>
                <input
                  type="url"
                  placeholder={t.pastePlaceholder}
                  value={pasteUrl}
                  onChange={(e) => setPasteUrl(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && pasteUrl.trim()) handleSave(pasteUrl.trim(), pasteUrl.trim()) }}
                  style={{ flex: 1, border: "none", outline: "none", backgroundColor: "transparent", color: fg, fontSize: 13, fontFamily: "inherit" }}
                />
              </div>
              <button
                onClick={() => pasteUrl.trim() && handleSave(pasteUrl.trim(), pasteUrl.trim())}
                disabled={!pasteUrl.trim()}
                style={{ width: 36, height: 36, borderRadius: 8, border: "none", backgroundColor: pasteUrl.trim() ? GREEN : (dark ? "#1a1a1a" : "#e0e0e0"), color: pasteUrl.trim() ? "#000" : subFg, fontSize: 18, cursor: pasteUrl.trim() ? "pointer" : "not-allowed", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                +
              </button>
            </div>
          </div>
        )}
      </div>

      {entries.length > 0 && (
        <div style={{ marginTop: 20, flex: 1, overflowY: "auto" }}>
          <p style={{ ...sectionLabel(subFg), margin: "0 16px 10px" }}>{t.recentlySaved}</p>
          {entries.map((entry) => (
            <EntryRow key={entry.key} entry={entry} dark={dark} fg={fg} subFg={subFg} cardBg={cardBg} GREEN={GREEN} t={t}
              onViewItem={(id) => chrome.tabs.create({ url: `${WEB}/app/item/${id}` })}
              onRemove={(key) => setEntries((prev) => prev.filter((e) => e.key !== key))}
            />
          ))}
        </div>
      )}

      <div style={{ marginTop: "auto", padding: "10px 16px", borderTop: `1px solid ${borderColor}`, display: "flex", justifyContent: "flex-end" }}>
        <span style={{ fontSize: 11, color: subFg }}>
          {aiCredits !== null ? t.aiCredits(aiCredits) : ""}
        </span>
      </div>
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────

function shell(bg: string, fg: string): React.CSSProperties {
  return { display: "flex", flexDirection: "column", height: "100vh", fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", backgroundColor: bg, color: fg, boxSizing: "border-box", overflow: "hidden" }
}

function sectionLabel(subFg: string): React.CSSProperties {
  return { margin: "0 0 8px", fontSize: 10, fontWeight: 600, color: subFg, letterSpacing: "0.08em" }
}

// ── Header ────────────────────────────────────────────────

function Header({ dark, setDark, lang, setLang, fg, subFg, borderColor, itemCount, t }: {
  dark: boolean; setDark: (v: boolean) => void
  lang: Lang; setLang: (v: Lang) => void
  fg: string; subFg: string; borderColor: string
  itemCount: number | null; t: typeof T["zh"]
}) {
  const badgeBg = dark ? "#161616" : "#f0f0f0"
  return (
    <div style={{ padding: "12px 16px", borderBottom: `1px solid ${borderColor}`, display: "flex", alignItems: "center", gap: 8 }}>
      <button onClick={() => chrome.tabs.create({ url: WEB + "/app" })}
        style={{ background: "none", border: "none", padding: 0, cursor: "pointer", fontSize: 15, fontWeight: 700, color: GREEN, letterSpacing: "-0.3px" }}>
        Garner ✦
      </button>
      {itemCount !== null && (
        <span style={{ fontSize: 11, color: subFg, backgroundColor: badgeBg, borderRadius: 10, padding: "2px 8px" }}>
          {t.saved(itemCount)}
        </span>
      )}
      <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
        <IconBtn dark={dark} borderColor={borderColor} subFg={subFg}
          label={lang === "zh" ? "中" : "EN"}
          onClick={() => setLang(lang === "zh" ? "en" : "zh")}
        />
        <IconBtn dark={dark} borderColor={borderColor} subFg={subFg}
          label={dark ? "☀" : "☾"}
          onClick={() => setDark(!dark)}
        />
      </div>
    </div>
  )
}

function IconBtn({ dark, borderColor, subFg, label, onClick }: {
  dark: boolean; borderColor: string; subFg: string; label: string; onClick: () => void
}) {
  return (
    <button onClick={onClick} style={{ background: "none", border: `1px solid ${borderColor}`, borderRadius: 6, width: 28, height: 28, fontSize: 12, color: subFg, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
      {label}
    </button>
  )
}

// ── EntryRow ──────────────────────────────────────────────

function EntryRow({ entry, dark, fg, subFg, cardBg, GREEN, t, onViewItem, onRemove }: {
  entry: SaveEntry; dark: boolean; fg: string; subFg: string; cardBg: string; GREEN: string
  t: typeof T["zh"]; onViewItem: (id: string) => void; onRemove: (key: string) => void
}) {
  const { stage, title, item, key } = entry
  const rowStyle: React.CSSProperties = { margin: "0 16px 8px", backgroundColor: cardBg, borderRadius: 10, padding: "12px", display: "flex", flexDirection: "column", gap: 8 }
  const titleStyle: React.CSSProperties = { margin: 0, fontSize: 13, fontWeight: 500, color: fg, lineHeight: 1.4, overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }
  const subStyle: React.CSSProperties = { margin: 0, fontSize: 11, color: subFg }
  const smallBtn = (accent?: boolean): React.CSSProperties => ({
    border: "none", borderRadius: 6, padding: "6px 12px", fontSize: 12,
    cursor: "pointer", fontWeight: 600, flex: 1,
    backgroundColor: accent ? GREEN : (dark ? "#1e1e1e" : "#e8e8e8"),
    color: accent ? "#000" : subFg,
  })
  const dismissX = (
    <button onClick={() => onRemove(key)} style={{ background: "none", border: "none", cursor: "pointer", color: subFg, fontSize: 14, padding: 0, flexShrink: 0, lineHeight: 1 }}>✕</button>
  )

  if (PROGRESS_STAGES.has(stage)) {
    return (
      <div style={rowStyle}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
          <p style={{ ...titleStyle, flex: 1 }}>{title}</p>
          {dismissX}
        </div>
        <div style={{ backgroundColor: dark ? "#1e1e1e" : "#e0e0e0", borderRadius: 3, height: 3, overflow: "hidden" }}>
          <div style={{ backgroundColor: GREEN, height: "100%", borderRadius: 3, transition: "width 0.6s ease", width: `${STAGE_PROGRESS[stage] ?? 10}%` }} />
        </div>
        <p style={subStyle}>{t.stageLabel[stage as keyof typeof t.stageLabel] ?? t.saving}</p>
      </div>
    )
  }

  if (stage === "done") {
    return (
      <div style={rowStyle}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
          <span style={{ color: GREEN, fontSize: 14, marginTop: 1, flexShrink: 0 }}>✓</span>
          <p style={{ ...titleStyle, flex: 1 }}>{item?.title || title}</p>
          {dismissX}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ color: GREEN, fontSize: 11 }}>● {t.savedBadge}</span>
          <span style={{ color: subFg, fontSize: 11 }}>· {t.justNow}</span>
        </div>
        {item?.tags?.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
            {item.tags.slice(0, 4).map((tag: any) => (
              <span key={tag.id} style={{ backgroundColor: dark ? "#1e1e1e" : "#e8e8e8", color: subFg, borderRadius: 4, padding: "2px 7px", fontSize: 10 }}>
                {tag.name}
              </span>
            ))}
          </div>
        )}
        <div style={{ display: "flex", gap: 6 }}>
          <button style={smallBtn()} onClick={() => onRemove(key)}>{t.dismiss}</button>
          <button style={smallBtn(true)} onClick={() => onViewItem(item.id)}>{t.view}</button>
        </div>
      </div>
    )
  }

  if (stage === "duplicate") {
    return (
      <div style={rowStyle}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
          <p style={{ ...titleStyle, flex: 1, color: subFg }}>{title}</p>
          {dismissX}
        </div>
        <p style={subStyle}>{t.alreadyExists}</p>
      </div>
    )
  }

  if (stage === "quota_exceeded") {
    return (
      <div style={rowStyle}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
          <p style={{ ...titleStyle, flex: 1, color: "#fbbf24" }}>{title}</p>
          {dismissX}
        </div>
        <p style={subStyle}>{t.quotaExceeded}</p>
      </div>
    )
  }

  if (stage === "failed" || stage === "auth_expired") {
    return (
      <div style={rowStyle}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
          <p style={{ ...titleStyle, flex: 1, color: "#f87171" }}>{title}</p>
          {dismissX}
        </div>
        <p style={subStyle}>{stage === "auth_expired" ? t.authExpiredShort : t.failed}</p>
      </div>
    )
  }

  return null
}
