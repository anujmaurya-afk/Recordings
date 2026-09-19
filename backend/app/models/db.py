from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

import aiosqlite

from app.config import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()
DB_PATH = _settings.database_path

DDL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS jobs (
    job_id          TEXT PRIMARY KEY,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    total_records   INTEGER DEFAULT 0,
    processed_records INTEGER DEFAULT 0,
    successful_records INTEGER DEFAULT 0,
    failed_records  INTEGER DEFAULT 0,
    skipped_records INTEGER DEFAULT 0,
    input_filename  TEXT,
    url_column      TEXT,
    provider        TEXT DEFAULT 'recordings',
    extra_columns   TEXT DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id          TEXT NOT NULL,
    row_index       INTEGER NOT NULL,
    original_url    TEXT,
    converted_url   TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',
    error           TEXT,
    extra_data      TEXT DEFAULT '{}',
    started_at      TEXT,
    finished_at     TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_records_job_id ON records(job_id);
CREATE INDEX IF NOT EXISTS idx_records_status ON records(job_id, status);
CREATE INDEX IF NOT EXISTS idx_records_url ON records(original_url);
"""


@asynccontextmanager
async def get_db():
    """Async context manager that yields a configured aiosqlite connection."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        yield db


async def init_db() -> None:
    """Create database directory and tables if they don't exist."""
    db_dir = os.path.dirname(os.path.abspath(DB_PATH))
    os.makedirs(db_dir, exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(DDL)
        await db.commit()
    logger.info("Database initialised at %s", DB_PATH)
