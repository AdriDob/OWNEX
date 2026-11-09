"""Remote Job Matcher tests — explainable scoring, hard fails, honesty."""

from cores.opportunity.remote_job_matcher import JobPreferences, match_job, rank_jobs


def test_perfect_match() -> None:
    job = {
        "title": "Soporte técnico remoto",
        "language": "es",
        "remote": True,
        "argentina_ok": True,
        "experience_years_required": 0,
        "portfolio_required": False,
        "tech_tests_required": 1,
        "training_included": True,
        "signup_fee": False,
        "salary_min": 700,
        "payment_methods": ["payoneer", "wise"],
        "source": "test",
    }
    prefs = JobPreferences(salary_min_usd=500, payment_methods=("payoneer",))
    r = match_job(job, profile={"experience_years": 1}, prefs=prefs)
    assert r.eligible and r.score > 85
    assert any("Argentina" in x for x in r.reasons_positive)
    assert any("Salary" in x for x in r.reasons_positive)


def test_argentina_hard_fail() -> None:
    job = {"argentina_ok": False, "remote": True, "language": "es", "salary_min": 9999}
    r = match_job(job)
    assert not r.eligible
    assert any("Argentina" in x for x in r.risks)


def test_unknown_never_compatible() -> None:
    r = match_job({"title": "Vacante"})  # everything unknown
    assert "Country eligibility not stated" in r.requirements_missing
    assert "Salary not published" in r.requirements_missing
    assert "Payout method unknown" in r.requirements_missing
    assert r.score < 60  # neutral-ish, not high


def test_experience_gap_and_camera() -> None:
    job = {
        "argentina_ok": True,
        "remote": True,
        "language": "es",
        "experience_years_required": 5,
        "camera_or_mic_required": True,
        "tech_tests_required": 3,
    }
    r = match_job(job, profile={"experience_years": 0}, prefs=JobPreferences(max_tech_tests=1))
    assert any("Experience gap" in x for x in r.risks)
    assert any("Camera" in x for x in r.risks)
    assert any("tech tests" in x.lower() for x in r.risks)


def test_rank_orders_eligible_first() -> None:
    jobs = [
        {"title": "bad", "argentina_ok": False, "remote": True},
        {"title": "good", "argentina_ok": True, "remote": True, "language": "es", "salary_min": 800},
    ]
    ranked = rank_jobs(jobs, prefs=JobPreferences(salary_min_usd=100))
    assert ranked[0]["title"] == "good"
    assert ranked[0]["match"]["score"] > ranked[1]["match"]["score"]
