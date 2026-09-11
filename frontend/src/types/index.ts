// API types matching backend schemas exactly

export type JobStatus = 'pending' | 'processing' | 'completed' | 'completed_with_errors' | 'failed' | 'cancelled'
export type RecordStatus = 'pending' | 'processing' | 'success' | 'failed' | 'skipped'
export type UrlProvider = 'recordings' | 'cloudfront'

export interface JobProgress {
  job_id: string
  status: JobStatus
  total_records: number
  processed_records: number
  successful_records: number
  failed_records: number
  skipped_records: number
  provider: UrlProvider
  input_filename: string | null
  url_column: string | null
  created_at: string
  updated_at: string
}

export interface RecordResult {
  id: number
  job_id: string
  row_index: number
  original_url: string | null
  converted_url: string | null
  status: RecordStatus
  error: string | null
  extra_data: Record<string, unknown>
}

export interface RecordsPage {
  job_id: string
  total: number
  page: number
  page_size: number
  items: RecordResult[]
}

export interface ParsedFileInfo {
  file_id: string
  filename: string
  total_rows: number
  columns: string[]
  url_columns: string[]
  sheets: string[] | null
  preview: Record<string, unknown>[]
}

export interface ValidationSummary {
  total: number
  valid: number
  invalid: number
  duplicates: number
}

export interface CreateJobFromUrlsResponse {
  job_id: string
  validation: ValidationSummary
}

export interface CreateJobFromFileResponse {
  job_id: string
  total_records: number
}
