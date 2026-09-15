import { useBackendStatus } from '../hooks/useBackendStatus'

type StateConfig = { dot: string; label: string; text: string }

const stateConfig: Record<string, StateConfig> = {
  checking: {
    dot: 'bg-yellow-400 animate-pulse',
    label: 'Checking…',
    text: 'text-yellow-400',
  },
  connected: {
    dot: 'bg-green-400',
    label: 'Backend connected',
    text: 'text-green-400',
  },
  unreachable: {
    dot: 'bg-red-400',
    label: 'Backend unreachable',
    text: 'text-red-400',
  },
}

export function BackendStatusBadge() {
  const { state, health, lastChecked, refresh } = useBackendStatus()
  const cfg = stateConfig[state]

  return (
    <button
      onClick={refresh}
      title={
        lastChecked
          ? `Last checked: ${lastChecked.toLocaleTimeString()}`
          : 'Click to check'
      }
      className="flex items-center gap-2 rounded-md px-3 py-1.5 text-xs
                 bg-gray-800 hover:bg-gray-700 transition-colors cursor-pointer
                 border border-gray-700"
    >
      <span className={`inline-block w-2 h-2 rounded-full ${cfg.dot}`} />
      <span className={cfg.text}>{cfg.label}</span>
      {health && (
        <span className="text-gray-500">v{health.version}</span>
      )}
    </button>
  )
}
