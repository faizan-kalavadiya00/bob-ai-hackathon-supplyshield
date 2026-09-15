import React, { useEffect, useState } from 'react'
import { coldChainApi, ColdChainShipment, SensorReading } from '../api/coldChain'
import { Thermometer, Snowflake, AlertOctagon, Activity } from 'lucide-react'

export const ColdChain: React.FC = () => {
  const [shipments, setShipments] = useState<ColdChainShipment[]>([])
  const [selectedShipmentId, setSelectedShipmentId] = useState<string | number | null>(null)
  const [readings, setReadings] = useState<SensorReading[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadShipments = async () => {
      try {
        setLoading(true)
        const data = await coldChainApi.list()
        setShipments(data || [])
      } catch (err: any) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    loadShipments()
  }, [])

  useEffect(() => {
    if (selectedShipmentId) {
      coldChainApi.getReadings(selectedShipmentId)
        .then(setReadings)
        .catch(() => setReadings([]))
    }
  }, [selectedShipmentId])

  if (loading) return <div className="p-6 text-gray-400">Loading Cold Chain...</div>
  if (error) return <div className="p-6 text-red-400">Error: {error}</div>

  const atRiskCount = shipments.filter(s => s.cargo_at_risk).length

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h1 className="text-2xl font-bold text-gray-100 flex items-center gap-2">
          <Snowflake className="w-6 h-6 text-blue-400" /> Cold Chain Monitoring
        </h1>
        {atRiskCount > 0 && (
          <div className="px-4 py-2 bg-red-900/30 border border-red-800 rounded-lg flex items-center gap-2 text-red-400">
            <AlertOctagon className="w-5 h-5" />
            <span className="font-semibold">{atRiskCount} Cargo At Risk</span>
          </div>
        )}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <section>
          <h2 className="text-xl font-semibold text-gray-200 mb-4">Active Shipments</h2>
          {shipments.length === 0 ? (
            <p className="text-gray-400">No active cold chain shipments.</p>
          ) : (
            <div className="space-y-3">
              {shipments.map(s => (
                <div 
                  key={s.shipment_id} 
                  onClick={() => setSelectedShipmentId(s.shipment_id === selectedShipmentId ? null : s.shipment_id)}
                  className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                    s.shipment_id === selectedShipmentId 
                      ? 'bg-gray-800 border-shield-500' 
                      : 'bg-gray-900 border-gray-700 hover:border-gray-500'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="font-medium text-gray-200">Shipment #{s.shipment_id}</div>
                      <div className="text-sm text-gray-400 mt-1">Status: {s.status}</div>
                    </div>
                    <div className="flex gap-2">
                      {s.temperature_breach && (
                        <span className="px-2 py-1 bg-red-900/50 text-red-400 text-xs rounded border border-red-800 flex items-center gap-1">
                          <Thermometer className="w-3 h-3" /> Breach
                        </span>
                      )}
                    </div>
                  </div>
                  {s.summary && (
                    <div className="mt-3 text-sm text-gray-300 bg-gray-800 p-2 rounded">
                      {s.summary}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-200 mb-4">
            {selectedShipmentId ? `Sensor Readings (Shipment #${selectedShipmentId})` : 'Select a shipment to view readings'}
          </h2>
          {selectedShipmentId && (
            <div className="bg-gray-900 border border-gray-700 rounded-lg p-4">
              {readings.length === 0 ? (
                <p className="text-gray-400 text-sm">No sensor readings available.</p>
              ) : (
                <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2">
                  {readings.map((r, i) => (
                    <div key={i} className={`p-3 rounded border flex justify-between items-center ${
                      r.breach_detected ? 'bg-red-900/10 border-red-900/50' : 'bg-gray-800 border-gray-700'
                    }`}>
                      <div className="flex items-center gap-3">
                        <Activity className={`w-4 h-4 ${r.breach_detected ? 'text-red-400' : 'text-blue-400'}`} />
                        <div>
                          <div className="text-sm font-medium text-gray-200">
                            {r.temperature.toFixed(1)}°C / {r.humidity.toFixed(1)}% RH
                          </div>
                          <div className="text-xs text-gray-500">
                            {new Date(r.timestamp).toLocaleString()}
                          </div>
                        </div>
                      </div>
                      {r.breach_detected && (
                        <div className="text-xs text-red-400 font-medium">Out of Range</div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

export default ColdChain
