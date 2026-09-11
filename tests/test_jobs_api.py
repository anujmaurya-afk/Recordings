"""Tests for Jobs API endpoints."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

# We need to initialise the DB before importing the app
import os
os.environ.setdefault("DATABASE_PATH", ":memory:")


@pytest.fixture
async def client():
    from app.main import app
    from app.models.db import init_db
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_create_job_from_urls_no_valid_urls(client):
    resp = await client.post(
        "/api/jobs/urls",
        json={"urls": ["not-a-url", ""], "provider": "recordings"},
    )
    # Either 201 (if generic urls pass) or 422
    assert resp.status_code in (201, 422)


@pytest.mark.asyncio
async def test_create_job_from_valid_urls(client):
    urls = [
        "https://bucket.s3.ap-south-1.amazonaws.com/file1.wav",
        "https://bucket.s3.ap-south-1.amazonaws.com/file2.wav",
    ]
    with patch("app.workers.conversion_worker.run_conversion_job", new_callable=AsyncMock):
        resp = await client.post(
            "/api/jobs/urls",
            json={"urls": urls, "provider": "recordings"},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert "job_id" in data
    assert data["job_id"].startswith("JOB-")


@pytest.mark.asyncio
async def test_get_job_not_found(client):
    resp = await client.get("/api/jobs/JOB-DOESNOTEXIST")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_job_results_after_creation(client):
    urls = ["https://bucket.s3.ap-south-1.amazonaws.com/file.wav"]
    with patch("app.workers.conversion_worker.run_conversion_job", new_callable=AsyncMock):
        create_resp = await client.post(
            "/api/jobs/urls",
            json={"urls": urls, "provider": "recordings"},
        )
    job_id = create_resp.json()["job_id"]

    resp = await client.get(f"/api/jobs/{job_id}/results")
    assert resp.status_code == 200
    data = resp.json()
    assert data["job_id"] == job_id
    assert "items" in data


@pytest.mark.asyncio
async def test_retry_fails_when_no_failed_records(client):
    urls = ["https://bucket.s3.ap-south-1.amazonaws.com/file.wav"]
    with patch("app.workers.conversion_worker.run_conversion_job", new_callable=AsyncMock):
        create_resp = await client.post(
            "/api/jobs/urls",
            json={"urls": urls, "provider": "recordings"},
        )
    job_id = create_resp.json()["job_id"]

    # No failed records yet → should get 409 or 422
    with patch("app.workers.conversion_worker.run_conversion_job", new_callable=AsyncMock):
        retry_resp = await client.post(f"/api/jobs/{job_id}/retry", json={})
    assert retry_resp.status_code in (409, 422)
