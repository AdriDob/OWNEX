"""Tests for Content Factory API visibility (read-only status + jobs)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.content_factory import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_jobs_lists_five_schedules() -> None:
    resp = client.get("/api/content-factory/jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 6
    ids = {j["job_id"] for j in body["jobs"]}
    assert "content_factory_daily_generate" in ids
    assert "content_factory_health_check" in ids
    assert "content_factory_whop_auto_build" in ids
    for job in body["jobs"]:
        assert job["handler"].startswith("cores.content_factory.scheduler:")
        assert job["schedule"]


def test_status_never_raises_and_reports_mpt() -> None:
    resp = client.get("/api/content-factory/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "mpt" in body
    assert "material_key" in body
    assert isinstance(body["mpt"].get("healthy"), bool)
