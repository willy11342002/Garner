export {}

// 點擊 toolbar icon → 開啟 Side Panel
chrome.action.onClicked.addListener((tab) => {
  if (tab.windowId) {
    chrome.sidePanel.open({ windowId: tab.windowId })
  }
})

chrome.runtime.onInstalled.addListener(() => {
  console.log("Garner extension installed")
})
