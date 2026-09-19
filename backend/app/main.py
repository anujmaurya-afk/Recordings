"""
FastAPI application entry point.
"""
from __future__ import annotations

import logging
import logging.config
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models.db import init_db
from app.api import jobs, uploads

settings = get_settings()

# ─── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Recording Converter API",
    description="Convert S3 recording URLs to presigned (7-day) or CloudFront (30-day) URLs in bulk.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS ────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Startup ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    await init_db()
    logger.info(
        "Recording Converter API started | provider=%s | max_workers=%d",
        settings.url_provider,
        settings.max_workers,
    )

# ─── Routes ──────────────────────────────────────────────────────────────────

app.include_router(jobs.router)
app.include_router(uploads.router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "provider": settings.url_provider}
