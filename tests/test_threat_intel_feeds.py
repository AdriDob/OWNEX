"""Intel feeds closure (2026-09-12): fixtures only, zero network.

Covers: /hunt/restart contract, registry wiring (incl. ThreatFox),
contract conformity (IntelligenceItem everywhere), arxiv stdlib parse,
OSV query-by-package mapping, OpenAlex abstract reconstruction.
"""

from __future__ import annotations

import asyncio

import httpx


def _authed_client():
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)
    resp = client.post("/api/auth/login", json={"device_id": "pytest-intel-feeds"})
    if resp.status_code == 200 and "data" in resp.json():
        client.headers.update({"Authorization": f"Bearer {resp.json()['data']['token']}"})
    csrf = resp.cookies.get("csrf_token") or resp.cookies.get("csrf")
    if csrf:
        client.headers.update({"X-CSRF-Token": csrf})
    return client


def test_hunt_restart_endpoint() -> None:
    client = _authed_client()
    resp = client.post("/api/hunt/restart", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] in ("started", "already_running")


def test_registry_has_five_feeds() -> None:
    from cores.intelligence import IntelligenceFeed, build_default_intelligence_registry

    registry = build_default_intelligence_registry()
    sources = sorted(f.source.value for f in registry.get_all())
    assert sources == ["arxiv", "epss", "github_advisory", "nvd", "openalex", "osv", "threatfox"]
    for feed in registry.get_all():
        assert isinstance(feed, IntelligenceFeed)


def test_threatfox_without_key_is_degraded_never_fake() -> None:
    import os

    from cores.intelligence.feeds.threatfox_feed import ThreatFoxFeed

    os.environ.pop("THREATFOX_AUTH_KEY", None)
    feed = ThreatFoxFeed()
    health = asyncio.run(feed.health_check())
    assert health["status"] == "degraded"
    assert "Auth-Key" in health["error"]
    assert asyncio.run(feed.fetch_items()) == []


ARXIV_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2401.00001v1</id>
    <title>  Test Paper
Title  </title>
    <summary>Abstract text here.</summary>
    <published>2024-01-15T12:00:00Z</published>
    <link href="http://arxiv.org/abs/2401.00001v1" rel="alternate"/>
  </entry>
  <entry><id>bad</id></entry>
</feed>"""


def test_arxiv_stdlib_parse() -> None:
    from cores.intelligence.feeds.arxiv_feed import ArxivFeed

    entries = ArxivFeed._parse_atom(ARXIV_FIXTURE)
    assert len(entries) == 2
    assert entries[0]["id"] == "http://arxiv.org/abs/2401.00001v1"
    assert entries[0]["link"] == "http://arxiv.org/abs/2401.00001v1"
    assert entries[0]["published"] == "2024-01-15T12:00:00Z"
    assert ArxivFeed._parse_atom("not xml") == []
    assert ArxivFeed()._parse_date("2024-01-15T12:00:00Z") is not None
    assert ArxivFeed()._parse_date("garbage") is None


def test_osv_default_packages_and_mapping() -> None:
    from cores.intelligence.feeds.osv_feed import OSVFeed

    feed = OSVFeed()
    vuln = {
        "id": "PYSEC-2024-1",
        "summary": "s",
        "details": "d",
        "published": "2024-02-01T00:00:00Z",
        "severity": [{"type": "CVSS_V3", "score": "HIGH"}],
    }
    item = feed._to_item(vuln, "requests")
    assert item.external_id == "PYSEC-2024-1"
    assert item.severity == "high"
    assert "requests" in item.tags
    assert (item.url or "").endswith("PYSEC-2024-1")
    assert feed._severity_from_vuln({}) is None
    assert feed._parse_date(None) is None


def test_osv_querybatch_shape() -> None:
    import json

    from cores.intelligence.feeds.osv_feed import OSVFeed

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json={"results": [{"vulns": []}]})

    feed = OSVFeed()
    feed._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    assert asyncio.run(feed.fetch_items(packages=[{"name": "requests", "ecosystem": "PyPI"}])) == []
    assert captured["body"] == {"queries": [{"package": {"name": "requests", "ecosystem": "PyPI"}}]}


def test_github_advisory_returns_items() -> None:
    from cores.intelligence import IntelligenceItem
    from cores.intelligence.feeds.github_advisory_feed import GitHubAdvisoryFeed

    payload = [
        {
            "ghsa_id": "GHSA-xxxx-yyyy-zzzz",
            "summary": "s",
            "description": "d",
            "severity": "high",
            "published_at": "2024-03-01T00:00:00Z",
            "identifiers": [{"type": "CVE", "value": "CVE-2024-1"}],
            "vulnerabilities": [{"package": {"ecosystem": "pip"}}],
        }
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    feed = GitHubAdvisoryFeed()
    feed._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    items = asyncio.run(feed.fetch_items())
    assert len(items) == 1
    assert isinstance(items[0], IntelligenceItem)
    assert items[0].external_id == "github:GHSA-xxxx-yyyy-zzzz"
    assert items[0].severity == "high"


def test_openalex_abstract_reconstruction() -> None:
    from cores.intelligence.feeds.openalex_feed import OpenAlexFeed

    text = OpenAlexFeed._abstract_from_index({"hello": [0], "world": [1], "again": [2]})
    assert text == "hello world again"
    assert OpenAlexFeed._abstract_from_index({}) == ""
    assert OpenAlexFeed._abstract_from_index(None) == ""
    assert OpenAlexFeed._abstract_from_index("garbage") == ""


def test_openalex_mapping_uses_reconstruction() -> None:
    from cores.intelligence import IntelligenceItem
    from cores.intelligence.feeds.openalex_feed import OpenAlexFeed

    payload = {
        "results": [
            {
                "id": "https://openalex.org/W1",
                "title": "T",
                "doi": "https://doi.org/10.1/x",
                "publication_date": "2024-01-01",
                "abstract_inverted_index": {"deep": [0], "learning": [1]},
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    feed = OpenAlexFeed()
    feed._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    items = asyncio.run(feed.fetch_items())
    assert len(items) == 1
    assert isinstance(items[0], IntelligenceItem)
    assert items[0].summary == "deep learning"


def test_epss_mapping_and_url() -> None:
    from cores.intelligence.feeds.epss_feed import EPSSFeed

    feed = EPSSFeed()
    assert feed._severity_from_epss(0.95) == "critical"
    assert feed._severity_from_epss(0.0) == "info"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"data": [{"cve": "CVE-2024-1", "epss": 0.5, "percentile": 0.9, "date": "2024-01-01"}]}
        )

    feed._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    items = asyncio.run(feed.fetch_items())
    assert items[0].external_id == "epss:CVE-2024-1"
    assert "epsss" not in (items[0].url or "")


def test_feed_bridge_maps_cached_items_to_hypotheses() -> None:
    from cores.engine.hypothesis.models import HypothesisSource
    from cores.engine.hypothesis.threat_intel import generate_from_feed_items

    items = [
        {
            "source": "osv",
            "external_id": "CVE-2024-1234",
            "title": "RCE in openssl",
            "summary": "Remote code execution in openssl lib",
            "severity": "critical",
            "tags": [],
        },
        {
            "source": "epss",
            "external_id": "CVE-2024-9999",
            "title": "Unrelated thing",
            "summary": "something else entirely epss:0.9",
            "severity": "high",
            "tags": [],
        },
        {
            "source": "unknown_feed",
            "external_id": "X",
            "title": "openssl bug",
            "summary": "openssl",
            "severity": "high",
            "tags": [],
        },
    ]
    hyps = generate_from_feed_items(items, 1, "t", [{"name": "openssl"}], {"path": "/"})
    assert len(hyps) == 1
    assert hyps[0].source == HypothesisSource.THREAT_INTEL
    assert hyps[0].likelihood == 0.80
    assert "CVE-2024-1234" in hyps[0].id


def test_feed_bridge_empty_without_overlap() -> None:
    from cores.engine.hypothesis.threat_intel import generate_from_feed_items

    items = [
        {"source": "nvd", "external_id": "CVE-1", "title": "foo", "summary": "bar", "severity": "high", "tags": []}
    ]
    assert generate_from_feed_items(items, 1, "t", [{"name": "openssl"}], None) == []
    assert generate_from_feed_items([], 1, "t", [{"name": "openssl"}], None) == []


def test_feeds_health_endpoint() -> None:
    client = _authed_client()
    resp = client.get("/api/intelligence/feeds/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "arxiv" in body["registered"] and "openalex" in body["registered"]
    assert len(body["registered"]) == 7
    assert "cache" in body


def test_intelligence_refresh_never_raises(tmp_path) -> None:
    import os

    from cores.intelligence.tasks import run_intelligence_refresh

    os.environ["OWNEX_DATA_DIR"] = str(tmp_path)
    try:
        summary = run_intelligence_refresh()
    finally:
        del os.environ["OWNEX_DATA_DIR"]
    assert summary["status"] in ("ok", "error")
    assert "feeds" in summary or "error" in summary
