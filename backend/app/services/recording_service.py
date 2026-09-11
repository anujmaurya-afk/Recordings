"""
Thin adapter over recordings.py and cloudfront.py.

The frontend never knows which provider was used — it simply receives a converted_url.
"""
from __future__ import annotations

import logging
import sys
import os

# Ensure the backend root is on the path so the original modules are importable
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from recordings import generate_presigned_url  # noqa: E402
from cloudfront import generate_cloudfront_url  # noqa: E402
from app.config import get_settings  # noqa: E402

logger = logging.getLogger(__name__)
_settings = get_settings()


def convert_recording_url(s3_url: str, provider: str | None = None) -> str:
    """
    Convert an S3 URL to a presigned or CloudFront URL.

    Parameters
    ----------
    s3_url   : The raw S3 URL (https://bucket.s3.region.amazonaws.com/key or s3://bucket/key)
    provider : "recordings" for 7-day presigned URL (default)
               "cloudfront" for CloudFront URL (30-day signed if credentials configured)

    Returns
    -------
    str : The converted URL ready for the end user
    """
    effective_provider = provider or _settings.url_provider

    if effective_provider == "cloudfront":
        logger.debug("Using CloudFront provider for URL: %s", s3_url[:60])
        return generate_cloudfront_url(s3_url)

    # Default: recordings.py presigned URL (7-day)
    logger.debug("Using S3 presigned URL provider for URL: %s", s3_url[:60])
    return generate_presigned_url(s3_url)
