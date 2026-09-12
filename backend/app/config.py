from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # AWS
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "ap-south-1"

    # S3 presigned URL expiry
    recording_url_expiry_seconds: int = 604800  # 7 days

    # CloudFront
    cloudfront_domain: str = "https://d30beya68etkmf.cloudfront.net"
    cloudfront_url_expiry_days: int = 30
    cloudfront_key_pair_id: str = ""
    cloudfront_private_key: str = ""

    # URL provider
    url_provider: Literal["recordings", "cloudfront"] = "recordings"

    # Workers
    max_workers: int = 5

    # File uploads
    max_file_size_mb: int = 50

    # Database
    database_path: str = "./data/jobs.db"

    # Auth
    session_expiry_days: int = 30

    # SMTP
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_tls: bool = True

    # CORS
    cors_origins: str = (
        "http://localhost:5173,"
        "http://localhost:3000"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        origins = [
            o.strip()
            for o in self.cors_origins.split(",")
            if o.strip()
        ]

        return origins

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
