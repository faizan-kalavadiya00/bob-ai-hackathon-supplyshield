/**
 * Resilience API client — typed wrappers for Phase 3 endpoints.
 */

const BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? ''

export interface DimensionState {
  dimension: string
  maximum_balance: number
  remaining_balance: number
  consumed_balance: number
  utilization_percent: number
  dimension_score: number
  status: 'HEALTHY' | 'STRESSED' | 'VULNERABLE' | 'CRITICAL' | 'BANKRUPT'
  unit: string
}

export interface WalletState {
  shipment_id: number
  shipment_code: string
  time: DimensionState
  cost: DimensionState
  temperature: DimensionState
  capacity: DimensionState
  is_resilience_bankrupt: boolean
  computed_at: string
}

export interface Contributor {
  factor: string
  impact: number
  reason: string
  severity: string
}

export interface RRIExplanation {
  rri: number
  status: 'HEALTHY' | 'STRESSED' | 'VULNERABLE' | 'CRITICAL' | 'BANKRUPT'
  dimensions: Record<string, number>
  weights: Record<string, number>
  weighted_scores: Record<string, number>
  contributors: Contributor[]
  criticality_adjustment: number
  weighted_score_before_adjustment: number
  bankruptcy_flags: Record<string, boolean>
  is_resilience_bankrupt: boolean
  shipment_priority: string
  computed_at: string
}

export interface ResilienceResponse {
  wallet: WalletState
  rri: RRIExplanation
}

export interface ResilienceTransaction {
  id: number
  wallet_id: number
  dimension: string
  amount: number
  reason: string
  reference_id: string | null
  timestamp: string
}

export interface RRISummary {
  total_shipments_assessed: number
  average_rri: number
  healthy_count: number
  stressed_count: number
  vulnerable_count: number
  critical_count: number
  bankrupt_count: number
  resilience_bankruptcies: number
  computed_at: string
}

export interface ApplyEventRequest {
  dimension: 'time' | 'cost' | 'temperature' | 'capacity'
  amount: number
  reason: string
  reference_id?: string
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`API ${res.status}: ${detail}`)
  }
  return res.json() as Promise<T>
}

export const resilienceApi = {
  getResilience: (shipmentId: number) =>
    request<ResilienceResponse>(`/api/shipments/${shipmentId}/resilience`),

  recalculate: (shipmentId: number) =>
    request<ResilienceResponse>(`/api/shipments/${shipmentId}/resilience/recalculate`, {
      method: 'POST',
    }),

  applyEvent: (shipmentId: number, event: ApplyEventRequest) =>
    request<ResilienceResponse>(`/api/shipments/${shipmentId}/resilience/apply-event`, {
      method: 'POST',
      body: JSON.stringify(event),
    }),

  getTransactions: (shipmentId: number) =>
    request<ResilienceTransaction[]>(`/api/shipments/${shipmentId}/resilience/transactions`),

  getSummary: () =>
    request<RRISummary>('/api/shipments/resilience/summary'),
}
