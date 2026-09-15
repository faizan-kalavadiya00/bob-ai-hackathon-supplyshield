/**
 * Disruptions — Enterprise disruption command center (Phase 4B).
 *
 * Shows active and historical disruptions from the real database.
 * Selecting a disruption reveals detail, DNA fingerprint,
 * cascading impact view, and similar historical events.
 *
 * All values are database-backed. No hardcoded figures.
 */

import { useEffect, useState, useCallback } from 'react'
import {
  disruptionsApi,
  type DisruptionSummary,
  type DisruptionDetail,
  type SimilarityResult,
  type DisruptionImpact,
} from '../api/disruptions'
import { SeverityBadge, StatusBadge, TypeBadge } from '../components/DisruptionBadges'
import { DNAPanel } from '../components/DNAPanel'
import { SimilarityPanel } from '../components/SimilarityPanel'
import { CascadeView } from '../components/CascadeView'

// ── Helpers ──────────────────────────────────────────────────────────────────

function fmtUSD(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000)     return `$${(n / 1_000).toFixed(0)}K`
  return `$${n.toFixed(0)}`
}

function duration(d: DisruptionSummary): string {
  const h = d.duration_hours
  if (h > 720) return `${(h / 720).toFixed(1)} mo`
  if (h > 24)  return `${(h / 24).toFixed(1)} d`
  return `${h.toFixed(0)}h`
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 px-4 py-3">
      <p className="text-[10px] text-gray-500 uppercase tracking-wide mb-0.5">{label}</p>
      <p className="text-lg font-bold text-white">{value}</p>
      {sub && <p className="text-[10px] text-gray-500">{sub}</p>}
    </div>
  )
}

function DisruptionCard({
  dis,
  selected,
  onClick,
}: {
  dis: DisruptionSummary
  selected: boolean
  onClick: () => void
}) {
  const borderColor = selected ? 'border-shield-500' : 'border-gray-700 hover:border-gray-500'
  const bg = selected ? 'bg-gray-750 bg-opacity-80' : 'bg-gray-800'

  return (
    <button
      onClick={onClick}
      className={`w-full text-left rounded-xl border ${borderColor} ${bg}
        p-4 transition-colors cursor-pointer`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="min-w-0">
          <p className="text-xs font-semibold text-white truncate">{dis.name}</p>
          <p className="text-[10px] text-gray-500 font-mono">{dis.disruption_code}</p>
        </div>
        <SeverityBadge severity={dis.severity} className="shrink-0" />
      </div>

      <div className="flex items-center gap-1.5 flex-wrap mb-2">
        <StatusBadge status={dis.status} />
        <TypeBadge type={dis.type} />
      </div>

      <p className="text-[11px] text-gray-400 mb-2 line-clamp-2">{dis.affected_region}</p>

      <div className="grid grid-cols-2 gap-1 text-[10px]">
        <div>
          <span className="text-gray-500">Ships affected: </span>
          <span className="text-gray-300">{dis.affected_shipment_count}</span>
        </div>
        <div>
          <span className="text-gray-500">Cargo: </span>
          <span className="text-gray-300">{fmtUSD(dis.total_cargo_exposure_usd)}</span>
        </div>
        <div>
          <span className="text-gray-500">Delay: </span>
          <span className="text-gray-300">{dis.total_delay_hours.toFixed(0)}h total</span>
        </div>
        <div>
          <span className="text-gray-500">Duration: </span>
          <span className="text-gray-300">{duration(dis)}</span>
        </div>
      </div>
    </button>
  )
}

function DisruptionDetailPane({
  detail,
  similar,
  impact,
  loading,
}: {
  detail: DisruptionDetail
  similar: SimilarityResult[]
  impact: DisruptionImpact | null
  loading: boolean
}) {
  return (
    <div className="space-y-5">
      {/* Overview */}
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h2 className="text-base font-bold text-white">{detail.name}</h2>
            </div>
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-xs text-gray-500 font-mono">{detail.disruption_code}</span>
              <TypeBadge type={detail.type} />
              <StatusBadge status={detail.status} />
            </div>
          </div>
          <SeverityBadge severity={detail.severity} />
        </div>

        {detail.description && (
          <p className="text-sm text-gray-300 mb-4 leading-relaxed">{detail.description}</p>
        )}

        {/* KPI row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <StatCard
            label="Duration"
            value={detail.duration_hours > 24
              ? `${(detail.duration_hours / 24).toFixed(1)}d`
              : `${detail.duration_hours.toFixed(0)}h`}
            sub={`${detail.duration_hours.toFixed(0)} hours`}
          />
          <StatCard
            label="Affected shipments"
            value={String(detail.affected_shipment_count)}
            sub={`${detail.temperature_sensitive_count} cold-chain`}
          />
          <StatCard
            label="Cargo exposure"
            value={fmtUSD(detail.total_cargo_exposure_usd)}
            sub={`avg impact ${(detail.avg_impact_score * 100).toFixed(0)}%`}
          />
          <StatCard
            label="Total delay"
            value={`${detail.total_delay_hours.toFixed(0)}h`}
            sub={`${(detail.total_delay_hours / 24).toFixed(1)} day-equiv`}
          />
        </div>

        {/* Timing */}
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
          <div>
            <span className="text-gray-500">Region: </span>
            <span className="text-gray-200">{detail.affected_region}</span>
          </div>
          <div>
            <span className="text-gray-500">Started: </span>
            <span className="text-gray-200">
              {new Date(detail.start_time).toLocaleString()}
            </span>
          </div>
          {detail.end_time && (
            <div>
              <span className="text-gray-500">Ended: </span>
              <span className="text-gray-200">
                {new Date(detail.end_time).toLocaleString()}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* DNA Panel */}
      {detail.dna && <DNAPanel dna={detail.dna} />}

      {/* Similar Historical */}
      {loading ? (
        <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
          <p className="text-xs text-gray-500 animate-pulse">Loading similar disruptions...</p>
        </div>
      ) : (
        <SimilarityPanel results={similar} subjectName={detail.name} />
      )}

      {/* Cascade View */}
      {impact && <CascadeView cascade={impact.cascade} />}

      {/* Affected Shipments table */}
      {impact && impact.affected_shipments.length > 0 && (
        <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
          <h3 className="text-sm font-semibold text-white mb-3">
            Affected Shipments ({impact.affected_shipments.length})
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="border-b border-gray-700 text-left">
                  {['Code', 'Route', 'Cargo', 'Value', 'Priority', 'Impact', 'Delay', 'Cold'].map(h => (
                    <th key={h} className="pb-2 pr-3 text-gray-500 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {impact.affected_shipments.map(s => (
                  <tr key={s.shipment_id} className="border-b border-gray-700/50 hover:bg-gray-700/20">
                    <td className="py-1.5 pr-3 font-mono text-blue-300">{s.shipment_code}</td>
                    <td className="py-1.5 pr-3 text-gray-300">{s.origin} → {s.destination}</td>
                    <td className="py-1.5 pr-3 text-gray-400">{s.cargo_type}</td>
                    <td className="py-1.5 pr-3 text-gray-300">{fmtUSD(s.cargo_value_usd)}</td>
                    <td className="py-1.5 pr-3">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                        s.priority === 'critical' ? 'bg-red-900/50 text-red-300' :
                        s.priority === 'high'     ? 'bg-amber-900/50 text-amber-300' :
                                                    'bg-gray-700 text-gray-400'
                      }`}>
                        {s.priority.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-1.5 pr-3 text-gray-300">{(s.impact_score * 100).toFixed(0)}%</td>
                    <td className="py-1.5 pr-3 text-gray-300">{s.delay_hours.toFixed(0)}h</td>
                    <td className="py-1.5 pr-3">
                      {s.temperature_sensitive
                        ? <span className="text-cyan-400">COLD</span>
                        : <span className="text-gray-600">—</span>}
                    </td>
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

// ── Main page ─────────────────────────────────────────────────────────────────

type Filter = 'all' | 'active' | 'monitoring' | 'historical' | 'resolved'

export function Disruptions() {
  const [disruptions, setDisruptions] = useState<DisruptionSummary[]>([])
  const [filter, setFilter] = useState<Filter>('all')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [detail, setDetail] = useState<DisruptionDetail | null>(null)
  const [similar, setSimilar] = useState<SimilarityResult[]>([])
  const [impact, setImpact] = useState<DisruptionImpact | null>(null)
  const [listLoading, setListLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [similarLoading, setSimilarLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load disruption list
  useEffect(() => {
    setListLoading(true)
    const statusParam = filter === 'all' ? undefined : filter
    disruptionsApi.list(statusParam)
      .then(data => {
        setDisruptions(data)
        setListLoading(false)
        // Auto-select DIS-001 (Mumbai Port Crisis) on first load
        if (filter === 'all' && data.length > 0 && selectedId === null) {
          const demo = data.find(d => d.disruption_code === 'DIS-001') ?? data[0]
          setSelectedId(demo.id)
        }
      })
      .catch(err => {
        setError(String(err))
        setListLoading(false)
      })
  }, [filter])

  // Load detail + similar + impact when selection changes
  const loadDetail = useCallback((id: number) => {
    setDetailLoading(true)
    setSimilarLoading(true)
    setDetail(null)
    setSimilar([])
    setImpact(null)

    disruptionsApi.get(id)
      .then(d => { setDetail(d); setDetailLoading(false) })
      .catch(() => setDetailLoading(false))

    disruptionsApi.getSimilar(id)
      .then(s => { setSimilar(s); setSimilarLoading(false) })
      .catch(() => setSimilarLoading(false))

    disruptionsApi.getImpact(id)
      .then(imp => setImpact(imp))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (selectedId !== null) loadDetail(selectedId)
  }, [selectedId, loadDetail])

  // Aggregate stats
  const activeCount = disruptions.filter(d => d.status === 'active').length
  const monitoringCount = disruptions.filter(d => d.status === 'monitoring').length
  const totalCargo = disruptions
    .filter(d => d.status === 'active' || d.status === 'monitoring')
    .reduce((s, d) => s + d.total_cargo_exposure_usd, 0)
  const totalAffectedShips = disruptions
    .filter(d => d.status === 'active')
    .reduce((s, d) => s + d.affected_shipment_count, 0)

  const FILTERS: { key: Filter; label: string }[] = [
    { key: 'all',        label: 'All' },
    { key: 'active',     label: 'Active' },
    { key: 'monitoring', label: 'Monitoring' },
    { key: 'historical', label: 'Historical' },
    { key: 'resolved',   label: 'Resolved' },
  ]

  return (
    <div className="p-6 min-h-full bg-gray-900">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-xl font-bold text-white">Disruption Command Center</h1>
        <p className="text-sm text-gray-400 mt-1">
          Real-time disruption monitoring with Disruption DNA fingerprinting and historical playbook comparison
        </p>
      </div>

      {/* System stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Active disruptions"
          value={String(activeCount)}
          sub="Require immediate action"
        />
        <StatCard
          label="Under monitoring"
          value={String(monitoringCount)}
          sub="Elevated watch"
        />
        <StatCard
          label="Active cargo at risk"
          value={fmtUSD(totalCargo)}
          sub="Active + monitoring"
        />
        <StatCard
          label="Shipments affected"
          value={String(totalAffectedShips)}
          sub="Active disruptions only"
        />
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 mb-4">
        {FILTERS.map(f => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              filter === f.key
                ? 'bg-shield-600/40 text-shield-300 ring-1 ring-shield-500'
                : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-900/30 border border-red-700 px-4 py-3 text-sm text-red-300">
          Backend unavailable: {error}. Start the FastAPI server to load live data.
        </div>
      )}

      {/* Two-column layout: list + detail */}
      <div className="grid grid-cols-1 xl:grid-cols-[380px_1fr] gap-5">
        {/* Left: disruption list */}
        <div className="space-y-2 max-h-[calc(100vh-320px)] overflow-y-auto pr-1">
          {listLoading && (
            <p className="text-xs text-gray-500 animate-pulse px-2">Loading disruptions...</p>
          )}
          {!listLoading && disruptions.length === 0 && (
            <p className="text-xs text-gray-500 px-2">No disruptions found.</p>
          )}
          {disruptions.map(dis => (
            <DisruptionCard
              key={dis.id}
              dis={dis}
              selected={dis.id === selectedId}
              onClick={() => setSelectedId(dis.id)}
            />
          ))}
        </div>

        {/* Right: detail pane */}
        <div className="max-h-[calc(100vh-320px)] overflow-y-auto pr-1">
          {detailLoading && (
            <div className="bg-gray-800 rounded-xl border border-gray-700 p-8 text-center">
              <p className="text-sm text-gray-500 animate-pulse">Loading disruption detail...</p>
            </div>
          )}
          {!detailLoading && detail === null && !error && (
            <div className="bg-gray-800 rounded-xl border border-gray-700 p-8 text-center">
              <p className="text-sm text-gray-500">Select a disruption to view details.</p>
            </div>
          )}
          {!detailLoading && detail !== null && (
            <DisruptionDetailPane
              detail={detail}
              similar={similar}
              impact={impact}
              loading={similarLoading}
            />
          )}
        </div>
      </div>
    </div>
  )
}
