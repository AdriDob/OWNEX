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
    payload = {"jobs": [{"title": "Dev", "company_name": "ACME", "url": "https://x", "description": "d", "publication_date": "2026-01-01", "candidate_required_location": "Worldwide", "tags": ["Python"]}]}

    class R:
        def raise_for_status(self): pass
        def json(self): return payload

    monkeypatch.setattr(job_feeds.httpx, "get", lambda *a, **k: R())
    jobs = job_feeds.fetch_remotive()
    assert len(jobs) == 1
    assert jobs[0]["source"] == "remotive" and jobs[0]["remote"] is True
    assert jobs[0]["candidate_ok"] is True


def test_fetch_remoteok_skips_meta(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = [{"legal": "x"}, {"position": "Eng", "company": "ACME", "id": 1, "url": "u", "description": "d", "date": "2026-01-01", "salary_min": 5000, "tags": ["go"]}]

    class R:
        def raise_for_status(self): pass
        def json(self): return payload

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
    payload = {"jobs": [
        {"title": "Soporte es", "company_name": "A", "url": "u1", "description": "", "candidate_required_location": "Worldwide", "tags": []},
        {"title": "Senior US only", "company_name": "B", "url": "u2", "description": "", "candidate_required_location": "US Only", "tags": []},
    ]}

    class R:
        def raise_for_status(self): pass
        def json(self): return payload

    monkeypatch.setattr(job_feeds.httpx, "get", lambda *a, **k: R() if "remotive" in a[0] else (_ for _ in ()).throw(httpx.ConnectError("x")))
    prefs = JobPreferences(payment_methods=())
    ranked = job_feeds.search_remote_jobs(query="soporte", prefs=prefs)
    assert ranked and all("match" in j for j in ranked)
