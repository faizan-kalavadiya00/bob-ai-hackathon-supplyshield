/**
 * Disruption Management API client — Phase 4B.
 * All types mirror the backend Pydantic schemas exactly.
 */

const BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? ''

export interface DisruptionSummary {
  id: number
  disruption_code: string
  name: string
  type: string
  severity: number
  affected_region: string
  status: 'active' | 'monitoring' | 'historical' | 'resolved'
  start_time: string
  end_time: string | null
  description: string | null
  affected_shipment_count: number
  total_cargo_exposure_usd: number
  avg_impact_score: number
  total_delay_hours: number
  duration_hours: number
}

export interface ShipmentImpact {
  shipment_id: number
  shipment_code: string
  origin: string
  destination: string
  cargo_type: string
  cargo_value_usd: number
  weight_kg: number
  priority: string
  status: string
  temperature_sensitive: boolean
  impact_score: number
  delay_hours: number
}

export interface DNARecord {
  disruption_id: number
  type_score: number
  type_label: string
  severity_score: number
  severity_raw: number
  duration_score: number
  duration_hours: number
  geo_scope_score: number
  geo_scope_label: string
  transport_mode_score: number
  transport_mode_label: string
  capacity_impact_score: number
  port_relevance_score: number
  region_score: number
  region_label: string
  avg_impact_score: number
  affected_shipment_count: number
  dna_summary: string | null
  generated_at: string
}

export interface DimensionMatch {
  dimension: string
  weight: number
  subject_score: number
  candidate_score: number
  difference: number
  contribution: number
  match_quality: 'STRONG' | 'MODERATE' | 'WEAK' | 'NONE'
}

export interface SimilarityResult {
  disruption_id: number
  disruption_code: string
  name: string
  disruption_type: string
  severity: number
  affected_region: string
  status: string
  duration_hours: number
  similarity_score: number
  dimension_matches: DimensionMatch[]
  top_matching_dimensions: string[]
  historical_outcome: string | null
}

export interface CascadeNode {
  level: string
  label: string
  detail: string | null
  children: CascadeNode[]
}

export interface DisruptionImpact {
  disruption_id: number
  disruption_code: string
  name: string
  affected_shipments: ShipmentImpact[]
  total_cargo_exposure_usd: number
  affected_shipment_count: number
  temperature_sensitive_count: number
  total_delay_hours: number
  avg_impact_score: number
  cascade: CascadeNode
}

/** AI Decision Support — mirrors AIInsightsResponseSchema from the backend. */
export interface AIInsightsRecord {
  disruption_explanation: string
  risk_summary: string
  decision_support: string
  recommended_actions: string[]
  model_id: string
  tokens_used: number | null
}

export interface AIInsightsResponse {
  watsonx_enabled: boolean
  /** "available" | "unavailable" | "error" */
  status: string
  message: string
  /** Deterministic system facts — always present regardless of AI status */
  system_facts: Record<string, unknown>
  /** AI-generated text — null when watsonx is not configured or fails */
  insights: AIInsightsRecord | null
  error_detail: string | null
}

export interface DisruptionDetail {
  id: number
  disruption_code: string
  name: string
  type: string
  severity: number
  affected_region: string
  status: string
  start_time: string
  end_time: string | null
  description: string | null
  duration_hours: number
  affected_shipment_count: number
  total_cargo_exposure_usd: number
  avg_impact_score: number
  total_delay_hours: number
  temperature_sensitive_count: number
  dna: DNARecord | null
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

export const disruptionsApi = {
  list: (status?: string) => {
    const qs = status ? `?status=${encodeURIComponent(status)}` : ''
    return request<DisruptionSummary[]>(`/api/disruptions${qs}`)
  },

  get: (id: number) =>
    request<DisruptionDetail>(`/api/disruptions/${id}`),

  getDNA: (id: number) =>
    request<DNARecord>(`/api/disruptions/${id}/dna`),

  getSimilar: (id: number) =>
    request<SimilarityResult[]>(`/api/disruptions/${id}/similar`),

  getImpact: (id: number) =>
    request<DisruptionImpact>(`/api/disruptions/${id}/impact`),

  /**
   * AI Decision Support panel data.
   * Always returns system_facts (deterministic).
   * insights is null when watsonx.ai is not configured.
   */
  getAIInsights: (id: number) =>
    request<AIInsightsResponse>(`/api/disruptions/${id}/ai-insights`),
}
