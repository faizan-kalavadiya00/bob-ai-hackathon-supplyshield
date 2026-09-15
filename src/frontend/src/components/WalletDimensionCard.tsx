/**
 * WalletDimensionCard — shows one resilience dimension's state.
 */

import type { DimensionState } from '../api/resilience'

const STATUS_STYLES: Record<string, { bar: string; badge: string }> = {
  HEALTHY:    { bar: 'bg-green-500',  badge: 'bg-green-900/50 text-green-400' },
  STRESSED:   { bar: 'bg-yellow-500', badge: 'bg-yellow-900/50 text-yellow-400' },
  VULNERABLE: { bar: 'bg-orange-500', badge: 'bg-orange-900/50 text-orange-400' },
  CRITICAL:   { bar: 'bg-red-500',    badge: 'bg-red-900/50 text-red-400' },
  BANKRUPT:   { bar: 'bg-red-900',    badge: 'bg-red-950 text-red-300 font-bold' },
}

const DIM_ICONS: Record<string, string> = {
  time:        '⏱',
  cost:        '$',
  temperature: '❄',
  capacity:    '🏋',
}

const DIM_LABELS: Record<string, string> = {
  time:        'TIME',
  cost:        'COST',
  temperature: 'TEMPERATURE',
  capacity:    'CAPACITY',
}

function fmt(value: number, unit: string): string {
  if (unit === 'USD') return `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
  if (unit === 'hours') return `${value.toFixed(1)}h`
  if (unit === 'degC_hours') return `${value.toFixed(1)} °C·h`
  if (unit === 'kg') return `${value.toFixed(0)} kg`
  return value.toFixed(2)
}

interface WalletDimensionCardProps {
  dim: DimensionState
  showDetails?: boolean
}

export function WalletDimensionCard({ dim, showDetails = true }: WalletDimensionCardProps) {
  const styles = STATUS_STYLES[dim.status] ?? STATUS_STYLES['HEALTHY']
  const utilPct = Math.min(dim.utilization_percent, 100)
  const remainPct = 100 - utilPct

  return (
    <div className={`rounded-xl bg-gray-900 border p-4 ${
      dim.status === 'BANKRUPT' ? 'border-red-800' : 'border-gray-800'
    }`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg" aria-hidden="true">{DIM_ICONS[dim.dimension] ?? '◈'}</span>
          <span className="text-sm font-semibold text-gray-200">
            {DIM_LABELS[dim.dimension] ?? dim.dimension}
          </span>
        </div>
        <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${styles.badge}`}>
          {dim.status}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-gray-800 rounded-full mb-3 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${styles.bar}`}
          style={{ width: `${remainPct}%` }}
        />
      </div>

      <div className="flex items-end justify-between">
        <div>
          <p className="text-2xl font-bold text-gray-100">{remainPct.toFixed(0)}%</p>
          <p className="text-[10px] text-gray-500 uppercase tracking-wide">remaining</p>
        </div>
        {showDetails && (
          <div className="text-right text-xs text-gray-500 space-y-0.5">
            <p><span className="text-gray-600">Available </span><span className="text-gray-300">{fmt(dim.maximum_balance, dim.unit)}</span></p>
            <p><span className="text-gray-600">Consumed </span><span className="text-amber-300">{fmt(dim.consumed_balance, dim.unit)}</span></p>
            <p><span className="text-gray-600">Remaining </span><span className="text-gray-100">{fmt(dim.remaining_balance, dim.unit)}</span></p>
          </div>
        )}
      </div>
    </div>
  )
}
