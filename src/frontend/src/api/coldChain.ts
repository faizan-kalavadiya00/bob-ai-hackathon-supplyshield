const BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? ''

export interface ColdChainShipment {
  shipment_id: string | number
  status: string
  cargo_at_risk: boolean
  temperature_breach: boolean
  summary?: string
}

export interface SensorReading {
  timestamp: string
  temperature: number
  humidity: number
  breach_detected: boolean
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

export const coldChainApi = {
  list: () => request<ColdChainShipment[]>('/api/cold-chain'),
  getShipment: (id: string | number) => request<ColdChainShipment>(`/api/cold-chain/${id}`),
  getReadings: (id: string | number) => request<SensorReading[]>(`/api/cold-chain/${id}/readings`),
}
