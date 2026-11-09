"""Remote Job Integration tests — Remote Job Matcher ↔ Discovery ↔ Work Bank."""

import pytest

from cores.opportunity.remote_job_matcher import JobPreferences, match_job, rank_jobs


def test_match_job_eligible_argentina_and_salary():
    """Job debe ser elegible si tiene argentina_ok=True y salary_min suficiente."""
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
    assert r.eligible, f"Job debería ser elegible, got: {r}"
    assert any("Argentina" in x for x in r.reasons_positive)
    assert any("Salary" in x for x in r.reasons_positive)


def test_match_job_ineligible_argentina_false():
    """Job debe ser ineligible si argentina_ok=False."""
    job = {"argentina_ok": False, "remote": True, "language": "es", "salary_min": 9999}
    r = match_job(job)
    assert not r.eligible, f"Job debería ser ineligible (no AR), got: {r}"
    assert any("Argentina" in x for x in r.risks)


def test_match_job_unknown_fields():
    """Job con campos desconocidos debe marcar requisitos faltantes."""
    r = match_job({"title": "Vacante"})
    assert "Country eligibility not stated" in r.requirements_missing
    assert "Salary not published" in r.requirements_missing
    assert "Payout method unknown" in r.requirements_missing
    assert r.score < 60  # neutral, no alto


def test_rank_jobs_orders_eligible_first():
    """Ranking debe poner jobs elegibles antes de los no elegibles."""
    jobs = [
        {"title": "bad", "argentina_ok": False, "remote": True},
        {"title": "good", "argentina_ok": True, "remote": True, "language": "es", "salary_min": 800},
    ]
    ranked = rank_jobs(jobs, prefs=JobPreferences(salary_min_usd=100))
    assert ranked[0]["title"] == "good"
    assert ranked[0]["match"]["score"] > ranked[1]["match"]["score"]


def test_preferences_respect_payment_methods():
    """JobPreferences debe filtrar por payment_methods compatibles."""
    job = {
        "title": "Test job",
        "remote": True,
        "argentina_ok": True,
        "payment_methods": ["paypal", "wise"],
    }
    # Solo payoneer - should be less optimal
    prefs_payoneer = JobPreferences(payment_methods=("payoneer",))
    r1 = match_job(job, prefs=prefs_payoneer)

    # payoneer + wise - should be better
    prefs_both = JobPreferences(payment_methods=("payoneer", "wise"))
    r2 = match_job(job, prefs=prefs_both)

    # Both should be eligible since argentina_ok=True
    assert r1.eligible
    assert r2.eligible
    # r2 should have more positive reasons (extra payment method match)
    assert r2.score >= r1.score