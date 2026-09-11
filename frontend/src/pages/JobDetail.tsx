import { useCallback, useEffect, useState } from 'react'
import { cancelJob, getDownloadUrl, getErrorsDownloadUrl, getJobErrors, getJobResults, retryFailed } from '../services/api'
import type { RecordResult, RecordsPage, RecordStatus } from '../types'
import { useJobPolling } from '../hooks/useJobPolling'

interface JobDetailProps {
  jobId: string
  onBack: () => void
}

const PAGE_SIZE = 100

const STATUS_FILTERS: { label: string; value: string }[] = [
  { label: 'All', value: '' },
  { label: 'Success', value: 'success' },
  { label: 'Failed', value: 'failed' },
  { label: 'Processing', value: 'processing' },
  { label: 'Pending', value: 'pending' },
  { label: 'Skipped', value: 'skipped' },
]

export default function JobDetail({ jobId, onBack }: JobDetailProps) {
  const { job, error: jobError, refresh } = useJobPolling(jobId)
  const [statusFilter, setStatusFilter] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [results, setResults] = useState<RecordsPage | null>(null)
  const [resultsLoading, setResultsLoading] = useState(false)
  const [retrying, setRetrying] = useState(false)
  const [retryError, setRetryError] = useState<string | null>(null)
  const [cancelling, setCancelling] = useState(false)
  const [errorSummary, setErrorSummary] = useState<{
    total_failed: number
    error_breakdown: Record<string, number>
    sample_errors: Array<{
      row_number: number
      original_url: string
      error: string
      extra_data: Record<string, any>
    }>
  } | null>(null)

  useEffect(() => {
    if (job && job.failed_records > 0) {
      getJobErrors(jobId)
        .then(setErrorSummary)
        .catch(() => {})
    }
  }, [jobId, job?.failed_records])

  const fetchResults = useCallback(async () => {
    setResultsLoading(true)
    try {
      const data = await getJobResults(jobId, {
        page,
        page_size: PAGE_SIZE,
        status: statusFilter || undefined,
        search: search || undefined,
      })
      setResults(data)
    } catch {}
    finally { setResultsLoading(false) }
  }, [jobId, page, statusFilter, search])

  useEffect(() => { fetchResults() }, [fetchResults])
  // Refresh results when job progress updates
  useEffect(() => { if (job) fetchResults() }, [job?.processed_records])

  const handleRetry = async () => {
    setRetrying(true)
    setRetryError(null)
    try {
      await retryFailed(jobId)
      refresh()
    } catch (e) {
      setRetryError(e instanceof Error ? e.message : 'Retry failed')
    } finally {
      setRetrying(false)
    }
  }

  const handleCancel = async () => {
    if (!window.confirm('Are you sure you want to stop this conversion job?')) return
    setCancelling(true)
    try {
      await cancelJob(jobId)
      refresh()
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed to cancel job')
    } finally {
      setCancelling(false)
    }
  }

  const isTerminal = job && ['completed', 'completed_with_errors', 'failed', 'cancelled'].includes(job.status)

  if (!job && !jobError) {
    return (
      <div className="page">
        <div className="empty-state">
          <div className="empty-state-icon spin">⟳</div>
          <h3>Loading job…</h3>
        </div>
      </div>
    )
  }

  if (jobError) {
    return (
      <div className="page">
        <div className="error-banner">⚠ {jobError}</div>
      </div>
    )
  }

  const pct = job!.total_records > 0
    ? Math.round((job!.processed_records / job!.total_records) * 100)
    : 0

  const totalPages = results ? Math.ceil(results.total / PAGE_SIZE) : 1

  return (
    <div className="page">
      {/* Header */}
      <div className="flex-center gap-12" style={{ marginBottom: 24 }}>
        <button className="btn btn-secondary btn-sm" onClick={onBack}>← Back</button>
        <div>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 700, letterSpacing: '-0.02em', fontFamily: 'monospace' }}>
            {jobId}
          </h2>
          <div className="text-muted" style={{ fontSize: '0.78rem' }}>
            {job!.input_filename ? `${job!.input_filename} · ` : ''}
            Provider: {job!.provider} · Created {new Date(job!.created_at).toLocaleString()}
          </div>
        </div>
        <span className="nav-spacer" />
        <StatusBadge status={job!.status as any} large />
      </div>

      {/* Progress card */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="progress-container" style={{ margin: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: '0.85rem' }}>
            <span style={{ fontWeight: 600 }}>
              {job!.processed_records.toLocaleString()} / {job!.total_records.toLocaleString()}
            </span>
            <span style={{ color: 'var(--text-muted)' }}>{pct}%</span>
          </div>
          <div className="progress-track">
            <div
              className="progress-fill"
              style={{ width: `${pct}%`, animationPlayState: isTerminal ? 'paused' : 'running' }}
            />
          </div>

          <div className="progress-stats" style={{ marginTop: 16 }}>
            {[
              { cls: 'success',    label: 'Successful', val: job!.successful_records },
              { cls: 'failed',     label: 'Failed',     val: job!.failed_records },
              { cls: 'processing', label: 'Processing', val: job!.status === 'processing' ? 1 : 0 },
              { cls: 'pending',    label: 'Pending',    val: Math.max(0, job!.total_records - job!.processed_records) },
            ].map((s) => (
              <div
                key={s.label}
                className={`stat-chip ${s.cls}`}
                style={s.cls === 'failed' && s.val > 0 ? { cursor: 'pointer' } : undefined}
                onClick={() => {
                  if (s.cls === 'failed' && s.val > 0) {
                    setStatusFilter('failed')
                    setPage(1)
                  }
                }}
                title={s.cls === 'failed' && s.val > 0 ? 'Click to filter table to failed records' : undefined}
              >
                <div>
                  <div className="stat-val">{s.val.toLocaleString()}</div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    {s.label} {s.cls === 'failed' && s.val > 0 ? '🔍' : ''}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Action bar */}
      <div className="flex-center gap-8" style={{ marginBottom: 20, flexWrap: 'wrap' }}>
        {!isTerminal && (
          <button
            className="btn btn-danger"
            onClick={handleCancel}
            disabled={cancelling}
            title="Stop this conversion job"
          >
            {cancelling ? <span className="spin">⟳</span> : '⏹'} Stop Job
          </button>
        )}
        {isTerminal && job!.failed_records > 0 && (
          <button
            className="btn btn-danger"
            onClick={handleRetry}
            disabled={retrying}
          >
            {retrying ? <span className="spin">⟳</span> : '🔄'}
            Retry Failed ({job!.failed_records.toLocaleString()})
          </button>
        )}
        {job!.failed_records > 0 && (
          <a
            href={getErrorsDownloadUrl(jobId)}
            className="btn btn-danger"
            download
            title="Download CSV containing all failed rows and exact error reasons"
          >
            ⚠ Download Error Log ({job!.failed_records.toLocaleString()})
          </a>
        )}
        <a
          href={getDownloadUrl(jobId, 'csv')}
          className="btn btn-success"
          download
        >
          ⬇ Download CSV
        </a>
        <a
          href={getDownloadUrl(jobId, 'excel')}
          className="btn btn-success"
          download
        >
          ⬇ Download Excel
        </a>
      </div>
      {retryError && <div className="error-banner" style={{ marginBottom: 16 }}>⚠ {retryError}</div>}

      {/* Error breakdown card if there are failures */}
      {job!.failed_records > 0 && errorSummary && (
        <div className="card" style={{ marginBottom: 20, borderLeft: '4px solid var(--error)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: '1.2rem' }}>⚠️</span>
              <span style={{ fontWeight: 700, fontSize: '0.95rem', color: '#f87171' }}>
                Error Logs & Failed Records ({errorSummary.total_failed.toLocaleString()})
              </span>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => { setStatusFilter('failed'); setPage(1) }}
              >
                Filter Table to Failed
              </button>
              <a
                href={getErrorsDownloadUrl(jobId)}
                className="btn btn-danger btn-sm"
                download
              >
                ⬇ Download Error CSV
              </a>
            </div>
          </div>

          <div style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
            Root causes identified in this batch:
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 12 }}>
            {Object.entries(errorSummary.error_breakdown).map(([reason, count]) => (
              <div
                key={reason}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '8px 12px',
                  borderRadius: 8,
                  background: 'rgba(239, 68, 68, 0.08)',
                  border: '1px solid rgba(239, 68, 68, 0.2)',
                  fontSize: '0.84rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ color: 'var(--error)' }}>✕</span>
                  <span style={{ fontWeight: 600 }}>{reason}</span>
                </div>
                <span
                  className="badge badge-failed"
                  style={{ cursor: 'pointer' }}
                  onClick={() => { setStatusFilter('failed'); setPage(1) }}
                  title="Click to view these records in table"
                >
                  {count.toLocaleString()} rows ›
                </span>
              </div>
            ))}
          </div>

          {errorSummary.sample_errors.length > 0 && (
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Sample spreadsheet rows affected: {errorSummary.sample_errors.slice(0, 10).map(s => `Row #${s.row_number}`).join(', ')}
              {errorSummary.total_failed > 10 ? ` and ${errorSummary.total_failed - 10} more…` : ''}
            </div>
          )}
        </div>
      )}

      {/* Results */}
      <div className="card">
        {/* Filters */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
          <div className="filter-tabs">
            {STATUS_FILTERS.map((f) => (
              <button
                key={f.value}
                className={`filter-tab ${statusFilter === f.value ? 'active' : ''}`}
                onClick={() => { setStatusFilter(f.value); setPage(1) }}
              >
                {f.label}
              </button>
            ))}
          </div>
          <div className="search-bar" style={{ flex: 1, minWidth: 200 }}>
            <span className="search-icon">🔍</span>
            <input
              type="text"
              placeholder="Search URLs…"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            />
          </div>
        </div>

        {/* Table */}
        {resultsLoading ? (
          <div className="empty-state" style={{ padding: '40px' }}>
            <span className="spin" style={{ fontSize: '2rem' }}>⟳</span>
          </div>
        ) : !results || results.items.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📭</div>
            <h3>No records found</h3>
            <p>Try adjusting your filters.</p>
          </div>
        ) : (
          <>
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th style={{ width: 50 }}>#</th>
                    <th>Original URL</th>
                    <th style={{ width: 110 }}>Status</th>
                    <th>Converted URL</th>
                    <th>Error</th>
                  </tr>
                </thead>
                <tbody>
                  {results.items.map((rec) => (
                    <RecordRow key={rec.id} rec={rec} />
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="pagination" style={{ marginTop: 16 }}>
              <span className="pagination-info">
                {((page - 1) * PAGE_SIZE + 1).toLocaleString()}–{Math.min(page * PAGE_SIZE, results.total).toLocaleString()} of {results.total.toLocaleString()}
              </span>
              <button className="pagination-btn" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>‹</button>
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const p = Math.max(1, Math.min(page - 2, totalPages - 4)) + i
                return (
                  <button
                    key={p}
                    className={`pagination-btn ${p === page ? 'active' : ''}`}
                    onClick={() => setPage(p)}
                  >
                    {p}
                  </button>
                )
              })}
              <button className="pagination-btn" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>›</button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function RecordRow({ rec }: { rec: RecordResult }) {
  return (
    <tr>
      <td style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>
        {rec.row_index + 1}
      </td>
      <td className="url-cell" title={rec.original_url ?? ''}>
        {rec.original_url || <span style={{ color: 'var(--text-muted)' }}>—</span>}
      </td>
      <td>
        <StatusBadge status={rec.status} />
      </td>
      <td className="url-cell" title={rec.converted_url ?? ''}>
        {rec.converted_url ? (
          <a href={rec.converted_url} target="_blank" rel="noopener noreferrer" className="url-link">
            {rec.converted_url.length > 60 ? rec.converted_url.slice(0, 60) + '…' : rec.converted_url}
          </a>
        ) : <span style={{ color: 'var(--text-muted)' }}>—</span>}
      </td>
      <td style={{ color: 'var(--error)', fontSize: '0.78rem' }}>
        {rec.error || ''}
      </td>
    </tr>
  )
}

function StatusBadge({ status, large }: { status: RecordStatus | string; large?: boolean }) {
  return (
    <span
      className={`badge badge-${status}`}
      style={large ? { fontSize: '0.82rem', padding: '5px 14px' } : undefined}
    >
      {status}
    </span>
  )
}
