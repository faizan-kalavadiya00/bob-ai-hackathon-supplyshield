import { useState } from 'react'
import { simulationApi, type SimulationParams, type SimulationResult } from '../api/simulation'

export function Simulation() {
  const [params, setParams] = useState<SimulationParams>({
    type: 'port_strike',
    severity: 'high',
    region: 'Asia',
    duration_days: 7,
  })
  const [result, setResult] = useState<SimulationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSimulate = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await simulationApi.simulate({
        ...params,
        duration_days: Number(params.duration_days),
      })
      setResult(res)
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
        <h2 className="text-xl font-bold text-white mt-1">Disruption Simulation</h2>
        <p className="text-sm text-gray-500 mt-1">Configure scenario parameters to simulate disruption impact.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-1 rounded-xl bg-gray-900 border border-gray-800 p-5">
          <form onSubmit={handleSimulate} className="space-y-4">
            <div>
              <label className="block text-xs uppercase text-gray-500 mb-1">Disruption Type</label>
              <select
                value={params.type}
                onChange={(e) => setParams({ ...params, type: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 text-sm text-gray-200 rounded p-2 focus:border-shield-500 focus:outline-none"
              >
                <option value="port_strike">Port Strike</option>
                <option value="weather_event">Weather Event</option>
                <option value="geopolitical">Geopolitical Tension</option>
                <option value="cyber_attack">Cyber Attack</option>
              </select>
            </div>
            <div>
              <label className="block text-xs uppercase text-gray-500 mb-1">Severity</label>
              <select
                value={params.severity}
                onChange={(e) => setParams({ ...params, severity: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 text-sm text-gray-200 rounded p-2 focus:border-shield-500 focus:outline-none"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
            <div>
              <label className="block text-xs uppercase text-gray-500 mb-1">Region</label>
              <input
                type="text"
                value={params.region}
                onChange={(e) => setParams({ ...params, region: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 text-sm text-gray-200 rounded p-2 focus:border-shield-500 focus:outline-none"
                placeholder="e.g. Asia, Europe"
              />
            </div>
            <div>
              <label className="block text-xs uppercase text-gray-500 mb-1">Duration (Days)</label>
              <input
                type="number"
                min="1"
                value={params.duration_days}
                onChange={(e) => setParams({ ...params, duration_days: parseInt(e.target.value) || 0 })}
                className="w-full bg-gray-800 border border-gray-700 text-sm text-gray-200 rounded p-2 focus:border-shield-500 focus:outline-none"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-shield-600 hover:bg-shield-500 disabled:opacity-50 text-white text-sm font-semibold py-2 rounded transition-colors mt-2"
            >
              {loading ? 'Simulating...' : 'Run Simulation'}
            </button>
          </form>
          {error && <div className="mt-4 p-3 rounded bg-red-950/50 border border-red-800 text-xs text-red-300">{error}</div>}
        </div>

        <div className="md:col-span-2 space-y-4">
          {!result && !loading && (
            <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-10 flex items-center justify-center h-full">
              <p className="text-sm text-gray-500">Run a simulation to view impact metrics.</p>
            </div>
          )}
          {loading && (
            <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-10 flex items-center justify-center h-full">
              <p className="text-sm text-shield-500 animate-pulse">Running scenario engine...</p>
            </div>
          )}
          {result && (
            <div className="rounded-xl border border-gray-800 bg-gray-900 p-5 space-y-6">
              <div>
                <p className="text-xs uppercase tracking-widest text-shield-400 font-semibold mb-3">Simulation Results</p>
                <p className="text-sm text-gray-400">Scenario ID: <span className="font-mono text-gray-300">{result.scenario_id}</span></p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-lg bg-gray-800/50 border border-gray-700">
                  <p className="text-xs font-semibold text-gray-500 uppercase mb-3">Before</p>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-400">OTD Rate</span>
                      <span className="text-sm text-gray-200 font-medium">{(result.before.on_time_delivery_rate * 100).toFixed(1)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-400">Cost Impact</span>
                      <span className="text-sm text-gray-200 font-medium">${result.before.cost_impact_usd.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-400">Avg Delay</span>
                      <span className="text-sm text-gray-200 font-medium">{result.before.average_delay_days} days</span>
                    </div>
                  </div>
                </div>

                <div className="p-4 rounded-lg bg-red-950/20 border border-red-900/30">
                  <p className="text-xs font-semibold text-red-500 uppercase mb-3">After</p>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-400">OTD Rate</span>
                      <span className="text-sm text-red-300 font-medium">{(result.after.on_time_delivery_rate * 100).toFixed(1)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-400">Cost Impact</span>
                      <span className="text-sm text-red-300 font-medium">${result.after.cost_impact_usd.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-400">Avg Delay</span>
                      <span className="text-sm text-red-300 font-medium">{result.after.average_delay_days} days</span>
                    </div>
                  </div>
                </div>
              </div>

              {result.insights && result.insights.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase mb-2">AI Insights</p>
                  <ul className="list-disc list-inside text-sm text-gray-400 space-y-1">
                    {result.insights.map((insight, idx) => (
                      <li key={idx}>{insight}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
