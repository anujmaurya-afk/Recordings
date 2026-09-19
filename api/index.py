"""
Vercel Python serverless entrypoint.

Vercel's Python runtime looks for an ASGI/WSGI `app` (or `handler`) object in
files under /api. This just re-exports the existing FastAPI app so nothing
in backend/ has to change.
"""
import os
import sys

# Make `backend/app` importable as `app`
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app  # noqa: E402
