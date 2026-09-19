import type {
  CreateJobFromFileResponse,
  CreateJobFromUrlsResponse,
  JobProgress,
  ParsedFileInfo,
  RecordsPage,
  UrlProvider,
} from '../types'

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string>),
  }

  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers,
  })
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      detail = body.detail ?? detail
    } catch {}
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

// ── Jobs ─────────────────────────────────────────────────────────────────────

export async function createJobFromUrls(
  urls: string[],
  provider: UrlProvider = 'recordings'
): Promise<CreateJobFromUrlsResponse> {
  return request('/jobs/urls', {
    method: 'POST',
    body: JSON.stringify({ urls, provider }),
  })
}

export async function createJobFromFile(params: {
  file_id: string
  url_column: string
  provider: UrlProvider
  sheet_name?: string
}): Promise<CreateJobFromFileResponse> {
  return request('/jobs/file', {
    method: 'POST',
    body: JSON.stringify(params),
  })
}

export async function getJob(jobId: string): Promise<JobProgress> {
  return request(`/jobs/${jobId}`)
}

export async function listRecentJobs(limit = 10): Promise<JobProgress[]> {
  return request(`/jobs?limit=${limit}`)
}

export async function getJobResults(
  jobId: string,
  params: { page?: number; page_size?: number; status?: string; search?: string }
): Promise<RecordsPage> {
  const q = new URLSearchParams()
  if (params.page) q.set('page', String(params.page))
  if (params.page_size) q.set('page_size', String(params.page_size))
  if (params.status) q.set('status', params.status)
  if (params.search) q.set('search', params.search)
  return request(`/jobs/${jobId}/results?${q}`)
}

export async function retryFailed(jobId: string, provider?: UrlProvider) {
  return request(`/jobs/${jobId}/retry`, {
    method: 'POST',
    body: JSON.stringify({ provider }),
  })
}

export async function cancelJob(jobId: string) {
  return request(`/jobs/${jobId}/cancel`, {
    method: 'POST',
  })
}

export function getDownloadUrl(jobId: string, format: 'csv' | 'excel') {
  return `${BASE}/jobs/${jobId}/download/${format}`
}

export function getErrorsDownloadUrl(jobId: string) {
  return `${BASE}/jobs/${jobId}/download/errors`
}

export async function getJobErrors(jobId: string) {
  return request<{
    job_id: string
    total_failed: number
    error_breakdown: Record<string, number>
    sample_errors: Array<{
      row_number: number
      original_url: string
      error: string
      extra_data: Record<string, any>
    }>
  }>(`/jobs/${jobId}/errors`)
}

// ── File Parsing ─────────────────────────────────────────────────────────────

export async function parseCsv(file: File): Promise<ParsedFileInfo> {
  const form = new FormData()
  form.append('file', file)

  const res = await fetch(`${BASE}/parse/csv`, { method: 'POST', body: form })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

export async function parseExcel(file: File, sheetName?: string): Promise<ParsedFileInfo> {
  const form = new FormData()
  form.append('file', file)
  if (sheetName) form.append('sheet_name', sheetName)

  const res = await fetch(`${BASE}/parse/excel`, { method: 'POST', body: form })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

export async function parseExcelSheet(fileId: string, sheetName: string): Promise<ParsedFileInfo> {
  return request(`/parse/excel/${fileId}/sheet?sheet_name=${encodeURIComponent(sheetName)}`)
}
