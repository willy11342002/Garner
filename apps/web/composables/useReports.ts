import type { Report, ReportListItem } from '~/types/api'

export function useReports() {
  const apiFetch = useApiFetch()

  function listReports(): Promise<ReportListItem[]> {
    return apiFetch('/reports/')
  }

  function getReport(id: string): Promise<Report> {
    return apiFetch(`/reports/${id}`)
  }

  function updateReport(id: string, data: { title?: string; body_md?: string }): Promise<Report> {
    return apiFetch(`/reports/${id}`, { method: 'PATCH', body: data })
  }

  // AI 依指示修改目前內文（保留人類編輯）
  function reviseReport(id: string, instruction: string): Promise<Report> {
    return apiFetch(`/reports/${id}/revise`, { method: 'POST', body: { instruction } })
  }

  // AI 從來源重新生成（會覆蓋現有內文）
  function regenerateReport(id: string): Promise<Report> {
    return apiFetch(`/reports/${id}/regenerate`, { method: 'POST' })
  }

  function deleteReport(id: string): Promise<void> {
    return apiFetch(`/reports/${id}`, { method: 'DELETE' })
  }

  return { listReports, getReport, updateReport, reviseReport, regenerateReport, deleteReport }
}
