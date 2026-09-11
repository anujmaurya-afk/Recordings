"""Tests for recording service adapter."""
from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock, patch

import pytest

# Ensure backend root is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


class TestRecordingService:
    """Tests for the recording_service adapter."""

    def test_uses_presigned_url_for_recordings_provider(self):
        mock_url = "https://presigned.example.com/file.wav?X-Amz-Signature=abc"
        with patch("recordings.generate_presigned_url", return_value=mock_url) as mock_fn:
            from app.services.recording_service import convert_recording_url
            result = convert_recording_url(
                "https://bucket.s3.ap-south-1.amazonaws.com/file.wav",
                provider="recordings",
            )
            assert result == mock_url
            mock_fn.assert_called_once()

    def test_uses_cloudfront_url_for_cloudfront_provider(self):
        mock_url = "https://d30beya68etkmf.cloudfront.net/cpass/file.wav"
        with patch("cloudfront.generate_cloudfront_url", return_value=mock_url) as mock_fn:
            from app.services.recording_service import convert_recording_url
            result = convert_recording_url(
                "https://bucket.s3.ap-south-1.amazonaws.com/file.wav",
                provider="cloudfront",
            )
            assert result == mock_url
            mock_fn.assert_called_once()

    def test_defaults_to_recordings_provider(self):
        """When no provider given, should use recordings (presigned URL)."""
        mock_url = "https://presigned.example.com/file.wav?sig=xyz"
        with patch("recordings.generate_presigned_url", return_value=mock_url):
            from app.services.recording_service import convert_recording_url
            result = convert_recording_url(
                "https://bucket.s3.ap-south-1.amazonaws.com/file.wav",
                provider=None,
            )
            assert result == mock_url


class TestPresignedUrl:
    """Tests for recordings.py parse_s3_url helper."""

    def test_parse_https_url(self):
        from recordings import parse_s3_url
        bucket, key = parse_s3_url(
            "https://mybucket.s3.ap-south-1.amazonaws.com/folder/file.wav"
        )
        assert bucket == "mybucket"
        assert key == "folder/file.wav"

    def test_parse_s3_uri(self):
        from recordings import parse_s3_url
        bucket, key = parse_s3_url("s3://mybucket/folder/file.wav")
        assert bucket == "mybucket"
        assert key == "folder/file.wav"


class TestCloudfrontUrl:
    """Tests for cloudfront.py URL generation."""

    def test_converts_s3_to_cloudfront(self):
        import os
        os.environ["CLOUDFRONT_DOMAIN"] = "https://d30beya68etkmf.cloudfront.net"
        os.environ["CLOUDFRONT_KEY_PAIR_ID"] = ""  # no signing
        os.environ["CLOUDFRONT_PRIVATE_KEY"] = ""

        from cloudfront import generate_cloudfront_url
        result = generate_cloudfront_url(
            "https://mybucket.s3.ap-south-1.amazonaws.com/cpass/sample.wav"
        )
        assert result == "https://d30beya68etkmf.cloudfront.net/cpass/sample.wav"

    def test_handles_nested_path(self):
        from cloudfront import generate_cloudfront_url
        result = generate_cloudfront_url(
            "https://bucket.s3.amazonaws.com/a/b/c/d/recording.mp3"
        )
        assert result.endswith("/a/b/c/d/recording.mp3")
