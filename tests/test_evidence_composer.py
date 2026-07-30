"""Tests for Evidence Composer — PoC generation, CVSS, CWE, Nuclei templates, API."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from core.evidence.composer import (
    CAPEC_MAP,
    CWE_MAP,
    EvidenceBundle,
    EvidenceComposer,
    check_report_readiness,
    compute_cvss,
    generate_curl,
    generate_httpie,
    generate_js_fetch,
    generate_nuclei_template,
    generate_python,
    publish_evidence_event,
)
from core.offensive.models import Hypothesis

# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def sample_hypothesis() -> Hypothesis:
    return Hypothesis(
        vulnerability_type="idor",
        endpoint="/api/users/123",
        method="GET",
        confidence=0.85,
        severity="high",
        summary="IDOR in user profile endpoint",
        description="The /api/users endpoint returns other users' profiles when changing the user ID parameter.",
        parameters_of_interest=["userId", "id"],
        test_instructions=[
            "Send a GET request to /api/users/123 with your own session token",
            "Change userId to 456 and observe if another user's data is returned",
            "Repeat with userId=789 to confirm the pattern",
        ],
        signals=["path contains user ID pattern", "response contains PII fields"],
        scope_check="The target platform is in-scope for the current program",
        reproducibility_notes="Works consistently across multiple user IDs",
    )


@pytest.fixture
def composer() -> EvidenceComposer:
    return EvidenceComposer()


# ── PoC generators ───────────────────────────────────────────────


class TestGenerateCurl:
    def test_basic_get(self):
        result = generate_curl("https://api.example.com/users", "GET", None, None, None, "", "")
        assert result.startswith("curl -X GET 'https://api.example.com/users'")

    def test_with_query_params(self):
        result = generate_curl(
            "https://api.example.com/users",
            "GET",
            {"userId": "12345", "role": "admin"},
            None,
            None,
            "userId",
            "12345",
        )
        assert "userId=12345" in result
        assert "role=admin" in result
        assert "PoC: replace userId with '12345'" in result

    def test_with_headers_and_body(self):
        result = generate_curl(
            "https://api.example.com/users",
            "POST",
            None,
            {"Authorization": "Bearer token123"},
            {"name": "test", "email": "test@example.com"},
            "",
            "",
        )
        assert "Authorization: Bearer token123" in result
        assert "Content-Type: application/json" in result
        assert "test@example.com" in result

    def test_skips_path_params(self):
        result = generate_curl(
            "https://api.example.com/users/{id}",
            "GET",
            {"id": "{id}", "userId": "12345"},
            None,
            None,
            "userId",
            "12345",
        )
        assert "{id}" not in result or "userId=12345" in result


class TestGeneratePython:
    def test_basic_get_with_params(self):
        result = generate_python("GET", "https://api.example.com/users", {"id": "123"}, None, None, "id", "123")
        assert "import requests" in result
        assert "requests.get(url" in result
        assert "id=123" in result or '"id": "123"' in result

    def test_post_with_body(self):
        result = generate_python(
            "POST",
            "https://api.example.com/users",
            None,
            {"Authorization": "Bearer tok"},
            {"name": "test"},
            "",
            "",
        )
        assert "requests.post(url" in result
        assert "json=payload" in result or "name" in result


class TestGenerateJsFetch:
    def test_basic_get(self):
        result = generate_js_fetch("GET", "https://api.example.com/users", None, None, None)
        assert "fetch(" in result
        assert "method" in result or "GET" in result

    def test_post_with_body(self):
        result = generate_js_fetch("POST", "https://api.example.com/users", None, None, {"name": "test"})
        assert "POST" in result.upper() or "method" in result
        assert "JSON.stringify" in result


class TestGenerateHttpie:
    def test_basic_get(self):
        result = generate_httpie("GET", "https://api.example.com/users", None, None, None)
        assert "https" in result

    def test_with_headers(self):
        result = generate_httpie("GET", "https://api.example.com/users", None, {"Authorization": "Bearer tok"}, None)
        assert "Authorization" in result or "Bearer" in result


# ── CVSS calculator ──────────────────────────────────────────────


class TestComputeCvss:
    def test_critical_high_confidence(self):
        score, vector = compute_cvss("critical", 1.0)
        assert score == 9.5
        assert "CRITICAL" not in vector  # vector format, not severity name

    def test_high_medium_confidence(self):
        score, vector = compute_cvss("high", 0.5)
        assert score == 6.4  # round(7.5 * 0.85, 1) = 6.4
        assert "AV:N" in vector

    def test_low_zero_confidence(self):
        score, vector = compute_cvss("low", 0.0)
        assert score == 2.4  # round(3.5 * 0.7, 1) = 2.4
        assert "AV:N" in vector

    def test_unknown_severity_defaults(self):
        score, vector = compute_cvss("unknown", 0.5)
        assert score > 0
        assert "CVSS:3.1" in vector


# ── CWE / CAPEC maps ────────────────────────────────────────────


class TestCweCapecMaps:
    def test_cwe_map_contains_all_types(self):
        for vuln in ("idor", "ssrf", "auth_bypass", "xss", "sqli", "generic"):
            assert vuln in CWE_MAP, f"Missing CWE mapping for {vuln}"

    def test_cwe_format(self):
        for vuln in CWE_MAP:
            cwe_id, cwe_name = CWE_MAP[vuln]
            assert cwe_id.startswith("CWE-"), f"Invalid CWE format for {vuln}: {cwe_id}"
            assert len(cwe_name) > 5

    def test_capec_map_contains_known_types(self):
        for vuln in ("idor", "ssrf", "auth_bypass", "xss", "sqli"):
            assert vuln in CAPEC_MAP, f"Missing CAPEC mapping for {vuln}"

    def test_capec_format(self):
        for vuln in CAPEC_MAP:
            assert CAPEC_MAP[vuln].startswith("CAPEC-"), f"Invalid CAPEC format for {vuln}"


# ── Nuclei template ──────────────────────────────────────────────


class TestGenerateNucleiTemplate:
    def test_returns_valid_yaml_structure(self, sample_hypothesis):
        tid, yaml = generate_nuclei_template(sample_hypothesis)
        assert tid.startswith("orion-")
        assert "id:" in yaml
        assert "info:" in yaml
        assert "http:" in yaml
        assert "matchers:" in yaml

    def test_severity_mapped_correctly(self, sample_hypothesis):
        _, yaml = generate_nuclei_template(sample_hypothesis)
        assert "severity: high" in yaml

    def test_contains_hypothesis_id(self, sample_hypothesis):
        _, yaml = generate_nuclei_template(sample_hypothesis)
        assert sample_hypothesis.id in yaml

    def test_low_severity(self):
        hyp = Hypothesis(vulnerability_type="xss", endpoint="/test", method="GET", severity="low", summary="XSS test")
        _, yaml = generate_nuclei_template(hyp)
        assert "severity: low" in yaml


# ── Report readiness ─────────────────────────────────────────────


class TestCheckReportReadiness:
    def test_complete_bundle_is_ready(self):
        bundle = EvidenceBundle(
            reproduction_steps=["a", "b", "c"],
            expected_result="200",
            actual_result="403",
            business_impact="Critical data exposure",
            cvss_score=7.5,
            cwe_id="CWE-639",
            curl_command="curl -X GET ...",
            preconditions=["logged in"],
        )
        is_ready, gaps = check_report_readiness(bundle)
        assert is_ready
        assert len(gaps) <= 2

    def test_empty_bundle_has_gaps(self):
        bundle = EvidenceBundle()
        is_ready, gaps = check_report_readiness(bundle)
        assert not is_ready
        assert len(gaps) >= 4

    def test_minimal_valid_bundle(self):
        bundle = EvidenceBundle(
            reproduction_steps=["a", "b", "c"],
            expected_result="200",
            actual_result="403",
            business_impact="Data leak",
            cvss_score=5.0,
            cwe_id="CWE-200",
            curl_command="curl ...",
            preconditions=["auth"],
        )
        is_ready, gaps = check_report_readiness(bundle)
        assert is_ready


# ── EvidenceComposer ─────────────────────────────────────────────


class TestEvidenceComposer:
    def test_compose_returns_bundle_with_all_fields(self, sample_hypothesis, composer):
        bundle = composer.compose(sample_hypothesis)
        assert bundle.hypothesis_id == sample_hypothesis.id
        assert bundle.vulnerability_type == "idor"
        assert bundle.endpoint == "/api/users/123"
        assert bundle.method == "GET"
        assert bundle.cvss_score > 0
        assert bundle.curl_command
        assert bundle.python_script
        assert bundle.js_fetch_code
        assert bundle.httpie_command
        assert bundle.nuclei_template
        assert bundle.nuclei_template_id
        assert len(bundle.reproduction_steps) >= 3
        assert bundle.business_impact
        assert bundle.cwe_id == "CWE-639"

    def test_compose_from_dict(self, composer):
        data = {
            "vulnerability_type": "sqli",
            "endpoint": "/api/search",
            "method": "POST",
            "confidence": 0.75,
            "severity": "critical",
            "summary": "SQLi in search parameter",
            "description": "The search endpoint reflects user input in error messages",
            "parameters_of_interest": ["q", "query"],
            "test_instructions": ["Send POST with q=' OR '1'='1"],
            "signals": ["error messages contain SQL syntax"],
            "scope_check": "In scope",
            "reproducibility_notes": "Works consistently",
        }
        bundle = composer.compose_from_dict(data, host="https://api.example.com")
        assert bundle.vulnerability_type == "sqli"
        assert bundle.endpoint == "/api/search"
        assert bundle.method == "POST"
        assert bundle.cvss_score > 0
        assert bundle.cwe_id == "CWE-89"
        assert bundle.curl_command
        assert bundle.python_script
        assert bundle.nuclei_template

    def test_to_dict_structure(self, sample_hypothesis, composer):
        bundle = composer.compose(sample_hypothesis)
        d = bundle.to_dict()
        assert "hypothesis_id" in d
        assert "poc" in d
        assert "scoring" in d
        assert "report_body" in d
        assert "system_reasoning" in d
        assert "readiness" in d
        assert "nuclei_template" in d
        assert "nuclei_template_id" in d
        assert d["poc"]["curl"]
        assert d["scoring"]["cvss_score"] > 0
        assert isinstance(d["readiness"]["is_report_ready"], bool)

    def test_compose_from_dict_minimal(self, composer):
        bundle = composer.compose_from_dict({"vulnerability_type": "xss"})
        assert bundle.vulnerability_type == "xss"
        assert bundle.cwe_id == "CWE-79"
        assert bundle.curl_command

    def test_compose_sets_confidence_level(self, sample_hypothesis, composer):
        bundle = composer.compose(sample_hypothesis)
        assert bundle.confidence_level == "high"

    def test_compose_low_confidence(self, composer):
        hyp = Hypothesis(
            vulnerability_type="generic",
            endpoint="/test",
            method="GET",
            confidence=0.2,
            severity="low",
            summary="Low confidence test",
        )
        bundle = composer.compose(hyp)
        assert bundle.confidence_level == "low"


# ── Event publishing (mocked) ────────────────────────────────────


class TestPublishEvidenceEvent:
    def test_publishes_event_successfully(self):
        bundle = EvidenceBundle(
            hypothesis_id="hyp-test",
            vulnerability_type="idor",
            is_report_ready=True,
            cvss_score=7.5,
            cwe_id="CWE-639",
            acceptance_probability=0.8,
        )
        with patch("cores.events.event_bus.get_core_event_bus") as mock_get_bus:
            mock_bus = mock_get_bus.return_value
            publish_evidence_event("composed", bundle)
            mock_bus.publish.assert_called_once()

    def test_handles_event_bus_failure_gracefully(self):
        bundle = EvidenceBundle(hypothesis_id="hyp-test")
        with patch("core.events.event_bus.get_core_event_bus", side_effect=ImportError("No bus")):
            publish_evidence_event("composed", bundle)  # should not raise


# ── API endpoint ─────────────────────────────────────────────────


class TestEvidenceApi:
    _token: str | None = None

    @classmethod
    def _get_token(cls) -> str:
        if cls._token is None:
            from cores.auth.auth import create_session_token

            cls._token = create_session_token("test_device")
        return cls._token

    @classmethod
    def _auth_header(cls) -> dict[str, str]:
        return {"Authorization": f"Bearer {cls._get_token()}"}

    def test_compose_endpoint_returns_200(self):
        from api.main import app

        client = TestClient(app)
        payload = {
            "vulnerability_type": "idor",
            "endpoint": "/api/users/123",
            "method": "GET",
            "confidence": 0.85,
            "severity": "high",
            "summary": "IDOR in user profile",
            "description": "Users can access other users' profiles",
            "parameters_of_interest": ["userId"],
            "test_instructions": ["Change userId parameter"],
        }
        resp = client.post("/api/evidence/compose", json=payload, headers=self._auth_header())
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["schema_version"] == "1.0"
        assert data["generator"] == "EvidenceComposer"
        assert "bundle" in data
        bundle = data["bundle"]
        assert bundle["vulnerability_type"] == "idor"
        assert bundle["poc"]["curl"]
        assert bundle["scoring"]["cvss_score"] > 0
        assert bundle["scoring"]["cwe_id"] == "CWE-639"
        assert bundle["readiness"]["is_report_ready"] is not None
        assert bundle["nuclei_template"]

    def test_compose_endpoint_invalid_type_returns_422(self):
        from api.main import app

        client = TestClient(app)
        resp = client.post("/api/evidence/compose", json={"confidence": "not-a-float"}, headers=self._auth_header())
        assert resp.status_code == 422

    def test_compose_endpoint_minimal_payload(self):
        from api.main import app

        client = TestClient(app)
        resp = client.post("/api/evidence/compose", json={"endpoint": "/api/test"}, headers=self._auth_header())
        assert resp.status_code == 200
        data = resp.json()
        assert data["bundle"]["vulnerability_type"] == "generic"

    def test_compose_endpoint_unauthorized_without_token(self):
        from api.main import app

        client = TestClient(app)
        resp = client.post("/api/evidence/compose", json={"endpoint": "/api/test"})
        assert resp.status_code == 401
