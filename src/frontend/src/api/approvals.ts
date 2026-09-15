import { request } from './shared'

export interface ApprovalRequest {
  id: string
  entityType: string
  entityId: string
  action: string
  details: Record<string, any>
  status: 'pending' | 'approved' | 'rejected'
  requestedBy: string
  requestedAt: string
  resolvedBy?: string
  resolvedAt?: string
  reason?: string
}

export const apiApprovals = {
  list: () => request<ApprovalRequest[]>('/api/approvals'),
  approve: (id: string, reason?: string) => 
    request<ApprovalRequest>(`/api/approvals/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ reason })
    }),
  reject: (id: string, reason?: string) => 
    request<ApprovalRequest>(`/api/approvals/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason })
    }),
}
