"""
URL validation utilities.

Validates that input strings are well-formed S3 URLs (or s3:// URIs),
deduplicates, and produces a summary.
"""
from __future__ import annotations

import re
from typing import Dict, List, NamedTuple
from urllib.parse import urlparse

# S3 HTTPS URL pattern: https://bucket.s3.region.amazonaws.com/key
_S3_HTTPS = re.compile(
    r"^https?://[a-z0-9.\-]+\.s3(\.[a-z0-9\-]+)?\.amazonaws\.com/.+",
    re.IGNORECASE,
)

# s3:// URI pattern
_S3_URI = re.compile(r"^s3://[a-z0-9.\-]+/.+", re.IGNORECASE)


class UrlValidation(NamedTuple):
    url: str
    is_valid: bool
    reason: str | None


class ValidationSummaryResult(NamedTuple):
    total: int
    valid: int
    invalid: int
    duplicates: int
    validated: List[UrlValidation]


def is_valid_s3_url(url: str) -> tuple[bool, str | None]:
    """Return (True, None) if valid, or (False, reason) if not."""
    if not url or not url.strip():
        return False, "Empty URL"

    url = url.strip()

    if _S3_URI.match(url):
        return True, None

    if _S3_HTTPS.match(url):
        return True, None

    # Try generic URL parse fallback
    try:
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https") and parsed.netloc and parsed.path:
            # Accept any HTTPS URL — the worker will fail gracefully if it's not an S3 URL
            return True, None
    except Exception:
        pass

    return False, "Not a valid S3 URL or HTTP URL"


def validate_urls(raw_urls: List[str]) -> ValidationSummaryResult:
    """
    Validate and deduplicate a list of URL strings.

    Returns a ValidationSummaryResult with per-URL validation details.
    Duplicate URLs are flagged but still included (each row preserved).
    """
    seen: Dict[str, int] = {}  # url → first occurrence index
    results: List[UrlValidation] = []
    dup_count = 0

    for raw in raw_urls:
        url = raw.strip() if raw else ""
        valid, reason = is_valid_s3_url(url)

        is_dup = url and url in seen
        if is_dup:
            dup_count += 1

        if url and not is_dup:
            seen[url] = len(results)

        results.append(UrlValidation(url=url, is_valid=valid, reason=reason))

    valid_count = sum(1 for r in results if r.is_valid)
    invalid_count = sum(1 for r in results if not r.is_valid)

    return ValidationSummaryResult(
        total=len(results),
        valid=valid_count,
        invalid=invalid_count,
        duplicates=dup_count,
        validated=results,
    )


def parse_pasted_urls(raw_text: str) -> List[str]:
    """
    Parse a block of pasted text into individual URLs.
    Supports newline-separated and comma-separated formats.
    """
    # Split on newlines first, then on commas within each line
    lines = raw_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    urls: List[str] = []
    for line in lines:
        # Split on commas too
        parts = line.split(",")
        for part in parts:
            stripped = part.strip()
            if stripped:
                urls.append(stripped)
    return urls
