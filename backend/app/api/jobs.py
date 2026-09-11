"""
Jobs API endpoints.

POST   /api/jobs                     — create job (paste URLs, CSV, or Excel)
GET    /api/jobs/{job_id}            — job status + progress
GET    /api/jobs/{job_id}/results    — paginated records with filtering + search
POST   /api/jobs/{job_id}/retry      — retry failed records
GET    /api/jobs/{job_id}/download/csv
GET    /api/jobs/{job_id}/download/excel
"""
from __future__ import annotations

import io
import json
import logging
from typing import Annotated, List, Optional

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.auth import get_current_user
from app.schemas.schemas import (
    CreateJobFromFile,
    CreateJobFromUrls,
    JobProgress,
    RecordsPage,
    RetryFailedRequest,
    ValidationSummary,
)
from app.services import file_parser, job_service as js
from app.services.url_validator import parse_pasted_urls, validate_urls
from app.workers.conversion_worker import run_conversion_job

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _verify_job_ownership(job: dict, current_user: dict) -> None:
    """Ensure the job belongs to the current authenticated user."""
    if job.get("user_id") is not None and job["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Job not found")


def _row_to_job_progress(row: dict) -> JobProgress:
    return JobProgress(
        job_id=row["job_id"],
        status=row["status"],
        total_records=row["total_records"],
        processed_records=row["processed_records"],
        successful_records=row["successful_records"],
        failed_records=row["failed_records"],
        skipped_records=row["skipped_records"],
        provider=row["provider"],
        input_filename=row.get("input_filename"),
        url_column=row.get("url_column"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


# ─── GET /api/jobs — list recent jobs ────────────────────────────────────────
@router.get("", response_model=List[JobProgress])
async def list_jobs(
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """List recent conversion jobs for the current user."""
    jobs = await js.list_recent_jobs(limit=limit, user_id=current_user["id"])
    return [_row_to_job_progress(j) for j in jobs]


# ─── POST /api/jobs — create from pasted URLs ────────────────────────────────

@router.post("/urls", response_model=dict, status_code=201)
async def create_job_from_urls(
    payload: CreateJobFromUrls,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """Create a conversion job from pasted URL text."""
    validation = validate_urls(payload.urls)

    valid_urls = [v.url for v in validation.validated if v.is_valid]
    if not valid_urls:
        raise HTTPException(status_code=422, detail="No valid URLs provided")

    job_id = await js.create_job(
        provider=payload.provider,
        total_records=len(valid_urls),
        input_filename=None,
        url_column=None,
        user_id=current_user["id"],
    )

    records = [
        {"row_index": i, "original_url": url, "extra_data": {}}
        for i, url in enumerate(valid_urls)
    ]
    await js.bulk_insert_records(job_id, records)

    background_tasks.add_task(run_conversion_job, job_id, payload.provider)

    return {
        "job_id": job_id,
        "validation": {
            "total": validation.total,
            "valid": validation.valid,
            "invalid": validation.invalid,
            "duplicates": validation.duplicates,
        },
    }


# ─── POST /api/jobs/file — create from CSV/Excel ──────────────────────────────

@router.post("/file", response_model=dict, status_code=201)
async def create_job_from_file(
    payload: CreateJobFromFile,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """Create a conversion job from a previously uploaded CSV or Excel file."""
    # Determine file type from what's on disk
    csv_path = file_parser.get_upload_path(payload.file_id, [".csv"])
    excel_path = file_parser.get_upload_path(payload.file_id, [".xlsx", ".xls"])

    if csv_path:
        iterator = file_parser.iter_csv_records(payload.file_id, payload.url_column)
        filename = csv_path.name
    elif excel_path:
        iterator = file_parser.iter_excel_records(
            payload.file_id, payload.url_column, payload.sheet_name
        )
        filename = excel_path.name
    else:
        raise HTTPException(status_code=404, detail=f"No uploaded file found for file_id={payload.file_id}")

    # Collect all records (we need the count for job creation)
    all_records = []
    extra_columns_seen: set[str] = set()
    for row_index, url, extra in iterator:
        extra_columns_seen.update(extra.keys())
        all_records.append({
            "row_index": row_index,
            "original_url": url.strip(),
            "extra_data": extra,
        })

    if not all_records:
        raise HTTPException(status_code=422, detail="File appears to be empty or the URL column has no data")

    job_id = await js.create_job(
        provider=payload.provider,
        total_records=len(all_records),
        input_filename=filename,
        url_column=payload.url_column,
        extra_columns=list(extra_columns_seen),
        user_id=current_user["id"],
    )

    await js.bulk_insert_records(job_id, all_records)

    background_tasks.add_task(run_conversion_job, job_id, payload.provider)

    return {"job_id": job_id, "total_records": len(all_records)}


# ─── GET /api/jobs/{job_id} ──────────────────────────────────────────────────

@router.get("/{job_id}", response_model=JobProgress)
async def get_job(job_id: str, current_user: dict = Depends(get_current_user)):
    """Get job status and progress."""
    job = await js.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    _verify_job_ownership(job, current_user)
    return _row_to_job_progress(job)


# ─── GET /api/jobs/{job_id}/results ──────────────────────────────────────────

@router.get("/{job_id}/results", response_model=RecordsPage)
async def get_job_results(
    job_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """Get paginated results for a job."""
    job = await js.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    _verify_job_ownership(job, current_user)

    page_data = await js.get_records_page(
        job_id, page=page, page_size=page_size,
        status_filter=status, search=search,
    )
    return RecordsPage(**page_data)


# ─── POST /api/jobs/{job_id}/retry ───────────────────────────────────────────

@router.post("/{job_id}/retry", response_model=dict)
async def retry_failed(
    job_id: str,
    background_tasks: BackgroundTasks,
    payload: RetryFailedRequest = Body(default=RetryFailedRequest()),
    current_user: dict = Depends(get_current_user),
):
    """Retry all failed records in a job without reprocessing successful ones."""
    job = await js.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    _verify_job_ownership(job, current_user)
    if job["status"] == "processing":
        raise HTTPException(status_code=409, detail="Job is still processing")

    count = await js.reset_failed_records(job_id)
    if count == 0:
        raise HTTPException(status_code=422, detail="No failed records to retry")

    provider = payload.provider or job["provider"]
    background_tasks.add_task(run_conversion_job, job_id, provider)

    return {"job_id": job_id, "retrying": count, "provider": provider}


# ─── GET /api/jobs/{job_id}/download/csv ─────────────────────────────────────

@router.get("/{job_id}/download/csv")
async def download_csv(job_id: str, current_user: dict = Depends(get_current_user)):
    """Download all results as a CSV file preserving original columns."""
    job = await js.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    _verify_job_ownership(job, current_user)

    records = await js.get_all_records(job_id)
    df = _build_export_df(records, job)

    buf = io.BytesIO()
    df.to_csv(buf, index=False, encoding="utf-8-sig")
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{job_id}_results.csv"'},
    )


# ─── GET /api/jobs/{job_id}/download/excel ───────────────────────────────────

@router.get("/{job_id}/download/excel")
async def download_excel(job_id: str, current_user: dict = Depends(get_current_user)):
    """Download all results as an Excel file preserving original columns."""
    job = await js.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    _verify_job_ownership(job, current_user)

    records = await js.get_all_records(job_id)
    df = _build_export_df(records, job)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Results")
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{job_id}_results.xlsx"'},
    )


# ─── POST /api/jobs/{job_id}/cancel ──────────────────────────────────────────

@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str, current_user: dict = Depends(get_current_user)):
    """Cancel a running or pending conversion job."""
    job = await js.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    _verify_job_ownership(job, current_user)
    await js.cancel_job(job_id)
    return {"message": f"Job {job_id} cancelled", "status": "cancelled"}


# ─── GET /api/jobs/{job_id}/errors ───────────────────────────────────────────

@router.get("/{job_id}/errors")
async def get_job_errors(job_id: str, current_user: dict = Depends(get_current_user)):
    """Return error summary and sample of failed records for a job."""
    job = await js.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    _verify_job_ownership(job, current_user)

    failed = await js.get_failed_records(job_id)
    breakdown: dict[str, int] = {}
    for r in failed:
        err = r.get("error") or "Unknown error"
        breakdown[err] = breakdown.get(err, 0) + 1

    has_file = bool(job.get("input_filename"))
    sample = [
        {
            "row_number": r["row_index"] + 2 if has_file else r["row_index"] + 1,
            "original_url": r.get("original_url", ""),
            "error": r.get("error", "Unknown error"),
            "extra_data": r.get("extra_data", {}),
        }
        for r in failed[:50]
    ]

    return {
        "job_id": job_id,
        "total_failed": len(failed),
        "error_breakdown": breakdown,
        "sample_errors": sample,
    }


# ─── GET /api/jobs/{job_id}/download/errors ───────────────────────────────────

@router.get("/{job_id}/download/errors")
async def download_errors_csv(job_id: str, current_user: dict = Depends(get_current_user)):
    """Download a dedicated CSV error log of all failed records with their reasons."""
    job = await js.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    _verify_job_ownership(job, current_user)

    failed = await js.get_failed_records(job_id)
    if not failed:
        raise HTTPException(status_code=404, detail=f"No failed records for job {job_id}")

    rows = []
    has_file = bool(job.get("input_filename"))
    for r in failed:
        extra = r.get("extra_data") or {}
        row: dict = {
            "row_number": r["row_index"] + 2 if has_file else r["row_index"] + 1,
            "original_url": r.get("original_url", ""),
            "status": "failed",
            "error_reason": r.get("error", "Unknown error"),
        }
        if isinstance(extra, dict):
            row.update(extra)
        rows.append(row)

    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_csv(buf, index=False, encoding="utf-8-sig")
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{job_id}_error_log.csv"'},
    )


# ─── Helper ──────────────────────────────────────────────────────────────────

def _build_export_df(records: list, job: dict) -> pd.DataFrame:
    """Build a DataFrame with original columns + conversion result columns."""
    rows = []
    for r in records:
        extra = r.get("extra_data") or {}
        row: dict = {}
        if isinstance(extra, dict):
            row.update(extra)
        row["original_url"] = r.get("original_url", "")
        row["converted_url"] = r.get("converted_url", "")
        row["status"] = r.get("status", "")
        row["error"] = r.get("error", "")
        rows.append(row)

    return pd.DataFrame(rows) if rows else pd.DataFrame()
