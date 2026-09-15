import React, { useEffect, useState } from 'react'
import { fleetApi, Vehicle, Route, RouteAlternative } from '../api/fleet'
import { Truck, Map, AlertTriangle, ShieldCheck } from 'lucide-react'

export const Fleet: React.FC = () => {
  const [vehicles, setVehicles] = useState<Vehicle[]>([])
  const [routes, setRoutes] = useState<Route[]>([])
  const [selectedRouteId, setSelectedRouteId] = useState<string | number | null>(null)
  const [alternatives, setAlternatives] = useState<RouteAlternative[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true)
        const [fleetData, routesData] = await Promise.all([
          fleetApi.getFleet().catch(() => [] as Vehicle[]),
          fleetApi.getRoutes().catch(() => [] as Route[])
        ])
        setVehicles(fleetData)
        setRoutes(routesData)
      } catch (err: any) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  useEffect(() => {
    if (selectedRouteId) {
      fleetApi.getRouteAlternatives(selectedRouteId)
        .then(setAlternatives)
        .catch(() => setAlternatives([]))
    }
  }, [selectedRouteId])

  if (loading) return <div className="p-6 text-gray-400">Loading Fleet & Routes...</div>
  if (error) return <div className="p-6 text-red-400">Error: {error}</div>

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-100 flex items-center gap-2">
        <Truck className="w-6 h-6 text-shield-500" /> Fleet & Route Optimization
      </h1>

      <section>
        <h2 className="text-xl font-semibold text-gray-200 mb-4">Vehicles</h2>
        {vehicles.length === 0 ? (
          <p className="text-gray-400">No vehicles found.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {vehicles.map(v => (
              <div key={v.id} className="p-4 bg-gray-800 border border-gray-700 rounded-lg">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-medium text-gray-200">{v.name}</span>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${v.status === 'available' ? 'bg-green-900 text-green-300' : 'bg-gray-700 text-gray-300'}`}>
                    {v.status.replace('_', ' ')}
                  </span>
                </div>
                {v.current_route_id && (
                  <div className="text-sm text-gray-400">
                    Route ID: <span className="text-gray-300">{v.current_route_id}</span>
                  </div>
                )}
                {v.capacity && (
                  <div className="text-sm text-gray-400">
                    Capacity: <span className="text-gray-300">{v.capacity} units</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-xl font-semibold text-gray-200 mb-4">Routes</h2>
        {routes.length === 0 ? (
          <p className="text-gray-400">No active routes.</p>
        ) : (
          <div className="space-y-4">
            {routes.map(r => (
              <div key={r.id} className="p-4 bg-gray-800 border border-gray-700 rounded-lg flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                  <div className="font-medium text-gray-200 flex items-center gap-2">
                    <Map className="w-4 h-4 text-gray-400" />
                    {r.origin} → {r.destination}
                  </div>
                  <div className="text-sm text-gray-400 mt-1">
                    Status: {r.status} | Est. Duration: {r.estimated_duration_mins} mins
                  </div>
                  <div className="text-sm flex items-center gap-1 mt-1">
                    Risk Score: 
                    <span className={r.risk_score > 50 ? 'text-red-400' : 'text-green-400'}>
                      {r.risk_score}
                    </span>
                    {r.risk_score > 50 ? <AlertTriangle className="w-4 h-4 text-red-400" /> : <ShieldCheck className="w-4 h-4 text-green-400" />}
                  </div>
                </div>
                <button
                  onClick={() => setSelectedRouteId(selectedRouteId === r.id ? null : r.id)}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded text-sm transition-colors"
                >
                  {selectedRouteId === r.id ? 'Hide Alternatives' : 'View Alternatives'}
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {selectedRouteId && (
        <section className="p-4 bg-gray-900 border border-gray-700 rounded-lg">
          <h3 className="text-lg font-medium text-gray-200 mb-3">Alternatives for Route {selectedRouteId}</h3>
          {alternatives.length === 0 ? (
            <p className="text-gray-400 text-sm">No alternatives available.</p>
          ) : (
            <div className="space-y-3">
              {alternatives.map(alt => (
                <div key={alt.id} className="p-3 bg-gray-800 rounded border border-gray-700 flex justify-between items-center">
                  <div>
                    <div className="text-gray-200 text-sm font-medium">{alt.description}</div>
                    <div className="text-gray-400 text-xs mt-1">Duration: {alt.duration_mins} mins</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-gray-400 mb-1">Risk Weight</div>
                    <div className={`text-sm font-bold ${alt.risk_score > 50 ? 'text-red-400' : 'text-green-400'}`}>
                      {alt.risk_score}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  )
}

export default Fleet
