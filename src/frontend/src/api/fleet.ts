const BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? ''

export interface Vehicle {
  id: string | number
  name: string
  status: 'available' | 'in_transit' | 'maintenance' | 'offline'
  location?: { lat: number; lng: number }
  current_route_id?: string
  driver_id?: string
  capacity?: number
}

export interface Route {
  id: string | number
  origin: string
  destination: string
  status: string
  estimated_duration_mins: number
  risk_score: number
}

export interface RouteAlternative {
  id: string | number
  duration_mins: number
  risk_score: number
  description: string
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

export const fleetApi = {
  getFleet: () => request<Vehicle[]>('/api/fleet'),
  getVehicle: (id: string | number) => request<Vehicle>(`/api/fleet/${id}`),
  getRoutes: () => request<Route[]>('/api/routes'),
  getRouteAlternatives: (id: string | number) => request<RouteAlternative[]>(`/api/routes/${id}/alternatives`),
}
