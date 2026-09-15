import { BackendStatusBadge } from './BackendStatusBadge'

interface TopbarProps {
  title: string
}

export function Topbar({ title }: TopbarProps) {
  return (
    <header className="flex items-center justify-between px-6 py-3 bg-gray-950 border-b border-gray-800 shrink-0">
      <h1 className="text-sm font-semibold text-gray-200">{title}</h1>
      <div className="flex items-center gap-3">
        <BackendStatusBadge />
      </div>
    </header>
  )
}
