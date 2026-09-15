/**
 * RRIGauge — animated arc gauge showing 0–100 RRI score.
 * Uses SVG only. No external dependencies.
 */

interface RRIGaugeProps {
  rri: number
  status: string
  size?: number
}

const STATUS_COLORS: Record<string, string> = {
  HEALTHY:    '#22c55e',
  STRESSED:   '#eab308',
  VULNERABLE: '#f97316',
  CRITICAL:   '#ef4444',
  BANKRUPT:   '#7f1d1d',
}

export function RRIGauge({ rri, status, size = 140 }: RRIGaugeProps) {
  const color = STATUS_COLORS[status] ?? '#6b7280'
  const cx = size / 2
  const cy = size / 2
  const r = size * 0.38
  // Arc: 210° sweep from 195° to 345° (bottom-left to bottom-right, passing through top)
  const startAngle = 195
  const totalArc = 330 - 2 * 15  // 300°
  const pct = Math.max(0, Math.min(rri, 100)) / 100
  const fillArc = pct * totalArc

  function polar(cx: number, cy: number, r: number, angleDeg: number) {
    const rad = ((angleDeg - 90) * Math.PI) / 180
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
  }

  function arc(startDeg: number, sweepDeg: number, radius: number) {
    if (sweepDeg <= 0) return ''
    const s = polar(cx, cy, radius, startDeg)
    const e = polar(cx, cy, radius, startDeg + sweepDeg)
    const large = sweepDeg > 180 ? 1 : 0
    return `M ${s.x} ${s.y} A ${radius} ${radius} 0 ${large} 1 ${e.x} ${e.y}`
  }

  const trackPath = arc(startAngle, totalArc, r)
  const fillPath  = arc(startAngle, fillArc,  r)

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-label={`RRI ${rri}`}>
      {/* Track */}
      <path d={trackPath} fill="none" stroke="#374151" strokeWidth={size * 0.08}
            strokeLinecap="round" />
      {/* Fill */}
      {fillPath && (
        <path d={fillPath} fill="none" stroke={color} strokeWidth={size * 0.08}
              strokeLinecap="round" />
      )}
      {/* Score */}
      <text x={cx} y={cy + 4} textAnchor="middle" dominantBaseline="middle"
            fontSize={size * 0.22} fontWeight="700" fill={color}>
        {Math.round(rri)}
      </text>
      {/* Label */}
      <text x={cx} y={cy + size * 0.26} textAnchor="middle"
            fontSize={size * 0.09} fill="#9ca3af" fontWeight="500">
        {status}
      </text>
    </svg>
  )
}
