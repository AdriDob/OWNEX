"""Tests for Intelligent Recon Router — fingerprint, strategies, router."""

from __future__ import annotations

from unittest.mock import patch

from core.recon.fingerprint import Fingerprinter, FingerprintResult, TechnologyDetected
from core.recon.router import ReconRouter, RoutedReconResult
from core.recon.strategies import (
    ReconStrategy,
    get_strategy,
    list_strategies,
    select_strategies,
)

# ── TechnologyDetected ────────────────────────────────────────────


class TestTechnologyDetected:
    def test_create(self):
        t = TechnologyDetected(name="react", category="spa", confidence=0.85, evidence=["html:__NEXT_DATA__"])
        assert t.name == "react"
        assert t.category == "spa"
        assert t.confidence == 0.85


# ── FingerprintResult ─────────────────────────────────────────────


class TestFingerprintResult:
    def test_empty_primary(self):
        r = FingerprintResult()
        assert r.primary_tech == "unknown"
        assert r.tech_summary == "unknown"

    def test_primary_tech(self):
        r = FingerprintResult(
            technologies=[
                TechnologyDetected(name="wordpress", confidence=0.5),
                TechnologyDetected(name="react", confidence=0.9),
            ]
        )
        assert r.primary_tech == "react"

    def test_tech_summary_ordering(self):
        r = FingerprintResult(
            technologies=[
                TechnologyDetected(name="a", confidence=0.3),
                TechnologyDetected(name="b", confidence=0.9),
            ]
        )
        parts = r.tech_summary.split(", ")
        assert parts[0].startswith("b")

    def test_has_tech(self):
        r = FingerprintResult(
            technologies=[
                TechnologyDetected(name="react", confidence=0.8),
            ]
        )
        assert r.has_tech("react")
        assert not r.has_tech("vue")

    def test_get_confidence(self):
        r = FingerprintResult(
            technologies=[
                TechnologyDetected(name="laravel", confidence=0.75),
            ]
        )
        assert r.get_confidence("laravel") == 0.75
        assert r.get_confidence("django") == 0.0


# ── Fingerprinter (unit, mocked) ──────────────────────────────────


class TestFingerprinter:
    def test_fingerprint_empty(self):
        fp = Fingerprinter()
        with patch.object(fp, "_match_technologies", return_value=[]):
            result = fp.fingerprint("example.com", paths=["/"])
            assert result.primary_tech == "unknown"
            assert "/" in result.paths_checked

    def test_fingerprint_with_tech(self):
        fp = Fingerprinter()
        fake_tech = [TechnologyDetected(name="react", confidence=0.7)]
        with patch.object(fp, "_match_technologies", return_value=fake_tech):
            result = fp.fingerprint("example.com", paths=["/"])
            assert result.primary_tech == "react"
            assert len(result.technologies) == 1

    def test_fingerprint_below_threshold(self):
        fp = Fingerprinter()
        fake_tech = [TechnologyDetected(name="react", confidence=0.1)]
        with patch.object(fp, "_match_technologies", return_value=fake_tech):
            result = fp.fingerprint("example.com", paths=["/"])
            assert result.primary_tech == "unknown"
            assert len(result.technologies) == 0

    def test_match_technologies_no_match(self):
        fp = Fingerprinter()
        result = fp._match_technologies("<html></html>", {}, {}, ["/"])
        assert result == []

    def test_match_html_pattern(self):
        fp = Fingerprinter()
        result = fp._match_technologies('<html id="__next">next app</html>', {}, {}, ["/"])
        names = [t.name for t in result]
        assert "react" in names

    def test_match_header_pattern(self):
        fp = Fingerprinter()
        result = fp._match_technologies(
            "<html></html>",
            {"X-Powered-By": "Express"},
            {},
            ["/"],
        )
        names = [t.name for t in result]
        assert "express" in names

    def test_match_cookie_pattern(self):
        fp = Fingerprinter()
        result = fp._match_technologies(
            "<html></html>",
            {},
            {"laravel_session": "abc123"},
            ["/"],
        )
        names = [t.name for t in result]
        assert "laravel" in names


# ── ReconStrategy ──────────────────────────────────────────────────


class TestReconStrategy:
    def test_create(self):
        s = ReconStrategy(name="test", description="test strategy", tech_targets=["react"])
        assert s.name == "test"
        assert s.priority == 5

    def test_matches(self):
        s = ReconStrategy(name="react_spa", description="", tech_targets=["react"])
        fp = FingerprintResult(
            technologies=[
                TechnologyDetected(name="react", confidence=0.7),
            ]
        )
        assert s.matches(fp)
        assert not s.matches(FingerprintResult())

    def test_matches_below_threshold(self):
        s = ReconStrategy(name="react_spa", description="", tech_targets=["react"])
        fp = FingerprintResult(
            technologies=[
                TechnologyDetected(name="react", confidence=0.2),
            ]
        )
        assert not s.matches(fp)


# ── Strategy registry ──────────────────────────────────────────────


class TestStrategyRegistry:
    def test_list_strategies(self):
        strategies = list_strategies()
        assert len(strategies) >= 9
        names = [s.name for s in strategies]
        assert "react_spa" in names
        assert "graphql" in names
        assert "laravel" in names
        assert "wordpress" in names
        assert "spring" in names

    def test_get_strategy(self):
        s = get_strategy("graphql")
        assert s is not None
        assert s.name == "graphql"

    def test_get_strategy_nonexistent(self):
        assert get_strategy("nonexistent") is None

    def test_select_strategies(self):
        fp = FingerprintResult(
            technologies=[
                TechnologyDetected(name="react", confidence=0.7),
                TechnologyDetected(name="graphql", confidence=0.3),
            ]
        )
        selected = select_strategies(fp)
        names = [s.name for s in selected]
        assert "react_spa" in names
        assert "graphql" in names

    def test_select_strategies_empty(self):
        selected = select_strategies(FingerprintResult())
        assert selected == []

    def test_select_strategies_priority_order(self):
        fp = FingerprintResult(
            technologies=[
                TechnologyDetected(name="react", confidence=0.8),
                TechnologyDetected(name="api", confidence=0.4),
            ]
        )
        selected = select_strategies(fp)
        priorities = [s.priority for s in selected]
        assert priorities == sorted(priorities, reverse=True)

    def test_graphql_strategy_probes(self):
        s = get_strategy("graphql")
        assert s is not None
        assert len(s.probes) >= 5
        paths = [p.get("path") for p in s.probes]
        assert "/graphql" in paths
        assert "/graphiql" in paths

    def test_spring_strategy_probes(self):
        s = get_strategy("spring")
        assert s is not None
        paths = [p.get("path") for p in s.probes]
        assert "/actuator" in paths
        assert "/actuator/env" in paths
        assert "/actuator/heapdump" in paths

    def test_wordpress_strategy_probes(self):
        s = get_strategy("wordpress")
        assert s is not None
        paths = [p.get("path") for p in s.probes]
        assert "/wp-json/wp/v2/users" in paths
        assert "/xmlrpc.php" in paths

    def test_fastapi_strategy_probes(self):
        s = get_strategy("fastapi")
        assert s is not None
        paths = [p.get("path") for p in s.probes]
        assert "/openapi.json" in paths
        assert "/docs" in paths


# ── RoutedReconResult ──────────────────────────────────────────────


class TestRoutedReconResult:
    def test_create(self):
        r = RoutedReconResult(domain="example.com")
        assert r.domain == "example.com"
        assert r.endpoints_found == []
        assert r.strategies_used == []

    def test_to_json(self):
        r = RoutedReconResult(
            domain="example.com",
            strategies_used=["react_spa"],
            endpoints_found=[{"url": "https://example.com/api", "status": 200}],
        )
        j = r.to_json()
        assert "example.com" in j
        assert "react_spa" in j


# ── Router (unit, mocked) ────────────────────────────────────────


class TestReconRouter:
    def test_route_no_match(self):
        router = ReconRouter()
        with patch.object(router._fingerprinter, "fingerprint", return_value=FingerprintResult()):
            result = router.route("example.com")
            assert result.tech_summary == "unknown"
            assert result.strategies_used == []
            assert result.endpoints_found == []

    def test_route_with_match_no_endpoints(self):
        router = ReconRouter()
        fp = FingerprintResult(
            technologies=[
                TechnologyDetected(name="react", confidence=0.8),
            ]
        )
        with patch.object(router._fingerprinter, "fingerprint", return_value=fp):
            with patch("httpx.request", side_effect=Exception("timeout")):
                result = router.route("example.com")
                assert "react_spa" in result.strategies_used
                assert result.endpoints_found == []

    def test_endpoint_score_200(self):
        from core.recon.router import _endpoint_score

        assert _endpoint_score(200) == 0.9

    def test_endpoint_score_404(self):
        from core.recon.router import _endpoint_score

        assert _endpoint_score(404) == 0.1

    def test_endpoint_score_unknown(self):
        from core.recon.router import _endpoint_score

        assert _endpoint_score(503) == 0.5

    def test_detect_auth_smells_login(self):
        from core.recon.router import _detect_auth_smells

        smells = _detect_auth_smells({"body_preview": "please login first", "status": 200, "content_type": "text/html"})
        assert "login_page" in smells

    def test_detect_auth_smells_401(self):
        from core.recon.router import _detect_auth_smells

        smells = _detect_auth_smells({"body_preview": "", "status": 401, "content_type": "text/html"})
        assert "requires_authentication" in smells

    def test_detect_auth_smells_403(self):
        from core.recon.router import _detect_auth_smells

        smells = _detect_auth_smells({"body_preview": "", "status": 403, "content_type": "text/html"})
        assert "forbidden" in smells

    def test_detect_auth_smells_graphql(self):
        from core.recon.router import _detect_auth_smells

        smells = _detect_auth_smells({"body_preview": "", "status": 200, "content_type": "application/graphql+json"})
        assert "graphql_endpoint" in smells
