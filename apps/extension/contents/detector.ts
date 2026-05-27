export {}

function getOgImage(): string | null {
  const el = document.querySelector<HTMLMetaElement>('meta[property="og:image"]')
  return el?.content ?? null
}

function getOgTitle(): string | null {
  const el = document.querySelector<HTMLMetaElement>('meta[property="og:title"]')
  return el?.content ?? null
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "GET_PAGE_META") {
    sendResponse({
      ogImage: getOgImage(),
      ogTitle: getOgTitle(),
      url: location.href,
    })
  }
})
