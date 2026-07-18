"""Tests for HTTP Probe Module — probes, analyzer, engine, evidence generation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.capabilities.registry import get_capability_registry, reset_capability_registry
from core.http_probe.analyzer import Analyzer
from core.http_probe.engine import HTTPClient, ProbeEngine, ProbeRequest
from core.http_probe.probes import (
    AuthBypassProbe,
    HttpResponse,
    IDORProbe,
    ProbeResult,
    SQLiProbe,
    SSRFProbe,
    XSSProbe,
)
from core.http_probe.templates import ProbeTemplates

# ── Helpers ───────────────────────────────────────────────────


def _ok_response(body: str = "OK", status: int = 200, elapsed: float = 50.0) -> HttpResponse:
    return HttpResponse(status_code=status, body=body, elapsed_ms=elapsed, url="http://test.local/api")


def _error_response(msg: str = "timeout") -> HttpResponse:
    return HttpResponse(status_code=0, error=msg, url="http://test.local/api")


def _make_probe_result(
    status: str = "unknown",
    confidence: float = 0.0,
    name: str = "test_probe",
    vuln: str = "xss",
    payload: dict | None = None,
    baseline_body: str = "hello",
    probe_body: str = "hello <script>alert(1)</script>",
) -> ProbeResult:
    return ProbeResult(
        hypothesis_id="hyp-test-001",
        vulnerability_type=vuln,
        endpoint="http://test.local/api",
        method="GET",
        status=status,
        confidence=confidence,
        probe_name=name,
        payload_used=payload or {},
        baseline_response=_ok_response(baseline_body),
        probe_response=_ok_response(probe_body),
    )


# ── Template Tests ────────────────────────────────────────────


class TestProbeTemplates:
    def test_all_types_returns_five(self) -> None:
        types = ProbeTemplates.all_types()
        assert len(types) == 5
        assert "idor" in types
        assert "ssrf" in types
        assert "xss" in types
        assert "sqli" in types
        assert "auth_bypass" in types

    def test_idor_templates(self) -> None:
        templates = ProbeTemplates.idor_templates()
        assert len(templates) >= 2
        assert all(t.vulnerability_type == "idor" for t in templates)

    def test_ssrf_templates(self) -> None:
        templates = ProbeTemplates.ssrf_templates()
        assert len(templates) >= 2
        assert all(t.vulnerability_type == "ssrf" for t in templates)

    def test_xss_templates(self) -> None:
        templates = ProbeTemplates.xss_templates()
        assert len(templates) >= 2
        assert all(t.vulnerability_type == "xss" for t in templates)

    def test_sqli_templates(self) -> None:
        templates = ProbeTemplates.sqli_templates()
        assert len(templates) >= 2
        assert all(t.vulnerability_type == "sqli" for t in templates)

    def test_auth_bypass_templates(self) -> None:
        templates = ProbeTemplates.auth_bypass_templates()
        assert len(templates) >= 3
        assert all(t.vulnerability_type == "auth_bypass" for t in templates)

    def test_for_type(self) -> None:
        assert ProbeTemplates.for_type("idor") == ProbeTemplates.idor_templates()
        assert ProbeTemplates.for_type("nonexistent") == []

    def test_deep_copy(self) -> None:
        orig = ProbeTemplates.idor_templates()[0]
        copy = ProbeTemplates.deep_copy(orig)
        copy.name = "modified"
        assert orig.name != "modified"


# ── HttpResponse Tests ────────────────────────────────────────


class TestHttpResponse:
    def test_is_error(self) -> None:
        assert _error_response().is_error is True
        assert _ok_response().is_error is False

    def test_content_type(self) -> None:
        r = HttpResponse(status_code=200, headers={"Content-Type": "application/json"})
        assert r.content_type == "application/json"

    def test_body_lower(self) -> None:
        r = HttpResponse(status_code=200, body="Hello World")
        assert r.body_lower == "hello world"


# ── IDOR Probe Tests ─────────────────────────────────────────


class TestIDORProbe:
    def test_build_probe_requests_numeric_path(self) -> None:
        probe = IDORProbe()
        requests = probe.build_probe_requests("http://test.local/api/users/123/profile", "GET")
        assert len(requests) >= 1
        assert any("124" in r["url"] for r in requests)

    def test_build_probe_requests_numeric_param(self) -> None:
        probe = IDORProbe()
        requests = probe.build_probe_requests("http://test.local/api/users", "GET", params={"id": "42"})
        assert len(requests) >= 1
        assert any(r["payload"].get("id") == "43" for r in requests)

    def test_analyze_responses_same_content(self) -> None:
        probe = IDORProbe()
        baseline = _ok_response("user data")
        probe_resp = _ok_response("user data")
        status, conf, evidence, indicators = probe.analyze_responses(baseline, [probe_resp], {"id": "43"})
        assert status == "rejected"
        assert conf == 0.0

    def test_analyze_responses_different_content(self) -> None:
        probe = IDORProbe()
        baseline = _ok_response("user A data")
        probe_resp = _ok_response("user B data - different content here")
        status, conf, evidence, indicators = probe.analyze_responses(baseline, [probe_resp], {"id": "43"})
        assert status in ("confirmed", "unknown")
        assert conf > 0.0

    def test_analyze_responses_auth_enforced(self) -> None:
        probe = IDORProbe()
        baseline = _ok_response()
        probe_resp = HttpResponse(status_code=403, body="Forbidden")
        status, conf, evidence, indicators = probe.analyze_responses(baseline, [probe_resp], {})
        assert status == "rejected"


# ── SSRF Probe Tests ─────────────────────────────────────────


class TestSSRFProbe:
    def test_build_probe_requests_injects_internal_hosts(self) -> None:
        probe = SSRFProbe()
        requests = probe.build_probe_requests(
            "http://test.local/api/fetch", "GET", params={"url": "http://example.com"}
        )
        assert len(requests) >= 2
        payloads = [r["payload"] for r in requests]
        assert any("127.0.0.1" in str(p) for p in payloads)
        assert any("169.254.169.254" in str(p) for p in payloads)

    def test_analyze_responses_internal_leakage(self) -> None:
        probe = SSRFProbe()
        baseline = _ok_response("normal page")
        probe_resp = _ok_response("root:x:0:0:root on 127.0.0.1:/root:/bin/bash")
        status, conf, evidence, indicators = probe.analyze_responses(
            baseline, [probe_resp], {"url": "http://127.0.0.1"}
        )
        assert status == "confirmed"
        assert conf >= 0.5
        assert any("internal" in i.lower() for i in indicators)

    def test_analyze_responses_metadata_leakage(self) -> None:
        probe = SSRFProbe()
        baseline = _ok_response("normal")
        probe_resp = _ok_response("ami-id: ami-12345678\ninstance-id: i-abc123")
        status, conf, evidence, indicators = probe.analyze_responses(
            baseline, [probe_resp], {"url": "http://169.254.169.254"}
        )
        assert status == "confirmed"
        assert conf >= 0.5

    def test_analyze_responses_no_leakage(self) -> None:
        probe = SSRFProbe()
        baseline = _ok_response("normal page")
        probe_resp = _ok_response("normal page")
        status, conf, evidence, indicators = probe.analyze_responses(baseline, [probe_resp], {})
        assert status == "rejected"


# ── XSS Probe Tests ──────────────────────────────────────────


class TestXSSProbe:
    def test_build_probe_requests_injects_script(self) -> None:
        probe = XSSProbe()
        requests = probe.build_probe_requests("http://test.local/search", "GET", params={"q": "test"})
        assert len(requests) >= 3
        payloads = [r["payload"] for r in requests]
        assert any("<script>" in str(p) for p in payloads)

    def test_analyze_responses_script_reflected(self) -> None:
        probe = XSSProbe()
        baseline = _ok_response("<html>search results</html>")
        probe_resp = _ok_response("<html>results for <script>xssprobe12345</script></html>")
        status, conf, evidence, indicators = probe.analyze_responses(
            baseline, [probe_resp], {"q": "<script>xssprobe12345</script>"}
        )
        assert status == "confirmed"
        assert conf >= 0.5

    def test_analyze_responses_canary_reflected(self) -> None:
        probe = XSSProbe()
        baseline = _ok_response("no canary here")
        probe_resp = _ok_response("found: xssprobe12345 in results")
        status, conf, evidence, indicators = probe.analyze_responses(baseline, [probe_resp], {"q": "xssprobe12345"})
        assert status in ("confirmed", "unknown")
        assert conf > 0.0

    def test_analyze_responses_no_reflection(self) -> None:
        probe = XSSProbe()
        baseline = _ok_response("normal page")
        probe_resp = _ok_response("normal page")
        status, conf, evidence, indicators = probe.analyze_responses(baseline, [probe_resp], {"q": "xssprobe12345"})
        assert status == "rejected"


# ── SQLi Probe Tests ─────────────────────────────────────────


class TestSQLiProbe:
    def test_build_probe_requests_injects_sql(self) -> None:
        probe = SQLiProbe()
        requests = probe.build_probe_requests("http://test.local/api/items", "GET", params={"id": "1"})
        assert len(requests) >= 3
        payloads = [r["payload"] for r in requests]
        assert any("OR" in str(p) for p in payloads)

    def test_analyze_responses_sql_error(self) -> None:
        probe = SQLiProbe()
        baseline = _ok_response("normal items")
        probe_resp = _ok_response("You have an error in your SQL syntax near '1'")
        status, conf, evidence, indicators = probe.analyze_responses(baseline, [probe_resp], {"id": "' OR 1=1--"})
        assert status == "confirmed"
        assert conf >= 0.5

    def test_analyze_responses_server_error(self) -> None:
        probe = SQLiProbe()
        baseline = _ok_response("normal items")
        probe_resp = HttpResponse(status_code=500, body="Internal Server Error")
        status, conf, evidence, indicators = probe.analyze_responses(baseline, [probe_resp], {"id": "' OR 1=1--"})
        assert status in ("confirmed", "unknown")
        assert conf > 0.0

    def test_analyze_responses_no_sqli(self) -> None:
        probe = SQLiProbe()
        baseline = _ok_response("normal items")
        probe_resp = _ok_response("normal items")
        status, conf, evidence, indicators = probe.analyze_responses(baseline, [probe_resp], {"id": "1"})
        assert status == "rejected"


# ── Auth Bypass Probe Tests ──────────────────────────────────


class TestAuthBypassProbe:
    def test_build_probe_requests_removes_auth(self) -> None:
        probe = AuthBypassProbe()
        requests = probe.build_probe_requests(
            "http://test.local/admin",
            "GET",
            headers={"Authorization": "Bearer real-token", "X-Api-Key": "key123"},
        )
        assert len(requests) >= 3
        names = [r["name"] for r in requests]
        assert "auth_no_token" in names
        assert "auth_null_token" in names

    def test_analyze_responses_auth_bypassed(self) -> None:
        probe = AuthBypassProbe()
        baseline = HttpResponse(status_code=403, body="Forbidden")
        probe_resp = _ok_response("admin panel content")
        status, conf, evidence, indicators = probe.analyze_responses(baseline, [probe_resp], {})
        assert status == "confirmed"
        assert conf >= 0.5
        assert any("bypass" in i.lower() for i in indicators)

    def test_analyze_responses_auth_enforced(self) -> None:
        probe = AuthBypassProbe()
        baseline = _ok_response("normal user page")
        probe_resp = HttpResponse(status_code=401, body="Unauthorized")
        status, conf, evidence, indicators = probe.analyze_responses(baseline, [probe_resp], {})
        assert status == "rejected"


# ── Analyzer Tests ────────────────────────────────────────────


class TestAnalyzer:
    def test_analyze_empty_results(self) -> None:
        analyzer = Analyzer()
        result = analyzer.analyze([])
        assert result.status == "unknown"
        assert result.confidence == 0.0

    def test_analyze_confirmed_probes(self) -> None:
        analyzer = Analyzer()
        pr = _make_probe_result(status="confirmed", confidence=0.8)
        result = analyzer.analyze([pr], hypothesis_id="hyp-001", vulnerability_type="xss")
        assert result.status == "confirmed"
        assert result.confidence == 0.8
        assert result.vulnerability_type == "xss"

    def test_analyze_rejected_probes(self) -> None:
        analyzer = Analyzer()
        pr = _make_probe_result(status="rejected", confidence=0.0)
        result = analyzer.analyze([pr])
        assert result.status == "rejected"
        assert result.confidence == 0.0

    def test_analyze_mixed_results(self) -> None:
        analyzer = Analyzer()
        pr1 = _make_probe_result(status="confirmed", confidence=0.7, name="probe1")
        pr2 = _make_probe_result(status="rejected", confidence=0.0, name="probe2", probe_body="nothing interesting")
        result = analyzer.analyze([pr1, pr2])
        assert result.status == "confirmed"
        assert result.confidence >= 0.5

    def test_analyze_produces_poc_data(self) -> None:
        analyzer = Analyzer()
        pr = _make_probe_result(status="confirmed", confidence=0.7)
        result = analyzer.analyze([pr], vulnerability_type="ssrf")
        assert "poc_data" in result.to_dict()
        assert result.poc_data.get("vulnerability_type") == "ssrf"
        assert "cwe" in result.poc_data

    def test_cwe_mapping(self) -> None:
        analyzer = Analyzer()
        pr = _make_probe_result(status="confirmed", confidence=0.8, vuln="sqli")
        result = analyzer.analyze([pr], vulnerability_type="sqli")
        assert result.cwe_id == "CWE-89"
        assert result.cvss_estimate == 9.8

    def test_extract_evidence_from_pair(self) -> None:
        analyzer = Analyzer()
        baseline = HttpResponse(status_code=200, body="normal")
        probe = HttpResponse(status_code=500, body="SQL syntax error near '1'")
        items = analyzer.extract_evidence_from_pair(baseline, probe, {"id": "test"})
        assert len(items) >= 1
        types = [i["type"] for i in items]
        assert "sql_error" in types

    def test_deduplication(self) -> None:
        analyzer = Analyzer()
        pr1 = _make_probe_result(status="confirmed", confidence=0.7, name="p1")
        pr2 = _make_probe_result(
            status="confirmed",
            confidence=0.7,
            name="p2",
            probe_body=pr1.probe_response.body if pr1.probe_response else "",
        )
        result = analyzer.analyze([pr1, pr2])
        # Indicators should be deduplicated
        assert len(result.indicators) == len(set(result.indicators))

    def test_to_dict(self) -> None:
        analyzer = Analyzer()
        pr = _make_probe_result(status="confirmed", confidence=0.7)
        result = analyzer.analyze([pr])
        d = result.to_dict()
        assert "hypothesis_id" in d
        assert "confidence" in d
        assert "evidence_items" in d
        assert "poc_data" in d


# ── ProbeResult Tests ────────────────────────────────────────


class TestProbeResult:
    def test_to_dict(self) -> None:
        pr = _make_probe_result(status="confirmed", confidence=0.75)
        d = pr.to_dict()
        assert d["status"] == "confirmed"
        assert d["confidence"] == 0.75
        assert "evidence_snippets" in d

    def test_is_error(self) -> None:
        pr = ProbeResult(error="connection refused")
        assert pr.error == "connection refused"


# ── Engine Tests ──────────────────────────────────────────────


class TestProbeEngine:
    @pytest.fixture(autouse=True)
    def _reset_registry(self) -> None:
        reset_capability_registry()
        yield
        reset_capability_registry()

    def _mock_engine(self) -> tuple[ProbeEngine, MagicMock]:
        mock_client = MagicMock(spec=HTTPClient)
        return ProbeEngine(http_client=mock_client), mock_client

    def test_capabilities_registered(self) -> None:
        engine, _ = self._mock_engine()
        reg = get_capability_registry()
        assert reg.has_capability("probe_idor")
        assert reg.has_capability("probe_ssrf")
        assert reg.has_capability("probe_xss")
        assert reg.has_capability("probe_sqli")
        assert reg.has_capability("probe_auth_bypass")

    def test_supported_types(self) -> None:
        engine, _ = self._mock_engine()
        types = engine.supported_types()
        assert "idor" in types
        assert "ssrf" in types
        assert "xss" in types
        assert "sqli" in types
        assert "auth_bypass" in types

    def test_probe_unknown_type(self) -> None:
        engine, _ = self._mock_engine()
        result = engine.probe(
            hypothesis_id="hyp-001",
            endpoint="http://test.local/api",
            method="GET",
            vulnerability_type="nonexistent",
        )
        assert result.status == "unknown"
        assert "Unsupported" in str(result.indicators)

    @patch.object(HTTPClient, "send")
    def test_probe_idor_rejected(self, mock_send: MagicMock) -> None:
        engine = ProbeEngine()
        baseline = _ok_response("user A data here")
        mock_send.return_value = baseline
        result = engine.probe(
            hypothesis_id="hyp-idor-001",
            endpoint="http://test.local/api/users/123",
            method="GET",
            vulnerability_type="idor",
            params={"id": "123"},
        )
        assert result.status in ("rejected", "unknown")

    @patch.object(HTTPClient, "send")
    def test_probe_xss_confirmed(self, mock_send: MagicMock) -> None:
        engine = ProbeEngine()
        baseline = _ok_response("<html>search page</html>")

        def side_effect(req: ProbeRequest) -> HttpResponse:
            if "xssprobe12345" in req.params.get("q", ""):
                return _ok_response("<html>results for <script>xssprobe12345</script></html>")
            return baseline

        mock_send.side_effect = side_effect
        result = engine.probe(
            hypothesis_id="hyp-xss-001",
            endpoint="http://test.local/search",
            method="GET",
            vulnerability_type="xss",
            params={"q": "test"},
        )
        assert result.status == "confirmed"
        assert result.confidence > 0.0

    @patch.object(HTTPClient, "send")
    def test_probe_sqli_confirmed(self, mock_send: MagicMock) -> None:
        engine = ProbeEngine()
        baseline = _ok_response("normal data")

        def side_effect(req: ProbeRequest) -> HttpResponse:
            payload_val = str(req.params.values())
            if "OR" in payload_val or "1=1" in payload_val:
                return _ok_response("You have an error in your SQL syntax")
            return baseline

        mock_send.side_effect = side_effect
        result = engine.probe(
            hypothesis_id="hyp-sqli-001",
            endpoint="http://test.local/api/items",
            method="GET",
            vulnerability_type="sqli",
            params={"id": "1"},
        )
        assert result.status == "confirmed"

    def test_probe_handles_connection_error(self) -> None:
        engine, mock_client = self._mock_engine()
        mock_client.send.return_value = _error_response("Connection refused")
        result = engine.probe(
            hypothesis_id="hyp-err-001",
            endpoint="http://test.local/api",
            method="GET",
            vulnerability_type="xss",
            params={"q": "test"},
        )
        assert result.status in ("unknown", "rejected")
        assert any("error" in i.lower() or "fail" in i.lower() for i in result.indicators)

    def test_probe_batch(self) -> None:
        engine, mock_client = self._mock_engine()
        mock_client.send.return_value = _ok_response("same content")
        results = engine.probe_batch(
            [
                {
                    "hypothesis_id": "hyp-1",
                    "endpoint": "http://test.local/a",
                    "method": "GET",
                    "vulnerability_type": "xss",
                },
                {
                    "hypothesis_id": "hyp-2",
                    "endpoint": "http://test.local/b",
                    "method": "GET",
                    "vulnerability_type": "sqli",
                },
            ]
        )
        assert len(results) == 2


# ── HTTPClient Tests ─────────────────────────────────────────


class TestHTTPClient:
    def test_send_returns_response(self) -> None:
        client = HTTPClient(timeout=5.0)
        # Can't actually send in tests, but verify init
        assert client._timeout == 5.0
        assert client._follow_redirects is False

    def test_close(self) -> None:
        client = HTTPClient()
        # Should not raise
        client.close()


# ── ProbeRequest Tests ───────────────────────────────────────


class TestProbeRequest:
    def test_defaults(self) -> None:
        req = ProbeRequest(url="http://test.local")
        assert req.method == "GET"
        assert req.params == {}
        assert req.headers == {}
        assert req.body is None
        assert req.timeout == 10.0


# ── Evidence Format Compatibility ─────────────────────────────


class TestEvidenceCompatibility:
    def test_analysis_result_to_dict_has_all_fields(self) -> None:
        pr = _make_probe_result(status="confirmed", confidence=0.8, vuln="ssrf")
        analyzer = Analyzer()
        result = analyzer.analyze([pr], hypothesis_id="hyp-evidence-001", vulnerability_type="ssrf")
        d = result.to_dict()

        # Fields needed by EvidenceComposer
        assert "hypothesis_id" in d
        assert "vulnerability_type" in d
        assert "endpoint" in d
        assert "method" in d
        assert "status" in d
        assert "confidence" in d
        assert "evidence_items" in d
        assert "poc_data" in d

    def test_poc_data_structure(self) -> None:
        pr = _make_probe_result(status="confirmed", confidence=0.8, vuln="idor")
        analyzer = Analyzer()
        result = analyzer.analyze([pr], hypothesis_id="hyp-poc-001", vulnerability_type="idor")
        poc = result.poc_data

        assert "method" in poc
        assert "endpoint" in poc
        assert "vulnerability_type" in poc
        assert "confidence" in poc
        assert "status" in poc
        assert "cwe" in poc
        assert "cvss_estimate" in poc

    def test_probe_result_compatible_with_evidence(self) -> None:
        pr = _make_probe_result(status="confirmed", confidence=0.7)
        d = pr.to_dict()
        assert "hypothesis_id" in d
        assert "vulnerability_type" in d
        assert "payload_used" in d
        assert "evidence_snippets" in d
