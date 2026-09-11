import { useEffect, useState } from 'react'
import { listRecentJobs } from '../services/api'
import type { JobProgress } from '../types'

type Mode = 'paste' | 'csv' | 'excel'

interface HomeProps {
  onSelectMode: (mode: Mode) => void
  onSelectJob?: (jobId: string) => void
}

const MODES = [
  {
    id: 'paste' as Mode,
    icon: '📋',
    title: 'Paste Links',
    sub: 'One or many S3 URLs, newline or comma separated',
  },
  {
    id: 'csv' as Mode,
    icon: '📄',
    title: 'Upload CSV',
    sub: 'Bulk convert from a .csv file',
  },
  {
    id: 'excel' as Mode,
    icon: '📊',
    title: 'Upload Excel',
    sub: 'Supports .xlsx and .xls files',
  },
]

const CSV_TEMPLATE = `recording_url,agent_name,call_id,duration_sec
https://bucket.s3.ap-south-1.amazonaws.com/calls/call-001.wav,Alice,C001,120
https://bucket.s3.ap-south-1.amazonaws.com/calls/call-002.wav,Bob,C002,95
https://bucket.s3.ap-south-1.amazonaws.com/calls/call-003.wav,Alice,C003,200`

const EXCEL_TEMPLATE = `Sheet: Sheet1 (or any sheet name)

| recording_url                                        | agent_name | call_id | duration_sec |
|------------------------------------------------------|------------|---------|--------------|
| https://bucket.s3.ap-south-1.amazonaws.com/call1.wav | Alice      | C001    | 120          |
| https://bucket.s3.ap-south-1.amazonaws.com/call2.wav | Bob        | C002    | 95           |`

function FormatGuide() {
  const [open, setOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<'csv' | 'excel'>('csv')
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    const text = activeTab === 'csv' ? CSV_TEMPLATE : EXCEL_TEMPLATE
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div className="format-guide">
      <button
        id="format-guide-toggle"
        className="format-guide-toggle"
        onClick={() => setOpen((o) => !o)}
      >
        <span style={{ fontSize: '1rem' }}>📋</span>
        <span>File Format Guide — CSV & Excel column reference</span>
        <span className={`format-guide-toggle-icon${open ? ' open' : ''}`}>▼</span>
      </button>

      {open && (
        <div className="format-guide-body">
          {/* Tab switcher */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            {(['csv', 'excel'] as const).map((t) => (
              <button
                key={t}
                className={`filter-tab${activeTab === t ? ' active' : ''}`}
                onClick={() => setActiveTab(t)}
              >
                {t === 'csv' ? '📄 CSV' : '📊 Excel / XLSX'}
              </button>
            ))}
          </div>

          {/* How the backend reads the file */}
          <h3>How the backend reads your file</h3>
          <div className="table-wrapper" style={{ marginBottom: 16 }}>
            <table>
              <thead>
                <tr>
                  <th>Column</th>
                  <th>Required?</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>
                    <strong style={{ color: 'var(--text-primary)' }}>URL column</strong>
                    <br />
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      Any name containing:&nbsp;
                      {['url','link','recording','audio','media','src','source','href'].map((k) => (
                        <span key={k} className="format-keyword">{k}</span>
                      ))}
                    </span>
                  </td>
                  <td><span className="format-required">✓ Required</span></td>
                  <td style={{ color: 'var(--text-secondary)', whiteSpace: 'normal' }}>
                    Must contain full S3 URLs (e.g.{' '}
                    <code style={{ fontSize: '0.75rem', color: 'var(--accent-2)' }}>
                      https://bucket.s3.region.amazonaws.com/…
                    </code>
                    ). Auto-detected by column name — or you can select it manually.
                  </td>
                </tr>
                {activeTab === 'excel' && (
                  <tr>
                    <td>
                      <strong style={{ color: 'var(--text-primary)' }}>Sheet</strong>
                    </td>
                    <td><span className="format-optional">Optional</span></td>
                    <td style={{ color: 'var(--text-secondary)', whiteSpace: 'normal' }}>
                      If the file has multiple sheets you'll be prompted to pick one. First sheet is used by default.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Rules */}
          <h3 style={{ marginBottom: 8 }}>Rules</h3>
          <ul style={{
            listStyle: 'none',
            display: 'flex',
            flexDirection: 'column',
            gap: 6,
            marginBottom: 16,
            fontSize: '0.83rem',
            color: 'var(--text-secondary)',
          }}>
            {[
              'Row 1 must be the header row with column names.',
              'The file must be saved as UTF-8 (CSV) or standard Excel format (.xlsx / .xls).',
              'Empty rows are skipped automatically.',
              'Duplicate URLs within the same job are deduplicated — only the first occurrence is processed.',
              'There is no hard row limit — the backend streams large files efficiently.',
            ].map((rule) => (
              <li key={rule} style={{ display: 'flex', gap: 8 }}>
                <span style={{ color: 'var(--accent-2)', flexShrink: 0 }}>›</span>
                {rule}
              </li>
            ))}
          </ul>

          {/* Template */}
          <h3 style={{ marginBottom: 8 }}>
            Example {activeTab === 'csv' ? 'CSV' : 'Excel'} template
          </h3>
          <div className="format-code-block">
            <button
              className={`copy-btn${copied ? ' copied' : ''}`}
              onClick={handleCopy}
            >
              {copied ? '✓ Copied' : 'Copy'}
            </button>
            <pre style={{ margin: 0, whiteSpace: 'pre', overflow: 'auto' }}>
              {activeTab === 'csv' ? CSV_TEMPLATE : EXCEL_TEMPLATE}
            </pre>
          </div>

          <p style={{
            marginTop: 12,
            fontSize: '0.78rem',
            color: 'var(--text-muted)',
            lineHeight: 1.7,
          }}>
            💡 <strong style={{ color: 'var(--text-secondary)' }}>Tip:</strong> The backend
            auto-detects the URL column — but if your column name doesn't match any of the
            keywords above, just select it manually in the next step after uploading.
          </p>
        </div>
      )}
    </div>
  )
}

export default function Home({ onSelectMode, onSelectJob }: HomeProps) {
  const [recentJobs, setRecentJobs] = useState<JobProgress[]>([])

  useEffect(() => {
    listRecentJobs(6).then(setRecentJobs).catch(() => {})
  }, [])

  return (
    <div className="hero">
      <div className="hero-badge">Production-ready · Bulk processing · 7-day presigned URLs</div>
      <h1>Recording Converter</h1>
      <p className="hero-sub">
        Convert S3 recording URLs to presigned or CloudFront URLs in bulk.
        Handles thousands of recordings with live progress tracking.
      </p>

      <div className="mode-tabs">
        {MODES.map((m) => (
          <button key={m.id} className="mode-tab" onClick={() => onSelectMode(m.id)}>
            <span className="mode-tab-icon">{m.icon}</span>
            <span style={{ fontWeight: 600 }}>{m.title}</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textAlign: 'center' }}>
              {m.sub}
            </span>
          </button>
        ))}
      </div>

      <FormatGuide />

      {recentJobs.length > 0 && onSelectJob && (
        <div style={{ marginTop: 32, width: '100%', maxWidth: '780px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <span style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
              🕒 Recent Conversion Jobs
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Click any job to view details & error logs
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {recentJobs.map((j) => (
              <div
                key={j.job_id}
                onClick={() => onSelectJob(j.job_id)}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '12px 16px',
                  borderRadius: 12,
                  background: 'var(--surface)',
                  border: '1px solid var(--border-subtle)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
                className="recent-job-item"
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '0.86rem' }}>
                      {j.job_id}
                    </span>
                    <span className={`badge badge-${j.status}`} style={{ fontSize: '0.7rem' }}>
                      {j.status}
                    </span>
                    {j.failed_records > 0 && (
                      <span className="badge badge-failed" style={{ fontSize: '0.7rem' }}>
                        ⚠ {j.failed_records.toLocaleString()} failed
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                    {j.input_filename ? `${j.input_filename} · ` : ''}
                    {j.total_records.toLocaleString()} records · {new Date(j.created_at).toLocaleString()}
                  </div>
                </div>

                <span style={{ color: 'var(--accent-2)', fontSize: '1.2rem', fontWeight: 300 }}>›</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
