import { useEffect, useState } from 'react'
import { useBackendStatus } from '../hooks/useBackendStatus'
import { resilienceApi, type RRISummary } from '../api/resilience'
import { RRIGauge } from '../components/RRIGauge'

function useRRISummary() {
  const [summary, setSummary] = useState<RRISummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    resilienceApi.getSummary()
      .then(setSummary)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])
  return { summary, loading, error, refresh: load }
}

function SystemStatusCard() {
  const { state, health } = useBackendStatus()
  const statusMap = {
    checking:    { label: 'Checking…',    color: 'text-yellow-400', dot: 'bg-yellow-400 animate-pulse' },
    connected:   { label: 'Operational',  color: 'text-green-400',  dot: 'bg-green-400' },
    unreachable: { label: 'Unreachable',  color: 'text-red-400',    dot: 'bg-red-400' },
  }
  const cfg = statusMap[state]

  return (
    <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
      <p className="text-xs text-gray-500 uppercase tracking-widest mb-3">Backend Status</p>
      <div className="flex items-center gap-2 mb-3">
        <span className={`inline-block w-2.5 h-2.5 rounded-full ${cfg.dot}`} />
        <span className={`font-semibold text-sm ${cfg.color}`}>{cfg.label}</span>
      </div>
      {health ? (
        <p className="text-xs text-gray-600">
          {health.service} v{health.version} ({health.environment})
        </p>
      ) : (
        <p className="text-xs text-gray-600">
          {state === 'unreachable' ? 'Start the FastAPI backend to connect.' : 'Connecting…'}
        </p>
      )}
    </div>
  )
}

function RRISummaryCard({ summary, loading }: { summary: RRISummary | null; loading: boolean }) {
  if (loading && !summary) {
    return (
      <div className="rounded-xl bg-gray-900 border border-gray-800 p-5 flex items-center justify-center">
        <p className="text-xs text-gray-500 animate-pulse">Calculating RRI…</p>
      </div>
    )
  }
  if (!summary) {
    return (
      <div className="rounded-xl bg-gray-900 border border-gray-800 p-5">
        <p className="text-xs text-gray-500 uppercase tracking-widest mb-2">Network RRI</p>
        <p className="text-2xl font-bold text-gray-600">—</p>
        <p className="text-xs text-gray-600 mt-1">Backend not reachable</p>
      </div>
    )
  }
  return (
    <div className="rounded-xl bg-gray-900 border border-gray-800 p-5 flex items-center gap-4">
      <RRIGauge rri={summary.average_rri} status={_summaryStatus(summary.average_rri)} size={90} />
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-widest mb-1">Avg Network RRI</p>
        <p className="text-xs text-gray-600">
          {summary.total_shipments_assessed} active shipments assessed
        </p>
        {summary.resilience_bankruptcies > 0 && (
          <p className="text-xs text-red-400 font-semibold mt-1">
            {summary.resilience_bankruptcies} resilience bankruptcies
          </p>
        )}
      </div>
    </div>
  )
}

function _summaryStatus(rri: number): string {
  if (rri >= 75) return 'HEALTHY'
  if (rri >= 50) return 'STRESSED'
  if (rri >= 25) return 'VULNERABLE'
  if (rri >= 10) return 'CRITICAL'
  return 'BANKRUPT'
}

function StatusCountsRow({ summary }: { summary: RRISummary }) {
  const counts = [
    { label: 'Healthy',    n: summary.healthy_count,    color: 'text-green-400' },
    { label: 'Stressed',   n: summary.stressed_count,   color: 'text-yellow-400' },
    { label: 'Vulnerable', n: summary.vulnerable_count, color: 'text-orange-400' },
    { label: 'Critical',   n: summary.critical_count,   color: 'text-red-400' },
    { label: 'Bankrupt',   n: summary.bankrupt_count,   color: 'text-red-900' },
  ]
  return (
    <div className="grid grid-cols-5 gap-2">
      {counts.map((c) => (
        <div key={c.label} className="rounded-xl bg-gray-900 border border-gray-800 p-4 text-center">
          <p className={`text-xl font-bold ${c.color}`}>{c.n}</p>
          <p className="text-[10px] text-gray-500 mt-1">{c.label}</p>
        </div>
      ))}
    </div>
  )
}

export function Dashboard() {
  const { summary, loading, error, refresh } = useRRISummary()

  return (
    <div className="p-6 space-y-6">
      {/* Phase banner */}
      <div className="rounded-lg border border-shield-700/50 bg-shield-950/30 px-4 py-3 text-sm text-shield-300">
        <strong className="font-semibold">Phase 3 — Resilience Wallet + RRI.</strong>
        {' '}Network RRI is calculated deterministically from {summary?.total_shipments_assessed ?? '…'} active shipments.
      </div>

      {/* System + RRI summary */}
      <section>
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
          System
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SystemStatusCard />
          <RRISummaryCard summary={summary} loading={loading} />
        </div>
      </section>

      {/* RRI status distribution */}
      {summary && (
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
              Shipment Resilience Distribution
            </h2>
            <button
              onClick={refresh}
              className="text-xs text-gray-600 hover:text-gray-400 transition-colors"
            >
              Refresh
            </button>
          </div>
          <StatusCountsRow summary={summary} />
        </section>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-800 bg-red-950/30 px-4 py-3 text-xs text-red-400">
          {error}
        </div>
      )}

      {/* Capability map */}
      <section>
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
          Capability Areas
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {[
            { icon: '🛡', label: 'Resilience Wallet',     phase: 3, done: true  },
            { icon: '📊', label: 'RRI Engine',            phase: 3, done: true  },
            { icon: '🚢', label: 'Shipment Tracking',     phase: 4, done: false },
            { icon: '⚡', label: 'Disruption Management', phase: 4, done: false },
            { icon: '🚛', label: 'Fleet Optimization',    phase: 4, done: false },
            { icon: '❄',  label: 'Cold-Chain Monitor',   phase: 4, done: false },
            { icon: '🔬', label: 'Disruption Simulation', phase: 4, done: false },
            { icon: '♻',  label: 'Recovery Planning',    phase: 4, done: false },
            { icon: '🤖', label: 'IBM Bob / MCP Agent',  phase: 5, done: false },
          ].map((area) => (
            <div
              key={area.label}
              className={`flex items-center gap-3 rounded-lg border px-4 py-3 text-sm ${
                area.done
                  ? 'bg-shield-900/30 border-shield-700/50 text-shield-300'
                  : 'bg-gray-900 border-gray-800 text-gray-400'
              }`}
            >
              <span className="text-lg" aria-hidden="true">{area.icon}</span>
              <span className="flex-1">{area.label}</span>
              {area.done ? (
                <span className="text-[10px] text-shield-400 bg-shield-900/50 rounded px-1.5 py-0.5">
                  Live
                </span>
              ) : (
                <span className="text-[10px] text-gray-600 bg-gray-800 rounded px-1.5 py-0.5">
                  Phase {area.phase}
                </span>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
