"""Tests for the Career Engine API router (analyze / roadmap / daily-training / interview / gaps)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.career import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def profile_dict(**overrides) -> dict:
    data = {
        "name": "Adriel",
        "country": "Argentina",
        "languages": ["es", "en"],
        "skills": ["python", "web", "http", "recon"],
        "remote_only": True,
    }
    data.update(overrides)
    return data


class TestCareerApi:
    def test_status_endpoint(self) -> None:
        response = client.get("/career/status")
        assert response.status_code == 200
        body = response.json()
        assert body["enabled"] is True
        assert body["categories_count"] > 0

    def test_analyze_returns_summary(self) -> None:
        response = client.post("/career/analyze", json={"profile": profile_dict()})
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Adriel"
        assert body["skills_count"] == 4
        assert body["skill_gaps"] >= 0
        assert "high_priority_gaps" in body
        assert "top_categories" in body

    def test_roadmap_ordered_high_priority_first(self) -> None:
        # profile with NO skills; categories share 'web'/'http'/'python' so
        # those gaps appear in 2+ categories => marked high priority.
        response = client.post(
            "/career/roadmap",
            json={
                "profile": {"name": "New", "skills": []},
                "categories": ["bug_bounty", "security_research", "backend"],
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total_gaps"] > 0
        assert body["items"][0]["priority"] == "high"

    def test_daily_training_returns_plan(self) -> None:
        response = client.post("/career/daily-training", json={"profile": profile_dict()})
        assert response.status_code == 200
        body = response.json()
        assert "focus_skills" in body
        assert "drills" in body
        assert "interview_questions" in body
        assert body["date"]

    def test_interview_returns_questions(self) -> None:
        response = client.post("/career/interview", json={"category": "bug_bounty"})
        assert response.status_code == 200
        assert len(response.json()["questions"]) > 0

    def test_interview_invalid_category_422(self) -> None:
        response = client.post("/career/interview", json={"category": "nonexistent"})
        assert response.status_code == 422

    def test_gaps_returns_top_level_detail(self) -> None:
        response = client.post(
            "/career/gaps",
            json={"profile": profile_dict(), "categories": ["bug_bounty"]},
        )
        assert response.status_code == 200
        body = response.json()
        assert "total_gaps" in body
        assert "high_priority" in body
        assert "gaps" in body
