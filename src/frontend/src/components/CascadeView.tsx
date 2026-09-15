/**
 * CascadeView — visual tree showing the cascading impact of a disruption.
 * Disruption → Port/Region → Routes → Shipments → Cargo
 */

import type { CascadeNode } from '../api/disruptions'

const LEVEL_STYLES: Record<string, { border: string; text: string; bg: string; indent: string }> = {
  DISRUPTION:  { border: 'border-red-700',    text: 'text-red-200',    bg: 'bg-red-900/30',    indent: 'ml-0' },
  PORT_REGION: { border: 'border-amber-700',  text: 'text-amber-200',  bg: 'bg-amber-900/30',  indent: 'ml-4' },
  ROUTES:      { border: 'border-blue-700',   text: 'text-blue-200',   bg: 'bg-blue-900/30',   indent: 'ml-8' },
  SHIPMENTS:   { border: 'border-violet-700', text: 'text-violet-200', bg: 'bg-violet-900/30', indent: 'ml-12' },
  CARGO:       { border: 'border-teal-700',   text: 'text-teal-200',   bg: 'bg-teal-900/30',   indent: 'ml-16' },
  FLEET:       { border: 'border-green-700',  text: 'text-green-200',  bg: 'bg-green-900/30',  indent: 'ml-20' },
}

function NodeLine({ node, depth = 0 }: { node: CascadeNode; depth?: number }) {
  const style = LEVEL_STYLES[node.level] ?? LEVEL_STYLES.CARGO
  const indent = `ml-${depth * 4}`

  return (
    <div className={`${indent}`}>
      {/* Connector line */}
      {depth > 0 && (
        <div className="flex items-start">
          <div className="w-4 border-l-2 border-dashed border-gray-700 self-stretch mr-2 mt-0" />
          <div className="flex-1">
            <NodeCard node={node} style={style} depth={depth} />
          </div>
        </div>
      )}
      {depth === 0 && <NodeCard node={node} style={style} depth={depth} />}
    </div>
  )
}

function NodeCard({ node, style, depth }: {
  node: CascadeNode
  style: { border: string; text: string; bg: string; indent: string }
  depth: number
}) {
  const visibleChildren = node.level === 'ROUTES' ? node.children.slice(0, 6) : node.children
  const hiddenChildren = node.children.length - visibleChildren.length
  return (
    <div className="mb-1">
      <div className={`rounded border ${style.border} ${style.bg} px-3 py-2 mb-1`}>
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0">
            <span className={`text-[10px] font-mono ${style.text} opacity-70 mr-1`}>
              {node.level}
            </span>
            <span className={`text-[11px] font-semibold ${style.text}`}>{node.label}</span>
          </div>
        </div>
        {node.detail && (
          <p className="text-[10px] text-gray-400 mt-0.5 leading-relaxed">{node.detail}</p>
        )}
      </div>
      {visibleChildren.map((child, i) => (
        <NodeLine key={i} node={child} depth={depth + 1} />
      ))}
      {hiddenChildren > 0 && <p className="ml-6 py-1 text-[10px] text-gray-500">+ {hiddenChildren} additional affected shipments — see the ranked investigation table below.</p>}
    </div>
  )
}

interface Props {
  cascade: CascadeNode
}

export function CascadeView({ cascade }: Props) {
  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-white">Cascading Impact</h3>
        <p className="text-[11px] text-gray-500 mt-0.5">
          Deterministic propagation from recorded database relationships
        </p>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-2 mb-4">
        {Object.entries(LEVEL_STYLES).map(([level, s]) => (
          <span
            key={level}
            className={`text-[10px] px-1.5 py-0.5 rounded border ${s.border} ${s.text} ${s.bg}`}
          >
            {level}
          </span>
        ))}
      </div>

      <div className="overflow-x-auto">
        <NodeLine node={cascade} depth={0} />
      </div>
    </div>
  )
}
