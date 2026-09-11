"""
File upload parsing endpoints.

POST /api/parse/csv    — upload CSV → columns, row count, preview
POST /api/parse/excel  — upload Excel → sheets, columns, row count, preview
POST /api/parse/excel/sheet — select sheet → columns, preview
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import get_settings
from app.schemas.schemas import ParsedFileInfo
from app.services import file_parser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/parse", tags=["uploads"])
_settings = get_settings()


def _check_file_size(content: bytes, filename: str) -> None:
    if len(content) > _settings.max_file_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File '{filename}' exceeds maximum size of {_settings.max_file_size_mb} MB",
        )


def _check_extension(filename: str, allowed: list[str]) -> None:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '.{ext}'. Allowed: {allowed}",
        )


@router.post("/csv", response_model=ParsedFileInfo)
async def parse_csv(file: UploadFile = File(...)):
    """Upload a CSV file and return column info, row count, and a preview."""
    _check_extension(file.filename or "", ["csv"])
    content = await file.read()
    _check_file_size(content, file.filename or "file.csv")

    file_id = file_parser.save_upload(content, file.filename or "upload.csv")

    try:
        info = file_parser.parse_csv_file(file_id)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ParsedFileInfo(**info)


@router.post("/excel", response_model=ParsedFileInfo)
async def parse_excel(
    file: UploadFile = File(...),
    sheet_name: str | None = Form(default=None),
):
    """Upload an Excel file and return sheet list, column info, row count, and preview."""
    _check_extension(file.filename or "", ["xlsx", "xls"])
    content = await file.read()
    _check_file_size(content, file.filename or "file.xlsx")

    file_id = file_parser.save_upload(content, file.filename or "upload.xlsx")

    try:
        info = file_parser.parse_excel_file(file_id, sheet_name=sheet_name)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ParsedFileInfo(**info)


@router.get("/excel/{file_id}/sheet", response_model=ParsedFileInfo)
async def parse_excel_sheet(file_id: str, sheet_name: str):
    """Select a specific sheet in an already-uploaded Excel file."""
    try:
        info = file_parser.parse_excel_file(file_id, sheet_name=sheet_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ParsedFileInfo(**info)
