"""
CSV and Excel file parsing service.

Streams large files efficiently without loading everything into memory.
"""
from __future__ import annotations

import io
import json
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

import pandas as pd

from app.config import get_settings

logger = logging.getLogger(__name__)
_settings = get_settings()

# Temp directory for uploaded files. On serverless platforms (e.g. Vercel)
# only /tmp is writable, so default there automatically.
UPLOAD_DIR = Path("/tmp/uploads") if os.environ.get("VERCEL") else Path("./data/uploads")

# Regex patterns for auto-detecting URL columns
_URL_COLUMN_PATTERNS = re.compile(
    r"(url|link|recording|audio|media|src|source|href)",
    re.IGNORECASE,
)


def get_upload_dir() -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


def save_upload(content: bytes, filename: str) -> str:
    """Save uploaded file to temp directory, return file_id."""
    file_id = str(uuid.uuid4())
    ext = Path(filename).suffix.lower()
    safe_name = f"{file_id}{ext}"
    path = get_upload_dir() / safe_name
    path.write_bytes(content)
    logger.info("Saved upload %s → %s (%d bytes)", filename, path, len(content))
    return file_id


def get_upload_path(file_id: str, extensions: List[str]) -> Optional[Path]:
    """Locate an uploaded file by its file_id."""
    upload_dir = get_upload_dir()
    for ext in extensions:
        path = upload_dir / f"{file_id}{ext}"
        if path.exists():
            return path
    return None


def detect_url_columns(columns: List[str]) -> List[str]:
    """Auto-detect which column names are likely recording URL columns."""
    return [col for col in columns if _URL_COLUMN_PATTERNS.search(str(col))]


def parse_csv_file(
    file_id: str,
    url_column: Optional[str] = None,
    preview_rows: int = 20,
) -> Dict[str, Any]:
    """
    Parse a CSV file and return metadata + preview.
    If url_column is given, validates it exists.
    """
    path = get_upload_path(file_id, [".csv"])
    if not path:
        raise FileNotFoundError(f"No CSV file found for file_id={file_id}")

    # Count rows efficiently
    total_rows = 0
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        for i, _ in enumerate(f):
            if i > 0:
                total_rows += 1

    # Read a preview (header + first preview_rows)
    df_preview = pd.read_csv(path, nrows=preview_rows, encoding="utf-8-sig", on_bad_lines="skip")
    columns = df_preview.columns.tolist()

    if url_column and url_column not in columns:
        raise ValueError(f"Column '{url_column}' not found in CSV. Available: {columns}")

    url_cols = detect_url_columns(columns)

    return {
        "file_id": file_id,
        "filename": path.name,
        "total_rows": total_rows,
        "columns": columns,
        "url_columns": url_cols,
        "sheets": None,
        "preview": df_preview.where(pd.notna(df_preview), None).to_dict(orient="records"),
    }


def parse_excel_file(
    file_id: str,
    sheet_name: Optional[str] = None,
    url_column: Optional[str] = None,
    preview_rows: int = 20,
) -> Dict[str, Any]:
    """
    Parse an Excel file and return metadata + preview.
    """
    path = get_upload_path(file_id, [".xlsx", ".xls"])
    if not path:
        raise FileNotFoundError(f"No Excel file found for file_id={file_id}")

    xl = pd.ExcelFile(path)
    sheets = xl.sheet_names

    active_sheet = sheet_name if sheet_name and sheet_name in sheets else sheets[0]

    df_preview = xl.parse(active_sheet, nrows=preview_rows)
    total_rows = xl.parse(active_sheet).shape[0]
    columns = df_preview.columns.tolist()

    if url_column and url_column not in columns:
        raise ValueError(f"Column '{url_column}' not found in sheet '{active_sheet}'. Available: {columns}")

    url_cols = detect_url_columns(columns)

    return {
        "file_id": file_id,
        "filename": path.name,
        "total_rows": total_rows,
        "columns": columns,
        "url_columns": url_cols,
        "sheets": sheets,
        "active_sheet": active_sheet,
        "preview": df_preview.where(pd.notna(df_preview), None).to_dict(orient="records"),
    }


def iter_csv_records(
    file_id: str,
    url_column: str,
    chunk_size: int = 500,
) -> Generator[Tuple[int, str, Dict[str, Any]], None, None]:
    """
    Stream CSV records as (row_index, original_url, extra_data_dict).
    Yields one record at a time. Memory-efficient for large files.
    """
    path = get_upload_path(file_id, [".csv"])
    if not path:
        raise FileNotFoundError(f"No CSV file found for file_id={file_id}")

    row_index = 0
    for chunk in pd.read_csv(
        path,
        chunksize=chunk_size,
        encoding="utf-8-sig",
        on_bad_lines="skip",
        dtype=str,
    ):
        for _, row in chunk.iterrows():
            raw_val = row.get(url_column, "")
            raw_str = str(raw_val).strip() if pd.notna(raw_val) else ""
            url = "" if raw_str.lower() in ("nan", "none", "null") else raw_str
            extra = {k: str(v) if pd.notna(v) else "" for k, v in row.items() if k != url_column}
            yield row_index, url, extra
            row_index += 1


def iter_excel_records(
    file_id: str,
    url_column: str,
    sheet_name: Optional[str] = None,
) -> Generator[Tuple[int, str, Dict[str, Any]], None, None]:
    """
    Stream Excel records as (row_index, original_url, extra_data_dict).
    """
    path = get_upload_path(file_id, [".xlsx", ".xls"])
    if not path:
        raise FileNotFoundError(f"No Excel file found for file_id={file_id}")

    xl = pd.ExcelFile(path)
    active_sheet = sheet_name if sheet_name else xl.sheet_names[0]
    df = xl.parse(active_sheet, dtype=str)

    for row_index, (_, row) in enumerate(df.iterrows()):
        raw_val = row.get(url_column, "")
        raw_str = str(raw_val).strip() if pd.notna(raw_val) else ""
        url = "" if raw_str.lower() in ("nan", "none", "null") else raw_str
        extra = {k: str(v) if pd.notna(v) else "" for k, v in row.items() if k != url_column}
        yield row_index, url, extra


def delete_upload(file_id: str) -> None:
    """Delete an uploaded file by its file_id (any extension)."""
    for ext in [".csv", ".xlsx", ".xls"]:
        path = get_upload_path(file_id, [ext])
        if path and path.exists():
            path.unlink(missing_ok=True)
            logger.info("Deleted upload file: %s", path)
