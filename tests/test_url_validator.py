"""Tests for URL validation utilities."""
from __future__ import annotations

import pytest
from app.services.url_validator import is_valid_s3_url, parse_pasted_urls, validate_urls


class TestIsValidS3Url:
    def test_valid_s3_https_url(self):
        url = "https://resolve-x-production.s3.ap-south-1.amazonaws.com/cpass/sample.wav"
        valid, reason = is_valid_s3_url(url)
        assert valid is True
        assert reason is None

    def test_valid_s3_uri(self):
        url = "s3://my-bucket/path/to/recording.wav"
        valid, reason = is_valid_s3_url(url)
        assert valid is True

    def test_invalid_empty_string(self):
        valid, reason = is_valid_s3_url("")
        assert valid is False
        assert "Empty" in reason

    def test_invalid_none_like(self):
        valid, reason = is_valid_s3_url("   ")
        assert valid is False

    def test_invalid_random_text(self):
        valid, reason = is_valid_s3_url("not-a-url")
        assert valid is False

    def test_valid_generic_https(self):
        # Generic HTTPS URLs should also pass (fail gracefully in worker)
        url = "https://example.com/recording.wav"
        valid, _ = is_valid_s3_url(url)
        assert valid is True

    def test_valid_s3_url_without_region(self):
        url = "https://mybucket.s3.amazonaws.com/file.wav"
        valid, _ = is_valid_s3_url(url)
        assert valid is True


class TestValidateUrls:
    def test_mixed_valid_invalid(self):
        urls = [
            "https://bucket.s3.ap-south-1.amazonaws.com/file.wav",
            "",
            "not-a-url",
            "https://bucket.s3.amazonaws.com/file2.wav",
        ]
        result = validate_urls(urls)
        assert result.total == 4
        assert result.valid == 2
        assert result.invalid == 2

    def test_duplicates_counted(self):
        url = "https://bucket.s3.amazonaws.com/file.wav"
        result = validate_urls([url, url, url])
        assert result.total == 3
        assert result.duplicates == 2

    def test_empty_list(self):
        result = validate_urls([])
        assert result.total == 0
        assert result.valid == 0

    def test_all_valid(self):
        urls = [
            "https://b.s3.ap-south-1.amazonaws.com/a.wav",
            "https://b.s3.ap-south-1.amazonaws.com/b.wav",
        ]
        result = validate_urls(urls)
        assert result.valid == 2
        assert result.invalid == 0
        assert result.duplicates == 0


class TestParsePastedUrls:
    def test_newline_separated(self):
        text = "https://a.s3.amazonaws.com/a.wav\nhttps://a.s3.amazonaws.com/b.wav"
        urls = parse_pasted_urls(text)
        assert len(urls) == 2

    def test_comma_separated(self):
        text = "https://a.s3.amazonaws.com/a.wav,https://a.s3.amazonaws.com/b.wav"
        urls = parse_pasted_urls(text)
        assert len(urls) == 2

    def test_mixed_blank_lines(self):
        text = "https://a.s3.amazonaws.com/a.wav\n\n\nhttps://a.s3.amazonaws.com/b.wav\n"
        urls = parse_pasted_urls(text)
        assert len(urls) == 2

    def test_crlf_line_endings(self):
        text = "https://a.s3.amazonaws.com/a.wav\r\nhttps://a.s3.amazonaws.com/b.wav"
        urls = parse_pasted_urls(text)
        assert len(urls) == 2
