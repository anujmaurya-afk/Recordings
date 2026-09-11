import { useCallback, useEffect, useRef, useState } from 'react'
import { getJob } from '../services/api'
import type { JobProgress, JobStatus } from '../types'

const TERMINAL_STATUSES: JobStatus[] = ['completed', 'completed_with_errors', 'failed']
const POLL_INTERVAL_MS = 2000

export function useJobPolling(jobId: string | null) {
  const [job, setJob] = useState<JobProgress | null>(null)
  const [error, setError] = useState<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchJob = useCallback(async () => {
    if (!jobId) return
    try {
      const data = await getJob(jobId)
      setJob(data)
      setError(null)
      if (TERMINAL_STATUSES.includes(data.status)) {
        if (timerRef.current) clearInterval(timerRef.current)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch job status')
    }
  }, [jobId])

  useEffect(() => {
    if (!jobId) return
    fetchJob()
    timerRef.current = setInterval(fetchJob, POLL_INTERVAL_MS)
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [jobId, fetchJob])

  const refresh = useCallback(() => fetchJob(), [fetchJob])

  return { job, error, refresh }
}
