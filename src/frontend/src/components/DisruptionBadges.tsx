/**
 * SeverityBadge — colour-coded severity indicator for disruptions.
 */

interface Props {
  severity: number
  className?: string
}

export function SeverityBadge({ severity, className = '' }: Props) {
  const level =
    severity >= 9 ? { label: 'CATASTROPHIC', bg: 'bg-red-900', text: 'text-red-200', ring: 'ring-red-700' } :
    severity >= 7 ? { label: 'CRITICAL',      bg: 'bg-red-800', text: 'text-red-100', ring: 'ring-red-600' } :
    severity >= 5 ? { label: 'MAJOR',         bg: 'bg-amber-800',text: 'text-amber-100',ring:'ring-amber-600'} :
    severity >= 3 ? { label: 'MODERATE',      bg: 'bg-yellow-800',text:'text-yellow-100',ring:'ring-yellow-600'} :
                    { label: 'MINOR',         bg: 'bg-gray-700', text: 'text-gray-200', ring: 'ring-gray-600' }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-semibold ring-1
        ${level.bg} ${level.text} ${level.ring} ${className}`}
    >
      <span className="inline-block w-1.5 h-1.5 rounded-full bg-current opacity-80" />
      {severity}/10 {level.label}
    </span>
  )
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { bg: string; text: string; dot: string }> = {
    active:     { bg: 'bg-red-900/60',    text: 'text-red-300',    dot: 'bg-red-400' },
    monitoring: { bg: 'bg-amber-900/60',  text: 'text-amber-300',  dot: 'bg-amber-400' },
    resolved:   { bg: 'bg-green-900/60',  text: 'text-green-300',  dot: 'bg-green-400' },
    historical: { bg: 'bg-gray-700/60',   text: 'text-gray-400',   dot: 'bg-gray-500' },
  }
  const s = map[status.toLowerCase()] ?? map.historical
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-semibold ${s.bg} ${s.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot} ${status === 'active' ? 'animate-pulse' : ''}`} />
      {status.toUpperCase()}
    </span>
  )
}

export function TypeBadge({ type }: { type: string }) {
  const map: Record<string, string> = {
    port:        'bg-blue-900/50 text-blue-300',
    weather:     'bg-cyan-900/50 text-cyan-300',
    transport:   'bg-violet-900/50 text-violet-300',
    geopolitical:'bg-red-900/50 text-red-300',
    supplier:    'bg-orange-900/50 text-orange-300',
    regulatory:  'bg-teal-900/50 text-teal-300',
    cyber:       'bg-pink-900/50 text-pink-300',
    demand:      'bg-gray-700/50 text-gray-300',
  }
  const cls = map[type.toLowerCase()] ?? 'bg-gray-700/50 text-gray-300'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium ${cls}`}>
      {type.toUpperCase()}
    </span>
  )
}
