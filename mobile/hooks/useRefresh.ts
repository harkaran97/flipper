/**
 * Triggers a manual backend ingestion cycle via POST /refresh.
 * Polls the job status until complete or failed, then signals done.
 */
import { useState, useCallback } from 'react'
import { api } from '../lib/api'

const POLL_INTERVAL_MS = 1500
const MAX_POLLS = 20

export const useRefresh = () => {
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null)

  const triggerRefresh = useCallback(async () => {
    if (isRefreshing) return
    setIsRefreshing(true)
    try {
      const { data } = await api.post<{ job_id: string }>('/refresh')
      const jobId = data.job_id
      let polls = 0
      await new Promise<void>((resolve) => {
        const interval = setInterval(async () => {
          polls++
          try {
            const { data: job } = await api.get<{ status: string }>(`/refresh/${jobId}`)
            if (job.status === 'complete' || job.status === 'failed' || polls >= MAX_POLLS) {
              clearInterval(interval)
              resolve()
            }
          } catch {
            clearInterval(interval)
            resolve()
          }
        }, POLL_INTERVAL_MS)
      })
      setLastRefreshed(new Date())
    } catch {
      // swallow — caller handles via pull-to-refresh UI feedback
    } finally {
      setIsRefreshing(false)
    }
  }, [isRefreshing])

  return { triggerRefresh, isRefreshing, lastRefreshed }
}
