"""Tests for Job Search Integration (ai-job-search patterns)."""

import pytest

from cores.direct_work_engine.job_search import (
    FitDimension,
    JobSearchIntegration,
    get_job_search_integration,
)


@pytest.fixture
def integration(tmp_path):
    return JobSearchIntegration(data_dir=tmp_path)


SAMPLE_OPP = {
    "id": "job-1",
    "title": "Senior Python Developer",
    "platform": "linkedin",
    "skills": ["python", "fastapi", "docker", "aws"],
    "experience_level": "senior",
    "payment": 5000,
    "remote": True,
    "country": "",
    "category": "backend",
}

SAMPLE_PROFILE = {
    "name": "Adriel",
    "skills": ["Python", "Go", "TypeScript", "Docker", "AWS", "Linux", "Burp Suite"],
    "experience_level": "senior",
    "availability_hours": 40.0,
}


class TestFitEvaluation:
    def test_good_match_scores_high(self, integration):
        result = integration.evaluate_fit(SAMPLE_OPP, SAMPLE_PROFILE)
        assert result.overall_fit_score >= 70
        assert result.recommendation == "APPLY"
        assert any("skill" in s.lower() for s in result.strengths)

    def test_poor_skill_match_scores_low(self, integration):
        opp = {**SAMPLE_OPP, "skills": ["kubernetes", "rust", "solidity"]}
        result = integration.evaluate_fit(opp, SAMPLE_PROFILE)
        assert result.dimensions[FitDimension.SKILLS_MATCH.value] < 40
        assert len(result.gaps) > 0

    def test_non_remote_penalized(self, integration):
        opp = {**SAMPLE_OPP, "remote": False, "country": "USA"}
        result = integration.evaluate_fit(opp, SAMPLE_PROFILE)
        assert result.dimensions[FitDimension.LOCATION_REMOTE.value] < 50

    def test_remote_argentina_scores_full(self, integration):
        opp = {**SAMPLE_OPP, "remote": True}
        result = integration.evaluate_fit(opp, SAMPLE_PROFILE)
        assert result.dimensions[FitDimension.LOCATION_REMOTE.value] == 100.0

    def test_dimensions_sum_to_weighted_score(self, integration):
        result = integration.evaluate_fit(SAMPLE_OPP, SAMPLE_PROFILE)
        expected = sum(
            result.dimensions[d.value] * w
            for d, w in [
                (FitDimension.SKILLS_MATCH, 0.30),
                (FitDimension.EXPERIENCE_LEVEL, 0.20),
                (FitDimension.COMPENSATION, 0.25),
                (FitDimension.LOCATION_REMOTE, 0.15),
                (FitDimension.CAREER_GROWTH, 0.10),
            ]
        )
        assert abs(result.overall_fit_score - expected) < 1.0


class TestApplicationTracking:
    def test_track_and_retrieve(self, integration):
        eval_result = integration.evaluate_fit(SAMPLE_OPP, SAMPLE_PROFILE)
        integration.track_application(eval_result, url="https://example.com/job")

        pipeline = integration.get_pipeline()
        assert "applied" in pipeline
        assert pipeline["applied"][0]["title"] == "Senior Python Developer"

    def test_update_status(self, integration):
        eval_result = integration.evaluate_fit(SAMPLE_OPP, SAMPLE_PROFILE)
        integration.track_application(eval_result)

        ok = integration.update_status("job-1", "interviewing")
        assert ok is True
        stats = integration.get_stats()
        assert stats["by_status"].get("interviewing", 0) >= 1

    def test_update_nonexistent_returns_false(self, integration):
        assert integration.update_status("nonexistent", "rejected") is False

    def test_empty_pipeline(self, integration):
        assert integration.get_pipeline() == {}
        assert integration.get_stats()["total"] == 0

    def test_stats_shape(self, integration):
        eval_result = integration.evaluate_fit(SAMPLE_OPP, SAMPLE_PROFILE)
        integration.track_application(eval_result)
        stats = integration.get_stats()
        assert "total" in stats
        assert "by_status" in stats
        assert "interview_rate" in stats
        assert stats["total"] >= 1


class TestSingleton:
    def test_get_job_search_integration_singleton(self):
        assert get_job_search_integration() is get_job_search_integration()
