/**
 * Typed API client for the SupplyShield backend.
 *
 * Uses the Vite dev-server proxy so all calls go to /health and /api/...
 * In production, set VITE_API_BASE_URL to the backend origin.
 */

const BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? ''

export interface HealthResponse {
  status: 'ok' | 'degraded' | 'error'
  service: string
  version: string
  environment: string
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText} (${path})`)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: {
    get: () => request<HealthResponse>('/health'),
  },
}
