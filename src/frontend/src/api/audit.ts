import { request } from './shared'

export interface AuditLogEntry {
  id: string
  timestamp: string
  actor: string
  action: string
  entityType: string
  entityId: string
  changes?: {
    before?: Record<string, any>
    after?: Record<string, any>
  }
}

export const apiAudit = {
  list: (params?: { page?: number; limit?: number }) => {
    const qs = new URLSearchParams()
    if (params?.page) qs.append('page', params.page.toString())
    if (params?.limit) qs.append('limit', params.limit.toString())
    const qStr = qs.toString() ? `?${qs.toString()}` : ''
    return request<AuditLogEntry[]>(`/api/audit${qStr}`)
  }
}
