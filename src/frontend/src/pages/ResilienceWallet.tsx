/**
 * ResilienceWallet page — full wallet view for a selected shipment.
 * Consumes real backend API data. No mock values.
 */

import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { resilienceApi, type ResilienceResponse, type ResilienceTransaction } from '../api/resilience'
import { shipmentsApi, type ShipmentSummary } from '../api/shipments'
import { RRIGauge } from '../components/RRIGauge'
import { WalletDimensionCard } from '../components/WalletDimensionCard'

export function ResilienceWallet() {
  const [searchParams] = useSearchParams()
  const requestedShipment = Number(searchParams.get('shipment')) || null
  const [shipments, setShipments] = useState<ShipmentSummary[]>([])
  const [shipmentId, setShipmentId] = useState<number | null>(requestedShipment)
  const [data, setData] = useState<ResilienceResponse | null>(null)
  const [transactions, setTransactions] = useState<ResilienceTransaction[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    shipmentsApi.list()
      .then((records) => {
        setShipments(records)
        if (!requestedShipment) {
          setShipmentId(records.find((shipment) => shipment.shipment_code === 'S-1042')?.id ?? records[0]?.id ?? null)
        }
      })
      .catch((e) => setError(String(e)))
  }, [requestedShipment])

  useEffect(() => {
    if (shipmentId === null) return
    setLoading(true)
    setError(null)
    Promise.all([
      resilienceApi.getResilience(shipmentId),
      resilienceApi.getTransactions(shipmentId),
    ])
      .then(([res, txs]) => {
        setData(res)
        setTransactions(txs)
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false))
  }, [shipmentId])

  const handleRecalculate = () => {
    if (shipmentId === null) return
    setLoading(true)
    resilienceApi.recalculate(shipmentId)
      .then(setData)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false))
  }

  const rri = data?.rri
  const wallet = data?.wallet
  const selectableShipments = shipments
    .filter((shipment) => shipment.id === shipmentId || shipment.shipment_code === 'S-1042' || ['at_risk', 'delayed', 'in_transit'].includes(shipment.status))
    .sort((a, b) => (a.shipment_code === 'S-1042' ? -1 : b.shipment_code === 'S-1042' ? 1 : a.shipment_code.localeCompare(b.shipment_code)))
  const mostDepleted = wallet
    ? (['time', 'cost', 'temperature', 'capacity'] as const).map((dimension) => wallet[dimension]).sort((a, b) => a.dimension_score - b.dimension_score)[0]
    : null

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-gray-100">Resilience Wallet</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            SupplyShield Resilience Remaining Index (RRI) — deterministic backend calculation
          </p>
        </div>
        <button
          onClick={handleRecalculate}
          disabled={loading || shipmentId === null}
          className="text-xs px-3 py-1.5 rounded-lg bg-shield-600 hover:bg-shield-700
                     text-white disabled:opacity-50 transition-colors"
        >
          {loading ? 'Calculating…' : 'Recalculate'}
        </button>
      </div>

      {/* Shipment selector */}
      <div className="flex items-center gap-3">
        <label className="text-xs text-gray-500 shrink-0">Shipment:</label>
        <select
          value={shipmentId ?? ''}
          onChange={(e) => setShipmentId(Number(e.target.value))}
          className="text-sm bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5
                     text-gray-200 focus:outline-none focus:border-shield-500"
        >
          {selectableShipments.map((shipment) => (
            <option key={shipment.id} value={shipment.id}>
              {shipment.shipment_code} — {shipment.cargo_type} {shipment.origin}→{shipment.destination} ({shipment.priority.toUpperCase()})
            </option>
          ))}
        </select>
        {shipmentId !== null && (
          <span className="text-xs text-gray-600">DB id: {shipmentId}</span>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-950/50 border border-red-800 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && !data && (
        <div className="text-sm text-gray-500 animate-pulse">
          Loading resilience data from backend…
        </div>
      )}

      {/* No data yet */}
      {!loading && !data && !error && (
        <div className="rounded-lg border border-gray-800 bg-gray-900 px-4 py-8 text-center text-sm text-gray-500">
          {shipmentId === null
            ? 'Resolving shipment ID…'
            : 'No resilience data. Click Recalculate to initialise wallets.'}
        </div>
      )}

      {/* Main content */}
      {rri && wallet && (
        <>
          {/* RRI + status */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Gauge */}
            <div className="flex flex-col items-center justify-center rounded-xl bg-gray-900
                            border border-gray-800 p-6">
              <RRIGauge rri={rri.rri} status={rri.status} size={140} />
              <p className="text-xs text-gray-500 mt-2">SupplyShield RRI</p>
              {wallet.is_resilience_bankrupt && (
                <span className="mt-2 text-xs font-bold text-red-400 bg-red-950/50
                                 border border-red-800 rounded px-2 py-0.5">
                  RESILIENCE BANKRUPT
                </span>
              )}
            </div>

            {/* Explanation panel */}
            <div className="md:col-span-2 rounded-xl bg-gray-900 border border-gray-800 p-5 space-y-3">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
                RRI Breakdown
              </p>
              <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-sm">
                <span className="text-gray-500">Shipment</span>
                <span className="text-gray-200 font-mono">{wallet.shipment_code}</span>
                <span className="text-gray-500">Priority</span>
                <span className="text-gray-200 uppercase font-medium">{rri.shipment_priority}</span>
                <span className="text-gray-500">Weighted score</span>
                <span className="text-gray-200">{rri.weighted_score_before_adjustment.toFixed(2)}</span>
                <span className="text-gray-500">Criticality adj.</span>
                <span className={rri.criticality_adjustment < 0 ? 'text-red-400' : 'text-green-400'}>
                  {rri.criticality_adjustment >= 0 ? '+' : ''}{rri.criticality_adjustment.toFixed(2)}
                </span>
                <span className="text-gray-500">Final RRI</span>
                <span className="text-white font-bold text-base">{rri.rri.toFixed(2)}</span>
              </div>

              {/* Dimension weights */}
              <div className="pt-2 border-t border-gray-800">
                <p className="text-[10px] text-gray-600 uppercase tracking-widest mb-2">
                  Dimension weights
                </p>
                <div className="flex gap-4 flex-wrap text-xs">
                  {Object.entries(rri.weights).map(([dim, w]) => (
                    <span key={dim} className="text-gray-500">
                      <span className="text-gray-300">{dim}</span> {(w * 100).toFixed(0)}%
                    </span>
                  ))}
                </div>
              </div>
              {mostDepleted && (
                <div className="rounded-lg border border-gray-800 bg-gray-950/50 px-3 py-2 text-xs">
                  <span className="text-gray-500">Primary resilience pressure: </span>
                  <span className="font-semibold text-amber-300 uppercase">{mostDepleted.dimension}</span>
                  <span className="text-gray-400"> retains {mostDepleted.dimension_score.toFixed(0)}% of its available budget.</span>
                </div>
              )}
            </div>
          </div>

          {/* Four wallet dimensions */}
          <div>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
              Wallet Dimensions
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {(['time', 'cost', 'temperature', 'capacity'] as const).map((dim) => (
                <WalletDimensionCard key={dim} dim={wallet[dim]} />
              ))}
            </div>
          </div>

          {/* Contributors */}
          {rri.contributors.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
                Explanation
              </h3>
              <div className="space-y-2">
                {rri.contributors.map((c, i) => (
                  <div key={i} className="flex items-start gap-3 rounded-lg bg-gray-900
                                          border border-gray-800 px-4 py-2.5">
                    <span className={`text-xs font-mono mt-0.5 w-12 text-right shrink-0 ${
                      c.impact < 0 ? 'text-red-400' : 'text-green-400'
                    }`}>
                      {c.impact >= 0 ? '+' : ''}{c.impact.toFixed(2)}
                    </span>
                    <div>
                      <span className="text-xs font-semibold text-gray-200 capitalize">
                        {c.factor}
                      </span>
                      <p className="text-xs text-gray-500 mt-0.5">{c.reason}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Transaction history */}
          {transactions.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
                Transaction History
              </h3>
              <div className="rounded-xl border border-gray-800 overflow-hidden">
                <table className="w-full text-xs">
                  <thead className="bg-gray-900 text-gray-500">
                    <tr>
                      <th className="text-left px-4 py-2">Dimension</th>
                      <th className="text-right px-4 py-2">Amount</th>
                      <th className="text-left px-4 py-2">Reason</th>
                      <th className="text-left px-4 py-2">Ref</th>
                      <th className="text-left px-4 py-2">Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transactions.slice(0, 20).map((tx) => (
                      <tr key={tx.id} className="border-t border-gray-800 hover:bg-gray-900/50">
                        <td className="px-4 py-2 text-gray-300 capitalize">{tx.dimension}</td>
                        <td className={`px-4 py-2 text-right font-mono ${
                          tx.amount < 0 ? 'text-red-400' : 'text-green-400'
                        }`}>
                          {tx.amount >= 0 ? '+' : ''}{tx.amount.toFixed(2)}
                        </td>
                        <td className="px-4 py-2 text-gray-500 max-w-xs truncate">
                          {tx.reason}
                        </td>
                        <td className="px-4 py-2 text-gray-600 font-mono">
                          {tx.reference_id ?? '—'}
                        </td>
                        <td className="px-4 py-2 text-gray-600">
                          {new Date(tx.timestamp).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
