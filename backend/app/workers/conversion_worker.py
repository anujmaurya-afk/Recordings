"""
Background conversion worker with 10k batching and high-performance bulk writes.

Features:
- BATCH_SIZE = 10,000: Processes records in bounded 10k batches to prevent memory leaks and runaway processes.
- Bulk SQLite Transactions: Flushes updates in chunks using executemany inside a single transaction.
- Responsive Progress: Updates job progress counters after each chunk so the UI progress bar advances smoothly.
- Deduplication: In-memory URL cache reuses signed URLs for duplicate rows in 0ms.
- Cancellation: Gracefully terminates if a job is cancelled or stopped.
- Clean Logging: Logs summary metrics per batch instead of flooding the terminal with 60,000+ individual record lines.
"""
from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.config import get_settings
from app.services import job_service as js
from app.services.recording_service import convert_recording_url

logger = logging.getLogger(__name__)
_settings = get_settings()

BATCH_SIZE = 10_000        # Process pending records in 10k chunks
FLUSH_CHUNK_SIZE = 2_000  # Flush to SQLite in 2k bulk chunks for live progress

_executor = ThreadPoolExecutor(max_workers=max(_settings.max_workers, 4))


def _user_friendly_error(exc: Exception) -> str:
    """Map technical exceptions to user-friendly messages."""
    msg = str(exc)
    if "NoCredentialsError" in type(exc).__name__ or "credentials" in msg.lower():
        return "Authentication failed — AWS credentials not configured"
    if "NoSuchKey" in msg or "404" in msg:
        return "Recording not found (HTTP 404)"
    if "AccessDenied" in msg or "403" in msg:
        return "Access denied to this recording"
    if "EndpointResolutionError" in msg or "Could not connect" in msg.lower():
        return "Could not connect to AWS — check network/region"
    if "Timeout" in type(exc).__name__ or "timed out" in msg.lower():
        return "Request timed out"
    if "InvalidURL" in msg or "Invalid" in msg:
        return "Invalid URL format"
    return f"Conversion failed: {msg[:120]}"


def _process_records_chunk_sync(
    records_chunk: List[Dict[str, Any]],
    provider: str,
    url_cache: Dict[str, str],
) -> Tuple[List[Tuple[str, Optional[str], Optional[str], str, int]], Dict[str, int]]:
    """
    Synchronously convert a chunk of records.
    Runs inside the thread pool executor for raw CPU speed with zero async overhead.
    Returns:
        updates: List of (status, converted_url, error, finished_at, record_id)
        stats: Dictionary of count deltas
    """
    updates: List[Tuple[str, Optional[str], Optional[str], str, int]] = []
    stats = {"processed": 0, "success": 0, "failed": 0, "skipped": 0}
    now = datetime.now(timezone.utc).isoformat()

    for record in records_chunk:
        record_id: int = record["id"]
        original_url: str = (record.get("original_url") or "").strip()

        if not original_url or original_url.lower() in ("nan", "none", "null"):
            updates.append(("failed", None, "Missing URL in source file (empty or blank cell)", now, record_id))
            stats["failed"] += 1
            stats["processed"] += 1
            continue

        # Fast in-memory deduplication
        cached = url_cache.get(original_url)
        if cached:
            updates.append(("success", cached, None, now, record_id))
            stats["success"] += 1
            stats["processed"] += 1
            continue

        try:
            converted_url = convert_recording_url(original_url, provider)
            url_cache[original_url] = converted_url
            updates.append(("success", converted_url, None, now, record_id))
            stats["success"] += 1
            stats["processed"] += 1
        except Exception as exc:  # noqa: BLE001
            err_msg = _user_friendly_error(exc)
            updates.append(("failed", None, err_msg, now, record_id))
            stats["failed"] += 1
            stats["processed"] += 1

    return updates, stats


async def run_conversion_job(job_id: str, provider: str) -> None:
    """
    Main conversion runner.
    Processes jobs in bounded 10,000-record batches.
    """
    logger.info("Starting conversion job %s in 10k batches (provider=%s)", job_id, provider)

    job = await js.get_job(job_id)
    if not job:
        logger.error("Job %s not found", job_id)
        return

    if job["status"] == "cancelled":
        logger.info("Job %s is already cancelled", job_id)
        return

    await js.update_job_status(job_id, "processing")

    url_cache: Dict[str, str] = {}
    # Pre-populate cache with any already-converted URLs
    try:
        url_cache.update(await js.get_url_cache(job_id))
    except Exception as exc:
        logger.warning("Could not pre-populate cache for %s: %s", job_id, exc)

    loop = asyncio.get_event_loop()
    batch_index = 0
    start_time = time.perf_counter()

    try:
        while True:
            # Check for external cancellation
            current_job = await js.get_job(job_id)
            if not current_job or current_job.get("status") == "cancelled":
                logger.info("Job %s was cancelled by user. Halting conversion worker.", job_id)
                return

            # Fetch the next 10,000 pending records
            pending_batch = await js.get_pending_records_batch(job_id, limit=BATCH_SIZE)
            if not pending_batch:
                # No more pending records in this job
                break

            batch_index += 1
            batch_count = len(pending_batch)
            batch_start = time.perf_counter()
            logger.info(
                "Job %s: Starting Batch #%d (%d records)...",
                job_id,
                batch_index,
                batch_count,
            )

            # Process in sub-chunks to flush to DB and keep UI responsive
            for i in range(0, batch_count, FLUSH_CHUNK_SIZE):
                # Check for cancellation between chunks
                active_check = await js.get_job(job_id)
                if active_check and active_check.get("status") == "cancelled":
                    logger.info("Job %s cancelled during batch #%d. Halting.", job_id, batch_index)
                    return

                chunk = pending_batch[i : i + FLUSH_CHUNK_SIZE]
                updates, stats = await loop.run_in_executor(
                    _executor,
                    _process_records_chunk_sync,
                    chunk,
                    provider,
                    url_cache,
                )

                # Bulk write to SQLite in one fast transaction
                await js.bulk_update_records(updates)

                # Atomic increment of job counters
                await js.increment_job_counts(
                    job_id,
                    processed_delta=stats["processed"],
                    successful_delta=stats["success"],
                    failed_delta=stats["failed"],
                    skipped_delta=stats["skipped"],
                )

            batch_elapsed = time.perf_counter() - batch_start
            speed = batch_count / batch_elapsed if batch_elapsed > 0 else 0
            logger.info(
                "Job %s: Completed Batch #%d (%d records in %.2fs — %.0f rec/sec)",
                job_id,
                batch_index,
                batch_count,
                batch_elapsed,
                speed,
            )

        # Refresh exact counts and determine final status
        await js.refresh_job_counts(job_id)
        final_job = await js.get_job(job_id)
        total_time = time.perf_counter() - start_time

        if final_job:
            if final_job.get("status") == "cancelled":
                return

            if final_job["failed_records"] > 0 and final_job["successful_records"] > 0:
                final_status = "completed_with_errors"
            elif final_job["failed_records"] > 0 and final_job["successful_records"] == 0:
                final_status = "failed"
            else:
                final_status = "completed"

            await js.update_job_status(job_id, final_status)
            logger.info(
                "Job %s finished: status=%s total=%d success=%d failed=%d in %.1fs",
                job_id,
                final_status,
                final_job["total_records"],
                final_job["successful_records"],
                final_job["failed_records"],
                total_time,
            )

    except Exception as exc:  # noqa: BLE001
        logger.error("Job %s encountered a fatal error: %s", job_id, exc, exc_info=True)
        await js.update_job_status(job_id, "failed")
