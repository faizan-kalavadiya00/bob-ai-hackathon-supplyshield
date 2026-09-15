import { useEffect, useState } from 'react'
import { apiAudit, AuditLogEntry } from '../api/audit'

export function Audit() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)

  const fetchLogs = async (pageNum: number) => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiAudit.list({ page: pageNum, limit: 20 })
      setLogs(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs(page)
  }, [page])

  if (loading && logs.length === 0) return <div className="p-6 text-gray-400">Loading audit logs...</div>
  if (error) return <div className="p-6 text-red-500">Error: {error}</div>

  return (
    <div className="p-6 flex flex-col h-full space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold text-gray-100">Audit Log</h2>
        <div className="flex space-x-2">
          <button 
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1 || loading}
            className="px-3 py-1 bg-gray-800 text-gray-300 rounded border border-gray-700 disabled:opacity-50 hover:bg-gray-700 transition-colors"
          >
            Previous
          </button>
          <span className="px-3 py-1 text-gray-400">Page {page}</span>
          <button 
            onClick={() => setPage(p => p + 1)}
            disabled={loading || logs.length < 20}
            className="px-3 py-1 bg-gray-800 text-gray-300 rounded border border-gray-700 disabled:opacity-50 hover:bg-gray-700 transition-colors"
          >
            Next
          </button>
        </div>
      </div>

      {logs.length === 0 ? (
        <div className="text-gray-500 py-8 text-center bg-gray-900 rounded-lg border border-gray-800">
          No audit logs found.
        </div>
      ) : (
        <div className="flex-1 overflow-auto rounded-lg border border-gray-800 bg-gray-900">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-gray-400 uppercase bg-gray-800 border-b border-gray-700 sticky top-0">
              <tr>
                <th className="px-6 py-3 font-medium">Timestamp</th>
                <th className="px-6 py-3 font-medium">Actor</th>
                <th className="px-6 py-3 font-medium">Action</th>
                <th className="px-6 py-3 font-medium">Entity</th>
                <th className="px-6 py-3 font-medium">Changes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800 text-gray-300">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-800/50">
                  <td className="px-6 py-4 whitespace-nowrap text-gray-400">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="bg-gray-800 px-2 py-1 rounded border border-gray-700 text-xs">
                      {log.actor}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap font-medium text-shield-400">
                    {log.action}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {log.entityType} <span className="text-gray-500">#{log.entityId}</span>
                  </td>
                  <td className="px-6 py-4">
                    {log.changes ? (
                      <div className="text-xs space-y-2">
                        {log.changes.before && (
                          <div className="bg-red-900/20 border border-red-900/50 p-2 rounded">
                            <span className="text-red-400 font-bold block mb-1">- Before</span>
                            <pre className="font-mono text-gray-400 whitespace-pre-wrap">{JSON.stringify(log.changes.before, null, 2)}</pre>
                          </div>
                        )}
                        {log.changes.after && (
                          <div className="bg-green-900/20 border border-green-900/50 p-2 rounded">
                            <span className="text-green-400 font-bold block mb-1">+ After</span>
                            <pre className="font-mono text-gray-400 whitespace-pre-wrap">{JSON.stringify(log.changes.after, null, 2)}</pre>
                          </div>
                        )}
                      </div>
                    ) : (
                      <span className="text-gray-500 italic">No diff available</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
