import { request } from './shared'

export interface ShipmentSummary {
  id: number
  shipment_code: string
  origin: string
  destination: string
  cargo_type: string
  cargo_value_usd: number
  weight_kg: number
  priority: string
  status: string
  temperature_sensitive: boolean
  eta: string
}

export const shipmentsApi = {
  list: () => request<ShipmentSummary[]>('/api/shipments'),
}
