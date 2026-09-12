"""
FastAPI application entry point.
"""
from __future__ import annotations

import logging
import logging.config

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models.db import init_db
from app.api import auth, jobs, uploads

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
    description=(
        "Convert S3 recording URLs to presigned (7-day) "
        "or CloudFront (30-day) URLs in bulk."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS ────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,

    # Local development
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],

    # Allow Vercel frontend deployments
    allow_origin_regex=r"^https://.*\.vercel\.app$",

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

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(uploads.router)


@app.get("/", tags=["health"])
async def root():
    return {
        "message": "Recording Converter API is running",
        "status": "ok",
    }


@app.get("/health", tags=["health"])
async def health():
    return {
        "status": "ok",
        "provider": settings.url_provider,
    }
