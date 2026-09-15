import { useEffect, useState } from 'react'
import { api, type HealthResponse } from '../api/client'

type ConnectionState = 'checking' | 'connected' | 'unreachable'

interface UseBackendStatusResult {
  state: ConnectionState
  health: HealthResponse | null
  lastChecked: Date | null
  refresh: () => void
}

export function useBackendStatus(
  pollIntervalMs = 30_000,
): UseBackendStatusResult {
  const [state, setState] = useState<ConnectionState>('checking')
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [lastChecked, setLastChecked] = useState<Date | null>(null)

  const check = () => {
    setState('checking')
    api.health
      .get()
      .then((data) => {
        setHealth(data)
        setState('connected')
        setLastChecked(new Date())
      })
      .catch(() => {
        setHealth(null)
        setState('unreachable')
        setLastChecked(new Date())
      })
  }

  useEffect(() => {
    check()
    const id = setInterval(check, pollIntervalMs)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pollIntervalMs])

  return { state, health, lastChecked, refresh: check }
}
