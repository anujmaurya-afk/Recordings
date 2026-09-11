from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ─── Enums as Literals ──────────────────────────────────────────────────────

JobStatus = Literal["pending", "processing", "completed", "completed_with_errors", "failed", "cancelled"]
RecordStatus = Literal["pending", "processing", "success", "failed", "skipped"]
UrlProvider = Literal["recordings", "cloudfront"]


# ─── Request schemas ─────────────────────────────────────────────────────────

class CreateJobFromUrls(BaseModel):
    urls: List[str] = Field(..., min_length=1)
    provider: UrlProvider = "recordings"


class CreateJobFromFile(BaseModel):
    file_id: str
    url_column: str
    provider: UrlProvider = "recordings"
    sheet_name: Optional[str] = None  # Excel only


class RetryFailedRequest(BaseModel):
    provider: Optional[UrlProvider] = None  # defaults to original job provider


# ─── Response schemas ─────────────────────────────────────────────────────────

class JobProgress(BaseModel):
    job_id: str
    status: JobStatus
    total_records: int
    processed_records: int
    successful_records: int
    failed_records: int
    skipped_records: int
    provider: UrlProvider
    input_filename: Optional[str]
    url_column: Optional[str]
    created_at: str
    updated_at: str


class RecordResult(BaseModel):
    id: int
    job_id: str
    row_index: int
    original_url: Optional[str]
    converted_url: Optional[str]
    status: RecordStatus
    error: Optional[str]
    extra_data: Dict[str, Any] = {}


class RecordsPage(BaseModel):
    job_id: str
    total: int
    page: int
    page_size: int
    items: List[RecordResult]


class ValidationSummary(BaseModel):
    total: int
    valid: int
    invalid: int
    duplicates: int
    invalid_urls: List[str] = []


# ─── File parse response ──────────────────────────────────────────────────────

class ParsedFileInfo(BaseModel):
    file_id: str
    filename: str
    total_rows: int
    columns: List[str]
    url_columns: List[str]          # auto-detected likely URL columns
    sheets: Optional[List[str]] = None  # Excel only
    preview: List[Dict[str, Any]] = []  # first 20 rows


# ─── URL validation ───────────────────────────────────────────────────────────

class UrlValidationResult(BaseModel):
    url: str
    is_valid: bool
    reason: Optional[str] = None


# ─── Auth schemas ─────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    email: str
    user_id: int


class UserInfo(BaseModel):
    id: int
    email: str
    created_at: str

