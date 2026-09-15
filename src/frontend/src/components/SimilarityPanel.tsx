/**
 * SimilarityPanel — shows similar historical disruptions with
 * dimension-level match breakdown and historical playbook if available.
 */

import type { SimilarityResult } from '../api/disruptions'
import { TypeBadge, SeverityBadge } from './DisruptionBadges'

interface Props {
  results: SimilarityResult[]
  subjectName: string
}

function scoreBar(score: number) {
  const pct = Math.round(score)
  const color =
    pct >= 75 ? 'bg-green-500' :
    pct >= 50 ? 'bg-yellow-500' :
    pct >= 30 ? 'bg-amber-500' :
               'bg-gray-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono font-semibold text-white w-10 text-right">{pct}%</span>
    </div>
  )
}

function matchQualityColor(quality: string) {
  switch (quality) {
    case 'STRONG':   return 'text-green-400'
    case 'MODERATE': return 'text-yellow-400'
    case 'WEAK':     return 'text-amber-600'
    default:         return 'text-gray-600'
  }
}

export function SimilarityPanel({ results, subjectName }: Props) {
  if (results.length === 0) {
    return (
      <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
        <h3 className="text-sm font-semibold text-white mb-2">Similar Historical Disruptions</h3>
        <p className="text-xs text-gray-500">
          No historical disruptions exceed the similarity threshold.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-white">Similar Historical Disruptions</h3>
        <p className="text-[11px] text-gray-500 mt-0.5">
          Compared against: <span className="text-gray-300">{subjectName}</span>
          {' · '}Deterministic weighted-feature comparison
        </p>
      </div>

      <div className="space-y-4">
        {results.map((r, idx) => (
          <div
            key={r.disruption_id}
            className="rounded-lg border border-gray-700 bg-gray-900/50 p-4"
          >
            {/* Header */}
            <div className="flex items-start justify-between gap-3 mb-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className="text-[10px] text-gray-600 font-mono">#{idx + 1}</span>
                  <span className="text-xs font-semibold text-white truncate">{r.name}</span>
                </div>
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="text-[10px] text-gray-500 font-mono">{r.disruption_code}</span>
                  <TypeBadge type={r.disruption_type} />
                  <SeverityBadge severity={r.severity} />
                </div>
              </div>
              <div className="text-right shrink-0">
                <p className="text-[10px] text-gray-500 mb-1">Similarity</p>
                {scoreBar(r.similarity_score)}
              </div>
            </div>

            {/* Region + duration */}
            <div className="grid grid-cols-2 gap-2 text-[11px] mb-3">
              <div>
                <span className="text-gray-500">Region: </span>
                <span className="text-gray-300">{r.affected_region}</span>
              </div>
              <div>
                <span className="text-gray-500">Duration: </span>
                <span className="text-gray-300">{r.duration_hours.toFixed(0)}h</span>
              </div>
            </div>

            {/* Top matching dimensions */}
            {r.top_matching_dimensions.length > 0 && (
              <div className="mb-3">
                <p className="text-[10px] text-gray-500 mb-1">Top matching dimensions</p>
                <div className="flex flex-wrap gap-1">
                  {r.top_matching_dimensions.map(d => (
                    <span
                      key={d}
                      className="px-1.5 py-0.5 bg-blue-900/40 text-blue-300 text-[10px] rounded font-medium"
                    >
                      {d.toUpperCase()}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Dimension match table */}
            <div className="space-y-1 mb-3">
              {r.dimension_matches
                .filter(m => m.match_quality !== 'NONE')
                .sort((a, b) => b.contribution - a.contribution)
                .map(m => (
                  <div key={m.dimension} className="flex items-center justify-between text-[10px]">
                    <span className="text-gray-500 w-24 capitalize">{m.dimension}</span>
                    <span className={`w-16 text-right ${matchQualityColor(m.match_quality)}`}>
                      {m.match_quality}
                    </span>
                    <span className="text-gray-400 w-12 text-right font-mono">
                      {(m.contribution * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
            </div>

            {/* Historical outcome */}
            <div className="border-t border-gray-700 pt-2 mt-2">
              <p className="text-[10px] text-gray-500 mb-1">Historical outcome / playbook</p>
              {r.historical_outcome ? (
                <p className="text-[11px] text-gray-300 leading-relaxed">{r.historical_outcome}</p>
              ) : (
                <p className="text-[11px] text-gray-600 italic">
                  No historical recovery outcome recorded.
                </p>
              )}
            </div>
          </div>
        ))}
      </div>

      <p className="mt-3 text-[10px] text-gray-600">
        Similarity weights are configurable SupplyShield model assumptions.
        No machine learning is used.
      </p>
    </div>
  )
}
