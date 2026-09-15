/**
 * DNAPanel — displays a Disruption DNA fingerprint as a visual bar chart.
 * Each DNA dimension is shown with its normalized score as a horizontal bar.
 */

import type { DNARecord } from '../api/disruptions'

interface Props {
  dna: DNARecord
}

const DIMENSIONS: { key: keyof DNARecord; label: string; unit: string }[] = [
  { key: 'type_score',           label: 'Type Severity',    unit: 'type' },
  { key: 'severity_score',       label: 'Severity',         unit: 'score' },
  { key: 'duration_score',       label: 'Duration',         unit: 'log-norm' },
  { key: 'geo_scope_score',      label: 'Geographic Scope', unit: 'scope' },
  { key: 'transport_mode_score', label: 'Transport Mode',   unit: 'mode' },
  { key: 'capacity_impact_score',label: 'Capacity Impact',  unit: 'impact' },
  { key: 'port_relevance_score', label: 'Port Relevance',   unit: 'relevance' },
  { key: 'region_score',         label: 'Region Affinity',  unit: 'hash-bucket' },
]

function scoreColor(score: number): string {
  if (score >= 0.8) return 'bg-red-500'
  if (score >= 0.6) return 'bg-amber-500'
  if (score >= 0.4) return 'bg-yellow-500'
  if (score >= 0.2) return 'bg-blue-500'
  return 'bg-gray-500'
}

export function DNAPanel({ dna }: Props) {
  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-white">Disruption DNA</h3>
          <p className="text-[11px] text-gray-500 mt-0.5">
            Deterministic fingerprint — no ML, no LLM
          </p>
        </div>
        <div className="text-right">
          <span className="text-[11px] text-gray-500">Transport mode</span>
          <p className="text-xs font-semibold text-blue-300 uppercase">
            {dna.transport_mode_label}
          </p>
        </div>
      </div>

      {/* Bar chart */}
      <div className="space-y-2">
        {DIMENSIONS.map(({ key, label }) => {
          const raw = dna[key]
          const score = typeof raw === 'number' ? raw : 0
          const pct = Math.round(score * 100)
          return (
            <div key={key}>
              <div className="flex justify-between mb-0.5">
                <span className="text-[11px] text-gray-400">{label}</span>
                <span className="text-[11px] text-gray-300 font-mono">{pct}%</span>
              </div>
              <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${scoreColor(score)}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>

      {/* Labels row */}
      <div className="mt-4 grid grid-cols-2 gap-2 text-[11px]">
        <div className="bg-gray-700/50 rounded px-2 py-1.5">
          <span className="text-gray-500">Geo Scope</span>
          <p className="text-white font-medium">{dna.geo_scope_label}</p>
        </div>
        <div className="bg-gray-700/50 rounded px-2 py-1.5">
          <span className="text-gray-500">Port Relevance</span>
          <p className="text-white font-medium">{(dna.port_relevance_score * 100).toFixed(0)}%</p>
        </div>
        <div className="bg-gray-700/50 rounded px-2 py-1.5">
          <span className="text-gray-500">Duration</span>
          <p className="text-white font-medium">{dna.duration_hours.toFixed(0)}h</p>
        </div>
        <div className="bg-gray-700/50 rounded px-2 py-1.5">
          <span className="text-gray-500">Affected Shipments</span>
          <p className="text-white font-medium">{dna.affected_shipment_count}</p>
        </div>
      </div>

      {dna.dna_summary && (
        <p className="mt-3 text-[10px] font-mono text-gray-500 bg-gray-900/50 rounded px-2 py-1.5 break-all">
          {dna.dna_summary}
        </p>
      )}
    </div>
  )
}
