"""
Job service — CRUD operations on jobs and records using SQLite.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiosqlite

from app.models.db import get_db

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_job_id() -> str:
    now = datetime.now(timezone.utc)
    short = str(uuid.uuid4()).split("-")[0].upper()
    return f"JOB-{now.strftime('%Y%m%d')}-{short}"


# ─── Job CRUD ────────────────────────────────────────────────────────────────

async def create_job(
    provider: str,
    total_records: int,
    input_filename: Optional[str] = None,
    url_column: Optional[str] = None,
    extra_columns: Optional[List[str]] = None,
) -> str:
    job_id = generate_job_id()
    now = _now()
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO jobs (job_id, created_at, updated_at, status, total_records,
                              processed_records, successful_records, failed_records,
                              skipped_records, input_filename, url_column, provider, extra_columns)
            VALUES (?, ?, ?, 'pending', ?, 0, 0, 0, 0, ?, ?, ?, ?)
            """,
            (
                job_id, now, now, total_records,
                input_filename, url_column, provider,
                json.dumps(extra_columns or []),
            ),
        )
        await db.commit()
    logger.info("Created job %s (total=%d, provider=%s)", job_id, total_records, provider)
    return job_id


async def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        async with db.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)) as cur:
            row = await cur.fetchone()
            if row is None:
                return None
            return dict(row)


async def list_recent_jobs(limit: int = 10) -> List[Dict[str, Any]]:
    """Return the most recent conversion jobs."""
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM jobs ORDER BY rowid DESC LIMIT ?",
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def update_job_status(job_id: str, status: str) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE jobs SET status = ?, updated_at = ? WHERE job_id = ?",
            (status, _now(), job_id),
        )
        await db.commit()


async def refresh_job_counts(job_id: str) -> None:
    """Recompute processed/successful/failed/skipped from records table."""
    async with get_db() as db:
        async with db.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE status != 'pending') AS processed,
                COUNT(*) FILTER (WHERE status = 'success')  AS successful,
                COUNT(*) FILTER (WHERE status = 'failed')   AS failed,
                COUNT(*) FILTER (WHERE status = 'skipped')  AS skipped
            FROM records WHERE job_id = ?
            """,
            (job_id,),
        ) as cur:
            row = await cur.fetchone()

        await db.execute(
            """
            UPDATE jobs
            SET processed_records = ?, successful_records = ?,
                failed_records = ?, skipped_records = ?, updated_at = ?
            WHERE job_id = ?
            """,
            (row[0], row[1], row[2], row[3], _now(), job_id),
        )
        await db.commit()


# ─── Record CRUD ─────────────────────────────────────────────────────────────

async def bulk_insert_records(
    job_id: str,
    records: List[Dict[str, Any]],
) -> None:
    """Insert many pending records in one transaction."""
    async with get_db() as db:
        await db.executemany(
            """
            INSERT INTO records (job_id, row_index, original_url, status, extra_data)
            VALUES (?, ?, ?, 'pending', ?)
            """,
            [
                (job_id, r["row_index"], r["original_url"], json.dumps(r.get("extra_data", {})))
                for r in records
            ],
        )
        await db.commit()


async def get_pending_records(job_id: str) -> List[Dict[str, Any]]:
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM records WHERE job_id = ? AND status = 'pending' ORDER BY row_index",
            (job_id,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_pending_records_batch(job_id: str, limit: int = 10000) -> List[Dict[str, Any]]:
    """Fetch a bounded batch (e.g. 10,000) of pending records to prevent memory exhaustion."""
    async with get_db() as db:
        async with db.execute(
            "SELECT id, row_index, original_url, extra_data FROM records "
            "WHERE job_id = ? AND status = 'pending' ORDER BY row_index LIMIT ?",
            (job_id, limit),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def bulk_update_records(updates: List[tuple]) -> None:
    """
    Bulk update records in a single fast SQLite transaction.
    Each item in updates is a tuple: (status, converted_url, error, finished_at, record_id)
    """
    if not updates:
        return
    async with get_db() as db:
        await db.executemany(
            """
            UPDATE records
            SET status = ?, converted_url = ?, error = ?, finished_at = ?
            WHERE id = ?
            """,
            updates,
        )
        await db.commit()


async def increment_job_counts(
    job_id: str,
    processed_delta: int,
    successful_delta: int,
    failed_delta: int,
    skipped_delta: int,
) -> None:
    """Atomic update of job progress counters for live UI responsiveness without full table scans."""
    now = _now()
    async with get_db() as db:
        await db.execute(
            """
            UPDATE jobs
            SET processed_records = processed_records + ?,
                successful_records = successful_records + ?,
                failed_records = failed_records + ?,
                skipped_records = skipped_records + ?,
                updated_at = ?
            WHERE job_id = ?
            """,
            (processed_delta, successful_delta, failed_delta, skipped_delta, now, job_id),
        )
        await db.commit()


async def cancel_job(job_id: str) -> None:
    """Mark a job as cancelled so background workers stop processing remaining batches."""
    await update_job_status(job_id, "cancelled")


async def get_failed_records(job_id: str) -> List[Dict[str, Any]]:
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM records WHERE job_id = ? AND status = 'failed' ORDER BY row_index",
            (job_id,),
        ) as cur:
            rows = await cur.fetchall()
    result = []
    for r in rows:
        item = dict(r)
        try:
            item["extra_data"] = json.loads(item.get("extra_data") or "{}")
        except Exception:
            item["extra_data"] = {}
        result.append(item)
    return result


async def update_record(
    record_id: int,
    status: str,
    converted_url: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    now = _now()
    async with get_db() as db:
        await db.execute(
            """
            UPDATE records
            SET status = ?, converted_url = ?, error = ?, finished_at = ?
            WHERE id = ?
            """,
            (status, converted_url, error, now, record_id),
        )
        await db.commit()


async def reset_failed_records(job_id: str) -> int:
    """Reset all failed records to 'pending' for retry. Returns count reset."""
    async with get_db() as db:
        async with db.execute(
            "SELECT COUNT(*) FROM records WHERE job_id = ? AND status = 'failed'",
            (job_id,),
        ) as cur:
            count = (await cur.fetchone())[0]

        await db.execute(
            """
            UPDATE records
            SET status = 'pending', converted_url = NULL, error = NULL,
                started_at = NULL, finished_at = NULL
            WHERE job_id = ? AND status = 'failed'
            """,
            (job_id,),
        )
        # Update job totals
        await db.execute(
            """
            UPDATE jobs
            SET failed_records = 0,
                processed_records = processed_records - ?,
                total_records = total_records,
                updated_at = ?
            WHERE job_id = ?
            """,
            (count, _now(), job_id),
        )
        await db.commit()
    return count


async def get_records_page(
    job_id: str,
    page: int = 1,
    page_size: int = 100,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    offset = (page - 1) * page_size
    conditions = ["job_id = ?"]
    params: List[Any] = [job_id]

    if status_filter:
        conditions.append("status = ?")
        params.append(status_filter)

    if search:
        conditions.append("(original_url LIKE ? OR converted_url LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    where = " AND ".join(conditions)

    async with get_db() as db:
        async with db.execute(
            f"SELECT COUNT(*) FROM records WHERE {where}", params
        ) as cur:
            total = (await cur.fetchone())[0]

        async with db.execute(
            f"SELECT * FROM records WHERE {where} ORDER BY row_index LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ) as cur:
            rows = await cur.fetchall()

    items = []
    for row in rows:
        r = dict(row)
        try:
            r["extra_data"] = json.loads(r.get("extra_data") or "{}")
        except Exception:
            r["extra_data"] = {}
        items.append(r)

    return {
        "job_id": job_id,
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


async def get_all_records(job_id: str) -> List[Dict[str, Any]]:
    """Return all records for a job (for CSV/Excel export)."""
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM records WHERE job_id = ? ORDER BY row_index",
            (job_id,),
        ) as cur:
            rows = await cur.fetchall()

    result = []
    for row in rows:
        r = dict(row)
        try:
            r["extra_data"] = json.loads(r.get("extra_data") or "{}")
        except Exception:
            r["extra_data"] = {}
        result.append(r)
    return result


async def get_url_cache(job_id: str) -> Dict[str, str]:
    """Return a mapping of original_url → converted_url for deduplication."""
    async with get_db() as db:
        async with db.execute(
            "SELECT original_url, converted_url FROM records "
            "WHERE job_id = ? AND status = 'success' AND converted_url IS NOT NULL",
            (job_id,),
        ) as cur:
            rows = await cur.fetchall()
    return {row[0]: row[1] for row in rows}
