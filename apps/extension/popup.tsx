import React, { useEffect, useState } from "react"
import { clearStoredSession, getStoredSession } from "./lib/auth"

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

const PROGRESS_STAGES = new Set(["fetching_info", "fetching_content", "understanding", "analyzing", "embedding", "validating"])

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

type SaveState = {
  saveStage: Stage
  savedItem: any | null
  saveUrl: string | null
  saveTitle: string | null
}

const STORAGE_KEYS = ["saveStage", "savedItem", "saveUrl", "saveTitle"] as const

export default function Popup() {
  const dark = useTheme()
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null)
  const [saveState, setSaveState] = useState<SaveState>({
    saveStage: "idle",
    savedItem: null,
    saveUrl: null,
    saveTitle: null,
  })
  const [currentTab, setCurrentTab] = useState<{ url: string; title: string } | null>(null)

  const bg = dark ? "#0a0a0a" : "#ffffff"
  const fg = dark ? "#e8e8e8" : "#111111"
  const cardBg = dark ? "#141414" : "#f4f4f4"
  const subFg = dark ? "#555" : "#888"
  const borderColor = dark ? "#222" : "#e0e0e0"

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

    // 讀取持久化的儲存進度
    chrome.storage.local.get([...STORAGE_KEYS], (result) => {
      if (result.saveStage && result.saveStage !== "idle") {
        setSaveState({
          saveStage: result.saveStage as Stage,
          savedItem: result.savedItem ?? null,
          saveUrl: result.saveUrl ?? null,
          saveTitle: result.saveTitle ?? null,
        })
      }
    })

    function onStorageChanged(changes: Record<string, chrome.storage.StorageChange>) {
      if ("pat" in changes || "access_token" in changes) {
        getStoredSession().then((s) => setLoggedIn(!!s))
      }
      if (STORAGE_KEYS.some((k) => k in changes)) {
        chrome.storage.local.get([...STORAGE_KEYS], (result) => {
          setSaveState({
            saveStage: (result.saveStage as Stage) ?? "idle",
            savedItem: result.savedItem ?? null,
            saveUrl: result.saveUrl ?? null,
            saveTitle: result.saveTitle ?? null,
          })
        })
      }
    }
    chrome.storage.onChanged.addListener(onStorageChanged)
    return () => chrome.storage.onChanged.removeListener(onStorageChanged)
  }, [])

  async function handleSave() {
    if (!currentTab) return
    chrome.runtime.sendMessage({
      type: "SAVE_ITEM",
      url: currentTab.url,
      title: currentTab.title,
    })
  }

  async function handleDismiss() {
    await chrome.storage.local.remove([...STORAGE_KEYS])
    setSaveState({ saveStage: "idle", savedItem: null, saveUrl: null, saveTitle: null })
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

  const { saveStage: stage, savedItem, saveTitle } = saveState

  function renderContent() {
    if (loggedIn === null) {
      return <p style={{ color: subFg, fontSize: 13, margin: 0 }}>載入中…</p>
    }

    if (!loggedIn) {
      return (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <p style={{ color: subFg, fontSize: 13, margin: "0 0 4px" }}>請先在 Garner 網頁版登入</p>
          <button style={primaryBtn} onClick={() => openGarner("/app/connected")}>前往登入</button>
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
          <button style={secondaryBtn} onClick={handleDismiss}>再存一頁</button>
        </div>
      )
    }

    if (stage === "failed") {
      return (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <p style={{ color: "#f87171", fontSize: 13, margin: "0 0 4px", textAlign: "center" }}>處理失敗，請稍後再試</p>
          <button style={primaryBtn} onClick={handleDismiss}>重試</button>
        </div>
      )
    }

    // 進度中狀態（fetching_info / fetching_content / analyzing / embedding）
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {saveTitle && (
          <div style={{ backgroundColor: cardBg, borderRadius: 8, padding: "8px 12px", marginBottom: 2 }}>
            <p style={{ margin: 0, fontSize: 12, color: fg, lineHeight: 1.4 }}>
              {saveTitle.length > 52 ? saveTitle.slice(0, 49) + "…" : saveTitle}
            </p>
          </div>
        )}
        <div style={{ backgroundColor: cardBg, borderRadius: 4, height: 3, overflow: "hidden" }}>
          <div style={{
            backgroundColor: GREEN, height: "100%", borderRadius: 4,
            transition: "width 0.6s ease", width: `${STAGE_PROGRESS[stage] ?? 10}%`,
          }} />
        </div>
        <p style={{ color: subFg, fontSize: 12, margin: 0, textAlign: "center" }}>
          {STAGE_LABEL[stage] ?? "處理中…"}
        </p>
        <button style={secondaryBtn} onClick={handleDismiss}>取消</button>
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
        {PROGRESS_STAGES.has(stage) && (
          <span style={{
            marginLeft: "auto", fontSize: 10, color: GREEN,
            border: `1px solid ${GREEN}`, borderRadius: 10,
            padding: "1px 7px", letterSpacing: "0.3px",
          }}>處理中</span>
        )}
      </div>
      {renderContent()}
    </div>
  )
}
