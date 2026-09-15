import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useBackendStatus } from '../hooks/useBackendStatus'
import { resilienceApi, type RRISummary } from '../api/resilience'
import { disruptionsApi, type DisruptionSummary } from '../api/disruptions'
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
  const [disruptions, setDisruptions] = useState<DisruptionSummary[]>([])
  const [disruptionError, setDisruptionError] = useState<string | null>(null)

  useEffect(() => {
    disruptionsApi.list()
      .then(setDisruptions)
      .catch((e) => setDisruptionError(String(e)))
  }, [])

  const active = disruptions.filter((disruption) => disruption.status === 'active' || disruption.status === 'monitoring')
  const totalExposure = active.reduce((sum, disruption) => sum + disruption.total_cargo_exposure_usd, 0)
  const critical = active.filter((disruption) => disruption.severity >= 7)
  const demo = disruptions.find((disruption) => disruption.disruption_code === 'DIS-001')

  return (
    <div className="p-6 space-y-6">
      <div className="rounded-xl border border-shield-700/50 bg-shield-950/30 px-5 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-widest text-shield-400 font-semibold">Live resilience posture</p>
          <p className="text-sm text-shield-100 mt-1">Deterministic RRI, wallet balances, disruption DNA, and cascade impact are calculated from the operational database.</p>
        </div>
        <Link to="/disruptions" className="shrink-0 rounded-lg bg-shield-600 hover:bg-shield-500 px-3 py-2 text-xs font-semibold text-white">Open Mumbai scenario →</Link>
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

      <section>
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">Disruption exposure</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            ['Active disruptions', String(active.length), 'currently active or being monitored'],
            ['Critical disruptions', String(critical.length), 'severity 7 or above'],
            ['Financial exposure', totalExposure >= 1_000_000 ? `$${(totalExposure / 1_000_000).toFixed(1)}M` : `$${Math.round(totalExposure / 1000)}K`, 'linked cargo value at risk'],
            ['Affected shipments', String(active.reduce((sum, disruption) => sum + disruption.affected_shipment_count, 0)), 'across live disruptions'],
          ].map(([label, value, hint]) => (
            <div key={label} className="rounded-xl border border-gray-800 bg-gray-900 p-4">
              <p className="text-[10px] uppercase tracking-widest text-gray-500">{label}</p>
              <p className="text-2xl font-bold text-white mt-2">{value}</p>
              <p className="text-[11px] text-gray-600 mt-1">{hint}</p>
            </div>
          ))}
        </div>
      </section>

      {demo && (
        <section className="rounded-xl border border-amber-800/50 bg-amber-950/20 p-5">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-amber-400">Demo scenario</p>
              <h2 className="text-lg font-bold text-white mt-1">{demo.name} <span className="font-mono text-sm text-gray-400">{demo.disruption_code}</span></h2>
              <p className="text-sm text-gray-400 mt-1">{demo.affected_region} · {demo.affected_shipment_count} affected shipments · ${demo.total_cargo_exposure_usd.toLocaleString()} exposure</p>
            </div>
            <Link to="/disruptions" className="text-sm font-semibold text-amber-300 hover:text-amber-100">Investigate disruption →</Link>
          </div>
        </section>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-800 bg-red-950/30 px-4 py-3 text-xs text-red-400">
          {error}
        </div>
      )}
      {disruptionError && <div className="rounded-lg border border-red-800 bg-red-950/30 px-4 py-3 text-xs text-red-400">{disruptionError}</div>}

    </div>
  )
}
