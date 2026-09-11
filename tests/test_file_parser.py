"""Tests for CSV and Excel file parsing."""
from __future__ import annotations

import io
import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from app.services.file_parser import (
    detect_url_columns,
    iter_csv_records,
    parse_csv_file,
)


def _write_temp_csv(content: str, file_id: str, upload_dir: Path) -> Path:
    upload_dir.mkdir(parents=True, exist_ok=True)
    path = upload_dir / f"{file_id}.csv"
    path.write_text(content, encoding="utf-8")
    return path


class TestDetectUrlColumns:
    def test_detects_url_column(self):
        cols = ["name", "recording_url", "date"]
        result = detect_url_columns(cols)
        assert "recording_url" in result

    def test_detects_link_column(self):
        cols = ["lead_code", "audio_link", "customer"]
        result = detect_url_columns(cols)
        assert "audio_link" in result

    def test_no_url_columns(self):
        cols = ["name", "email", "phone"]
        result = detect_url_columns(cols)
        assert result == []

    def test_multiple_url_columns(self):
        cols = ["recording_url", "thumbnail_url", "name"]
        result = detect_url_columns(cols)
        assert len(result) == 2


class TestParseCsvFile:
    def test_parses_valid_csv(self, tmp_path):
        file_id = str(uuid.uuid4())
        content = "name,recording_url,date\nAlice,https://bucket.s3.amazonaws.com/a.wav,2024-01-01\n"
        _write_temp_csv(content, file_id, tmp_path)

        with patch("app.services.file_parser.UPLOAD_DIR", tmp_path):
            result = parse_csv_file(file_id)

        assert result["total_rows"] == 1
        assert "recording_url" in result["columns"]
        assert "recording_url" in result["url_columns"]
        assert len(result["preview"]) == 1

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            with patch("app.services.file_parser.UPLOAD_DIR", Path("/nonexistent")):
                parse_csv_file("nonexistent-id")


class TestIterCsvRecords:
    def test_iterates_records(self, tmp_path):
        file_id = str(uuid.uuid4())
        content = "lead,url\nL1,https://b.s3.amazonaws.com/1.wav\nL2,https://b.s3.amazonaws.com/2.wav\n"
        _write_temp_csv(content, file_id, tmp_path)

        with patch("app.services.file_parser.UPLOAD_DIR", tmp_path):
            records = list(iter_csv_records(file_id, url_column="url"))

        assert len(records) == 2
        assert records[0][1] == "https://b.s3.amazonaws.com/1.wav"
        assert records[0][2]["lead"] == "L1"

    def test_preserves_extra_columns(self, tmp_path):
        file_id = str(uuid.uuid4())
        content = "lead_code,customer,url\nA001,John,https://b.s3.amazonaws.com/1.wav\n"
        _write_temp_csv(content, file_id, tmp_path)

        with patch("app.services.file_parser.UPLOAD_DIR", tmp_path):
            records = list(iter_csv_records(file_id, url_column="url"))

        _, url, extra = records[0]
        assert "lead_code" in extra
        assert "customer" in extra
        assert "url" not in extra  # URL column stripped from extra
