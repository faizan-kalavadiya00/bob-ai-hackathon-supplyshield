import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { shipmentsApi, type ShipmentSummary } from '../api/shipments'

function money(value: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value)
}

export function Shipments() {
  const [shipments, setShipments] = useState<ShipmentSummary[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    shipmentsApi.list().then(setShipments).catch((e) => setError(String(e)))
  }, [])

  return (
    <div className="p-6 max-w-6xl space-y-5">
      <div>
        <p className="text-xs uppercase tracking-widest text-shield-400 font-semibold">Operational exposure</p>
        <h2 className="text-xl font-bold text-white mt-1">Shipment investigation</h2>
        <p className="text-sm text-gray-500 mt-1">Select a shipment to view its deterministic resilience wallet and RRI.</p>
      </div>
      {error && <div className="rounded-lg border border-red-800 bg-red-950/30 p-3 text-sm text-red-300">{error}</div>}
      {!error && shipments.length === 0 && <p className="text-sm text-gray-500 animate-pulse">Loading shipment records…</p>}
      {shipments.length > 0 && (
        <div className="rounded-xl overflow-hidden border border-gray-800 bg-gray-900">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-800 text-left text-[11px] uppercase tracking-wide text-gray-500">
                <tr>{['Shipment', 'Route', 'Cargo', 'Exposure', 'Priority', 'Status', ''].map((h) => <th key={h} className="px-4 py-3 font-medium">{h}</th>)}</tr>
              </thead>
              <tbody>
                {shipments.map((shipment) => (
                  <tr key={shipment.id} className="border-t border-gray-800 hover:bg-gray-800/60">
                    <td className="px-4 py-3"><p className="font-mono font-semibold text-shield-300">{shipment.shipment_code}</p>{shipment.temperature_sensitive && <p className="text-[10px] text-cyan-400 mt-0.5">COLD-CHAIN</p>}</td>
                    <td className="px-4 py-3 text-gray-300 whitespace-nowrap">{shipment.origin} <span className="text-gray-600">→</span> {shipment.destination}</td>
                    <td className="px-4 py-3 text-gray-400">{shipment.cargo_type}</td>
                    <td className="px-4 py-3 text-gray-200 font-medium">{money(shipment.cargo_value_usd)}</td>
                    <td className="px-4 py-3"><span className="uppercase text-[11px] text-amber-300">{shipment.priority}</span></td>
                    <td className="px-4 py-3 text-gray-400 capitalize">{shipment.status.replace('_', ' ')}</td>
                    <td className="px-4 py-3 text-right"><Link to={`/resilience?shipment=${shipment.id}`} className="text-xs text-shield-300 hover:text-white">Inspect resilience →</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
