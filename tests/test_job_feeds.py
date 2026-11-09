"""Job feeds tests — mocked HTTP, normalization, matcher integration."""

import httpx
import pytest

from cores.opportunity import job_feeds
from cores.opportunity.remote_job_matcher import JobPreferences


def _mock_get(handler):
    def fake_get(url, **kwargs):
        return handler(url)

    return fake_get


def test_fetch_remotive_normalizes(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "jobs": [
            {
                "title": "Dev",
                "company_name": "ACME",
                "url": "https://x",
                "description": "d",
                "publication_date": "2026-01-01",
                "candidate_required_location": "Worldwide",
                "tags": ["Python"],
            }
        ]
    }

    class R:
        def raise_for_status(self):
            pass

        def json(self):
            return payload

    monkeypatch.setattr(job_feeds.httpx, "get", lambda *a, **k: R())
    jobs = job_feeds.fetch_remotive()
    assert len(jobs) == 1
    assert jobs[0]["source"] == "remotive" and jobs[0]["remote"] is True
    assert jobs[0]["candidate_ok"] is True


def test_fetch_remoteok_skips_meta(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = [
        {"legal": "x"},
        {"position": "Eng", "company": "ACME", "id": 1, "url": "u", "description": "d", "date": "2026-01-01", "salary_min": 5000, "tags": ["go"]},
    ]

    class R:
        def raise_for_status(self):
            pass

        def json(self):
            return payload

    monkeypatch.setattr(job_feeds.httpx, "get", lambda *a, **k: R())
    jobs = job_feeds.fetch_remoteok()
    assert len(jobs) == 1 and jobs[0]["title"] == "Eng" and jobs[0]["salary_min"] == 5000


def test_fetch_failure_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*a, **k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(job_feeds.httpx, "get", boom)
    assert job_feeds.fetch_remotive() == []
    assert job_feeds.fetch_arbeitnow() == []
    assert job_feeds.fetch_remoteok() == []


def test_search_ranks_real_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "jobs": [
            {"title": "Soporte es", "company_name": "A", "url": "u1", "description": "", "candidate_required_location": "Worldwide", "tags": []},
            {"title": "Senior US only", "company_name": "B", "url": "u2", "description": "", "candidate_required_location": "US Only", "tags": []},
        ]
    }

    class R:
        def raise_for_status(self):
            pass

        def json(self):
            return payload

    monkeypatch.setattr(job_feeds.httpx, "get", lambda *a, **k: R() if "remotive" in a[0] else (_ for _ in ()).throw(httpx.ConnectError("x")))
    prefs = JobPreferences(payment_methods=())
    ranked = job_feeds.search_remote_jobs(query="soporte", prefs=prefs)
    assert ranked and all("match" in j for j in ranked)


def test_remote_jobs_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from api.routers import opportunities
    from cores.opportunity import job_feeds as jf

    fake = [{"title": "Job", "match": {"score": 90.0, "eligible": True}}]
    monkeypatch.setattr(jf, "search_remote_jobs", lambda **kw: fake)
    app = FastAPI()
    app.include_router(opportunities.router)
    resp = TestClient(app).get("/api/opportunities/remote-jobs/search?q=dev&limit=5")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1 and body["jobs"][0]["title"] == "Job"


def test_job_tracker_pipeline(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    import cores.connections.importer as imp
    from cores.opportunity import job_tracker

    fake_cfg = type("Cfg", (), {"data_dir": tmp_path})()
    monkeypatch.setattr(imp, "get_config", lambda: fake_cfg)

    entry = job_tracker.save_job({"title": "Dev", "url": "https://x", "company": "ACME"}, {"score": 88})
    assert entry["status"] == "saved"
    # idempotent by url
    again = job_tracker.save_job({"title": "Dev", "url": "https://x"}, None)
    assert again["id"] == entry["id"]

    job_tracker.transition(entry["id"], "analyzed")
    job_tracker.transition(entry["id"], "prepared")
    job_tracker.transition(entry["id"], "approved")
    job_tracker.transition(entry["id"], "applied", note="sent manually")
    assert job_tracker.list_jobs(status="applied")[0]["id"] == entry["id"]
    # invalid transition
    import pytest as _p

    with _p.raises(ValueError):
        job_tracker.transition(entry["id"], "saved")


def test_gap_analysis() -> None:
    from cores.opportunity.job_tracker import gap_analysis

    job = {"title": "Dev", "description": "python django", "tags": ["python"], "experience_years_required": 3, "portfolio_required": True}
    out = gap_analysis(job, {"skills": ["python"], "experience_years": 1})
    assert "python" in out["matched_skills"]
    assert any("experience" in g for g in out["gaps"])
    assert any("portfolio" in g for g in out["gaps"])


def test_application_drafter() -> None:
    from cores.opportunity.application_drafter import draft_application

    job = {"title": "Soporte Técnico", "company": "ACME", "url": "u", "experience_years_required": 1, "tags": ["python"]}
    profile = {"name": "Adriel", "headline": "Desarrollador", "skills": ["python", "sql"], "experience_years": 2}
    d = draft_application(job, profile)
    assert d["requires_approval"] is True
    assert "ACME" in d["cover_letter"] and "Adriel" in d["cover_letter"]
    assert "python" in d["profile_summary"]["matched_skills"] or "python" in d["cover_letter"]
    # no invented skills: cover letter only mentions profile skills
    assert "excel" not in d["cover_letter"].lower()


def test_user_profile_store(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    import cores.connections.importer as imp
    from cores.opportunity import user_profile

    fake_cfg = type("Cfg", (), {"data_dir": tmp_path})()
    monkeypatch.setattr(imp, "get_config", lambda: fake_cfg)

    assert user_profile.get_profile() == {}
    out = user_profile.update_profile({"name": "Adriel", "skills": ["python"], "hack": "drop-me"})
    assert out["name"] == "Adriel" and "hack" not in out  # whitelist enforced
    # persists
    assert user_profile.get_profile()["skills"] == ["python"]


def test_profile_endpoints(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import cores.connections.importer as imp
    from api.routers import opportunities

    fake_cfg = type("Cfg", (), {"data_dir": tmp_path})()
    monkeypatch.setattr(imp, "get_config", lambda: fake_cfg)
    app = FastAPI()
    app.include_router(opportunities.router)
    c = TestClient(app)

    r = c.put("/api/opportunities/profile", json={"name": "Adriel", "skills": ["go"], "secret_field": "x"})
    assert r.status_code == 200 and r.json()["profile"]["name"] == "Adriel"
    assert "secret_field" not in r.json()["profile"]
    g = c.get("/api/opportunities/profile")
    assert g.json()["profile"]["skills"] == ["go"]


def test_fetch_jobicy_normalizes(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"jobs": [{"jobTitle": "Dev", "companyName": "ACME", "url": "u", "jobExcerpt": "d", "pubDate": "2026-01-01", "jobGeo": "LATAM, Europe", "jobIndustry": ["Engineering"], "salaryMin": 3000}]}

    class R:
        def raise_for_status(self): pass
        def json(self): return payload

    monkeypatch.setattr(job_feeds.httpx, "get", lambda *a, **k: R())
    jobs = job_feeds.fetch_jobicy()
    assert len(jobs) == 1
    assert jobs[0]["argentina_ok"] is True and jobs[0]["salary_min"] == 3000


def test_fetch_weworkremotely_parses_rss(monkeypatch: pytest.MonkeyPatch) -> None:
    rss = """<?xml version="1.0"?><rss version="2.0"><channel>
    <item><title>ACME Corp: Backend Engineer</title><link>https://x</link><description>desc</description><pubDate>Mon, 01 Jan 2026</pubDate></item>
    </channel></rss>"""

    class R:
        def raise_for_status(self): pass
        text = rss

    monkeypatch.setattr(job_feeds.httpx, "get", lambda *a, **k: R())
    jobs = job_feeds.fetch_weworkremotely()
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Backend Engineer" and jobs[0]["company"] == "ACME Corp"


def test_remote_jobs_import(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import cores.connections.importer as imp
    from api.routers import opportunities

    fake_cfg = type("Cfg", (), {"data_dir": tmp_path})()
    monkeypatch.setattr(imp, "get_config", lambda: fake_cfg)
    app = FastAPI()
    app.include_router(opportunities.router)
    c = TestClient(app)

    r = c.post("/api/opportunities/remote-jobs/import", json={"jobs": [
        {"title": "Soporte AR", "company": "X", "source": "computrabajo", "argentina_ok": True, "remote": True, "language": "es"},
        {"bad": "no title"},
    ]})
    assert r.status_code == 200
    body = r.json()
    assert body["imported"] == 1 and body["skipped"] == 1
    saved = c.get("/api/opportunities/remote-jobs/saved")
    assert saved.json()["count"] == 1
    assert saved.json()["jobs"][0]["job"]["source"] == "computrabajo"
    assert "match" in saved.json()["jobs"][0]
