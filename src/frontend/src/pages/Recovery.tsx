import { useState } from 'react'
import { recoveryApi, type RecoveryPlan } from '../api/recovery'

export function Recovery() {
  const [lookupId, setLookupId] = useState('')
  const [lookupType, setLookupType] = useState<'disruption' | 'shipment'>('disruption')
  const [plan, setPlan] = useState<RecoveryPlan | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFetch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!lookupId.trim()) return

    setLoading(true)
    setError(null)
    setPlan(null)
    try {
      const res = lookupType === 'disruption' 
        ? await recoveryApi.getPlanByDisruption(lookupId)
        : await recoveryApi.getPlanByShipment(lookupId)
      
      // Sort steps by impact/RRI improvement (descending)
      res.steps = [...res.steps].sort((a, b) => b.rri_improvement - a.rri_improvement)
      setPlan(res)
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 max-w-6xl space-y-6">
      <div>
        <p className="text-xs uppercase tracking-widest text-shield-400 font-semibold">Phase 2 Module</p>
        <h2 className="text-xl font-bold text-white mt-1">Recovery Planning</h2>
        <p className="text-sm text-gray-500 mt-1">Generate and view deterministic recovery plans.</p>
      </div>

      <div className="rounded-xl border border-gray-800 bg-gray-900 p-5">
        <form onSubmit={handleFetch} className="flex flex-col sm:flex-row gap-4 items-end">
          <div className="flex-1 w-full">
            <label className="block text-xs uppercase text-gray-500 mb-1">Lookup Type</label>
            <select
              value={lookupType}
              onChange={(e) => setLookupType(e.target.value as 'disruption' | 'shipment')}
              className="w-full bg-gray-800 border border-gray-700 text-sm text-gray-200 rounded p-2 focus:border-shield-500 focus:outline-none"
            >
              <option value="disruption">By Disruption ID</option>
              <option value="shipment">By Shipment ID</option>
            </select>
          </div>
          <div className="flex-[2] w-full">
            <label className="block text-xs uppercase text-gray-500 mb-1">{lookupType === 'disruption' ? 'Disruption ID' : 'Shipment ID'}</label>
            <input
              type="text"
              value={lookupId}
              onChange={(e) => setLookupId(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 text-sm text-gray-200 rounded p-2 focus:border-shield-500 focus:outline-none"
              placeholder={`Enter ${lookupType} ID (e.g. DIS-001)`}
            />
          </div>
          <button
            type="submit"
            disabled={loading || !lookupId.trim()}
            className="bg-shield-600 hover:bg-shield-500 disabled:opacity-50 text-white text-sm font-semibold px-6 py-2 rounded transition-colors"
          >
            {loading ? 'Loading...' : 'Load Plan'}
          </button>
        </form>
        {error && <div className="mt-4 p-3 rounded bg-red-950/50 border border-red-800 text-xs text-red-300">{error}</div>}
      </div>

      {plan && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
              <p className="text-[10px] uppercase tracking-widest text-gray-500">Total Cost</p>
              <p className="text-2xl font-bold text-white mt-2">${plan.total_cost_usd.toLocaleString()}</p>
            </div>
            <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
              <p className="text-[10px] uppercase tracking-widest text-gray-500">RRI Improvement</p>
              <p className="text-2xl font-bold text-green-400 mt-2">+{plan.total_rri_improvement.toFixed(1)}</p>
            </div>
            <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
              <p className="text-[10px] uppercase tracking-widest text-gray-500">Total Steps</p>
              <p className="text-2xl font-bold text-white mt-2">{plan.steps.length}</p>
            </div>
          </div>

          <div className="rounded-xl overflow-hidden border border-gray-800 bg-gray-900">
            <div className="px-5 py-4 border-b border-gray-800 bg-gray-800/50">
              <h3 className="text-sm font-semibold text-gray-200">Recommended Steps</h3>
              <p className="text-xs text-gray-500 mt-1">Ordered by RRI impact</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-800/30 text-left text-[11px] uppercase tracking-wide text-gray-500">
                  <tr>
                    <th className="px-5 py-3 font-medium">Action</th>
                    <th className="px-5 py-3 font-medium">Est. Cost</th>
                    <th className="px-5 py-3 font-medium">Time (Days)</th>
                    <th className="px-5 py-3 font-medium">RRI Gain</th>
                    <th className="px-5 py-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {plan.steps.map((step) => (
                    <tr key={step.id} className="border-t border-gray-800 hover:bg-gray-800/40">
                      <td className="px-5 py-3">
                        <p className="font-medium text-gray-200">{step.action}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{step.description}</p>
                      </td>
                      <td className="px-5 py-3 text-gray-300 font-mono">${step.estimated_cost_usd.toLocaleString()}</td>
                      <td className="px-5 py-3 text-gray-400">{step.time_to_implement_days}</td>
                      <td className="px-5 py-3 text-green-400 font-semibold">+{step.rri_improvement.toFixed(1)}</td>
                      <td className="px-5 py-3">
                        <span className={`inline-block px-2 py-1 rounded text-[10px] uppercase font-semibold ${
                          step.status === 'completed' ? 'bg-green-900/50 text-green-400 border border-green-800' :
                          step.status === 'in_progress' ? 'bg-blue-900/50 text-blue-400 border border-blue-800' :
                          'bg-gray-800 text-gray-400 border border-gray-700'
                        }`}>
                          {step.status.replace('_', ' ')}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
