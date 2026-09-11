import { useRef, useState } from 'react'
import { createJobFromFile, createJobFromUrls, parseCsv, parseExcel, parseExcelSheet } from '../services/api'
import type { ParsedFileInfo, UrlProvider } from '../types'
import { parse_pasted_urls_client } from '../utils/urlUtils'

interface NewJobProps {
  mode: 'paste' | 'csv' | 'excel'
  onJobCreated: (jobId: string) => void
  onBack: () => void
}

export default function NewJob({ mode, onJobCreated, onBack }: NewJobProps) {
  return (
    <div className="page">
      <div className="flex-center gap-12" style={{ marginBottom: 32 }}>
        <button className="btn btn-secondary btn-sm" onClick={onBack}>← Back</button>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
          {mode === 'paste' ? '📋 Paste Links' : mode === 'csv' ? '📄 Upload CSV' : '📊 Upload Excel'}
        </h2>
      </div>

      {mode === 'paste' && <PasteLinksForm onJobCreated={onJobCreated} />}
      {mode === 'csv' && <FileUploadForm accept=".csv" type="csv" onJobCreated={onJobCreated} />}
      {mode === 'excel' && <FileUploadForm accept=".xlsx,.xls" type="excel" onJobCreated={onJobCreated} />}
    </div>
  )
}

// ── Paste Links ──────────────────────────────────────────────────────────────

function PasteLinksForm({ onJobCreated }: { onJobCreated: (id: string) => void }) {
  const [text, setText] = useState('')
  const [provider, setProvider] = useState<UrlProvider>('recordings')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const urls = parse_pasted_urls_client(text)
  const uniqueUrls = [...new Set(urls.filter(Boolean))]
  const dupes = urls.length - uniqueUrls.length

  const handleStart = async () => {
    setError(null)
    setLoading(true)
    try {
      const resp = await createJobFromUrls(uniqueUrls, provider)
      onJobCreated(resp.job_id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create job')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 720, margin: '0 auto' }}>
      <div className="card">
        <div className="form-group">
          <label className="form-label">Recording URLs</label>
          <textarea
            placeholder="Paste S3 recording URLs here...&#10;&#10;https://bucket.s3.ap-south-1.amazonaws.com/path/recording1.wav&#10;https://bucket.s3.ap-south-1.amazonaws.com/path/recording2.wav&#10;&#10;One URL per line — comma-separated also supported"
            value={text}
            onChange={(e) => setText(e.target.value)}
            style={{ minHeight: 240 }}
          />
        </div>

        {text.trim() && (
          <div className="validation-grid" style={{ marginTop: 16 }}>
            {[
              { cls: 'vi-total',   val: urls.length,        label: 'Total' },
              { cls: 'vi-valid',   val: uniqueUrls.length,  label: 'Unique valid' },
              { cls: 'vi-dup',     val: dupes,              label: 'Duplicates' },
            ].map((v) => (
              <div key={v.label} className={`validation-item ${v.cls}`}>
                <div className="vi-val">{v.val.toLocaleString()}</div>
                <div className="vi-label">{v.label}</div>
              </div>
            ))}
          </div>
        )}

        <div className="divider" />

        <ProviderSelect value={provider} onChange={setProvider} />

        {error && <div className="error-banner" style={{ marginTop: 12 }}>⚠ {error}</div>}

        <button
          className="btn btn-primary btn-lg"
          style={{ marginTop: 16, width: '100%', justifyContent: 'center' }}
          onClick={handleStart}
          disabled={loading || uniqueUrls.length === 0}
        >
          {loading ? <span className="spin">⟳</span> : '🚀'}
          {loading ? 'Creating job…' : `Start Conversion (${uniqueUrls.length.toLocaleString()} URLs)`}
        </button>
      </div>
    </div>
  )
}

// ── File Upload Form ─────────────────────────────────────────────────────────

function FileUploadForm({
  accept, type, onJobCreated,
}: {
  accept: string
  type: 'csv' | 'excel'
  onJobCreated: (id: string) => void
}) {
  const [step, setStep] = useState<'upload' | 'configure' | 'preview'>('upload')
  const [dragging, setDragging] = useState(false)
  const [fileInfo, setFileInfo] = useState<ParsedFileInfo | null>(null)
  const [selectedSheet, setSelectedSheet] = useState<string>('')
  const [selectedCol, setSelectedCol] = useState<string>('')
  const [provider, setProvider] = useState<UrlProvider>('recordings')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = async (file: File) => {
    setError(null)
    setLoading(true)
    try {
      const info = type === 'csv' ? await parseCsv(file) : await parseExcel(file)
      setFileInfo(info)
      if (info.url_columns.length > 0) setSelectedCol(info.url_columns[0])
      if (info.sheets && info.sheets.length > 0) setSelectedSheet(info.sheets[0])
      setStep('configure')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to parse file')
    } finally {
      setLoading(false)
    }
  }

  const handleSheetChange = async (sheet: string) => {
    if (!fileInfo) return
    setSelectedSheet(sheet)
    setLoading(true)
    try {
      const info = await parseExcelSheet(fileInfo.file_id, sheet)
      setFileInfo(info)
      if (info.url_columns.length > 0) setSelectedCol(info.url_columns[0])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load sheet')
    } finally {
      setLoading(false)
    }
  }

  const handleStart = async () => {
    if (!fileInfo || !selectedCol) return
    setError(null)
    setLoading(true)
    try {
      const resp = await createJobFromFile({
        file_id: fileInfo.file_id,
        url_column: selectedCol,
        provider,
        sheet_name: selectedSheet || undefined,
      })
      onJobCreated(resp.job_id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create job')
    } finally {
      setLoading(false)
    }
  }

  if (step === 'upload') {
    return (
      <div style={{ maxWidth: 600, margin: '0 auto' }}>
        <div
          className={`dropzone ${dragging ? 'drag-over' : ''}`}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault(); setDragging(false)
            const file = e.dataTransfer.files[0]
            if (file) handleFile(file)
          }}
        >
          <div className="dropzone-icon">{type === 'csv' ? '📄' : '📊'}</div>
          <div className="dropzone-title">
            {loading ? 'Parsing file…' : `Drop your ${type.toUpperCase()} file here`}
          </div>
          <div className="dropzone-sub">
            {loading ? <span className="spin">⟳</span> : `or click to browse · ${accept}`}
          </div>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          style={{ display: 'none' }}
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f) }}
        />
        {error && <div className="error-banner" style={{ marginTop: 12 }}>⚠ {error}</div>}
      </div>
    )
  }

  if (!fileInfo) return null

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <div className="card">
        {/* File info */}
        <div className="flex-center gap-12" style={{ marginBottom: 20 }}>
          <div style={{ fontSize: '1.6rem' }}>{type === 'csv' ? '📄' : '📊'}</div>
          <div>
            <div style={{ fontWeight: 600 }}>{fileInfo.filename}</div>
            <div className="text-muted">{fileInfo.total_rows.toLocaleString()} rows detected</div>
          </div>
          <button className="btn btn-secondary btn-sm" style={{ marginLeft: 'auto' }} onClick={() => setStep('upload')}>
            Change file
          </button>
        </div>

        <div className="divider" />

        {/* Sheet selector (Excel) */}
        {fileInfo.sheets && fileInfo.sheets.length > 1 && (
          <div className="form-group" style={{ marginBottom: 16 }}>
            <label className="form-label">Sheet</label>
            <select value={selectedSheet} onChange={(e) => handleSheetChange(e.target.value)}>
              {fileInfo.sheets.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        )}

        {/* URL column selector */}
        <div className="form-group" style={{ marginBottom: 16 }}>
          <label className="form-label">
            Recording URL Column
            {fileInfo.url_columns.length > 0 && (
              <span style={{ color: 'var(--success)', marginLeft: 8 }}>✓ Auto-detected</span>
            )}
          </label>
          <select value={selectedCol} onChange={(e) => setSelectedCol(e.target.value)}>
            <option value="">— select column —</option>
            {fileInfo.columns.map((c) => (
              <option key={c} value={c}>{c}{fileInfo.url_columns.includes(c) ? ' ★' : ''}</option>
            ))}
          </select>
        </div>

        <ProviderSelect value={provider} onChange={setProvider} />

        {/* Preview */}
        {fileInfo.preview.length > 0 && (
          <>
            <div className="divider" />
            <div className="form-label" style={{ marginBottom: 8 }}>Preview (first {fileInfo.preview.length} rows)</div>
            <div className="preview-wrap">
              <table>
                <thead>
                  <tr>
                    {fileInfo.columns.map((c) => (
                      <th key={c} style={{ color: fileInfo.url_columns.includes(c) ? 'var(--accent-light)' : undefined }}>
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {fileInfo.preview.map((row, i) => (
                    <tr key={i}>
                      {fileInfo.columns.map((c) => (
                        <td key={c}>{String(row[c] ?? '')}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {error && <div className="error-banner" style={{ marginTop: 16 }}>⚠ {error}</div>}

        <button
          className="btn btn-primary btn-lg"
          style={{ marginTop: 20, width: '100%', justifyContent: 'center' }}
          onClick={handleStart}
          disabled={loading || !selectedCol}
        >
          {loading ? <><span className="spin">⟳</span> Creating job…</> : `🚀 Start Conversion (${fileInfo.total_rows.toLocaleString()} rows)`}
        </button>
      </div>
    </div>
  )
}

// ── Provider selector ────────────────────────────────────────────────────────

function ProviderSelect({ value, onChange }: { value: UrlProvider; onChange: (v: UrlProvider) => void }) {
  return (
    <div className="form-group">
      <label className="form-label">URL Provider</label>
      <div style={{ display: 'flex', gap: 8 }}>
        {[
          { id: 'recordings' as UrlProvider, label: '🔒 Presigned S3', sub: '7-day expiry' },
          { id: 'cloudfront' as UrlProvider, label: '☁ CloudFront', sub: '30-day signed' },
        ].map((p) => (
          <button
            key={p.id}
            className={`mode-tab ${value === p.id ? 'active' : ''}`}
            style={{ flex: 1, padding: '12px 16px', minWidth: 0, flexDirection: 'row', gap: 8 }}
            onClick={() => onChange(p.id)}
          >
            <span>{p.label}</span>
            <span style={{ fontSize: '0.72rem', color: value === p.id ? 'var(--accent-light)' : 'var(--text-muted)' }}>
              {p.sub}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
