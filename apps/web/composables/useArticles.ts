import type { ArticleUpdate, Item } from '~/types/api'

export function useArticles() {
  const apiFetch = useApiFetch()

  function listArticles(): Promise<Item[]> {
    return apiFetch('/articles/')
  }

  function createArticle(): Promise<Item> {
    return apiFetch('/articles/', { method: 'POST' })
  }

  function updateArticle(id: string, data: ArticleUpdate): Promise<Item> {
    return apiFetch(`/articles/${id}`, { method: 'PATCH', body: data })
  }

  function publishArticle(id: string): Promise<Item> {
    return apiFetch(`/articles/${id}/publish`, { method: 'POST' })
  }

  async function uploadCover(id: string, file: File): Promise<Item> {
    const compressed = await compressImage(file)
    const form = new FormData()
    form.append('file', compressed, 'cover.jpg')
    return apiFetch(`/articles/${id}/cover`, { method: 'POST', body: form })
  }

  return { listArticles, createArticle, updateArticle, publishArticle, uploadCover }
}

async function compressImage(file: File): Promise<Blob> {
  return new Promise((resolve) => {
    const img = new Image()
    const objectUrl = URL.createObjectURL(file)
    img.onload = () => {
      const MAX = 1200
      let { width, height } = img
      if (width > MAX || height > MAX) {
        const ratio = Math.min(MAX / width, MAX / height)
        width = Math.round(width * ratio)
        height = Math.round(height * ratio)
      }
      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      canvas.getContext('2d')!.drawImage(img, 0, 0, width, height)
      URL.revokeObjectURL(objectUrl)
      canvas.toBlob((blob) => resolve(blob!), 'image/jpeg', 0.82)
    }
    img.src = objectUrl
  })
}
