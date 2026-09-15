import { useEffect, useState } from 'react'
import { apiApprovals, ApprovalRequest } from '../api/approvals'

export function Approvals() {
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchApprovals = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiApprovals.list()
      setApprovals(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchApprovals()
  }, [])

  const handleAction = async (id: string, action: 'approve' | 'reject') => {
    try {
      if (action === 'approve') {
        await apiApprovals.approve(id)
      } else {
        await apiApprovals.reject(id)
      }
      await fetchApprovals()
    } catch (err: any) {
      alert(`Failed to ${action}: ${err.message}`)
    }
  }

  if (loading && approvals.length === 0) return <div className="p-6 text-gray-400">Loading approvals...</div>
  if (error) return <div className="p-6 text-red-500">Error: {error}</div>

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold text-gray-100">Pending Approvals</h2>
        <button 
          onClick={fetchApprovals}
          className="px-3 py-1 bg-gray-800 text-gray-300 rounded border border-gray-700 hover:bg-gray-700"
        >
          Refresh
        </button>
      </div>

      {approvals.length === 0 ? (
        <div className="text-gray-500 py-8 text-center bg-gray-900 rounded-lg border border-gray-800">
          No pending approvals found.
        </div>
      ) : (
        <div className="space-y-4">
          {approvals.map(approval => (
            <div key={approval.id} className="bg-gray-800 border border-gray-700 rounded-lg p-5">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-lg font-medium text-gray-200">
                    {approval.action} - {approval.entityType} ({approval.entityId})
                  </h3>
                  <div className="text-sm text-gray-400 mt-1">
                    Requested by <span className="text-gray-300 font-medium">{approval.requestedBy}</span> on {new Date(approval.requestedAt).toLocaleString()}
                  </div>
                  {approval.details && (
                    <div className="mt-3 text-sm bg-gray-900 p-3 rounded border border-gray-700 overflow-auto">
                      <pre className="text-gray-300 whitespace-pre-wrap font-mono text-xs">
                        {JSON.stringify(approval.details, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
                <div className="flex space-x-3 ml-4">
                  {approval.status === 'pending' && (
                    <>
                      <button
                        onClick={() => handleAction(approval.id, 'reject')}
                        className="px-4 py-2 bg-red-900/50 text-red-400 border border-red-800 rounded hover:bg-red-900/70 transition-colors"
                      >
                        Reject
                      </button>
                      <button
                        onClick={() => handleAction(approval.id, 'approve')}
                        className="px-4 py-2 bg-shield-600 text-white rounded hover:bg-shield-500 transition-colors"
                      >
                        Approve
                      </button>
                    </>
                  )}
                  {approval.status !== 'pending' && (
                    <span className={`px-3 py-1 rounded text-xs font-medium ${approval.status === 'approved' ? 'bg-green-900/50 text-green-400 border border-green-800' : 'bg-red-900/50 text-red-400 border border-red-800'}`}>
                      {approval.status.toUpperCase()}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
