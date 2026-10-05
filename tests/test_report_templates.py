from __future__ import annotations

from cores.reports.templates import (
    platform_list,
    render_report,
    render_report_from_finding,
)


def test_render_hackerone():
    md = render_report("hackerone", {"title": "IDOR test", "vulnerability_type": "idor", "severity": "high"})
    assert "# IDOR test" in md
    assert "Summary" in md
    assert "IDOR test" in md
    assert "sensitive data" in md  # from impact text


def test_render_bugcrowd():
    md = render_report("bugcrowd", {"title": "SSRF test", "vulnerability_type": "ssrf", "severity": "critical"})
    assert "Vulnerability Report:" in md
    assert "SSRF" in md
    assert "Critical" in md  # bugcrowd header includes severity


def test_render_intigriti():
    md = render_report("intigriti", {"title": "XSS test", "vulnerability_type": "xss", "severity": "medium"})
    assert "Security Vulnerability Report" in md
    assert "XSS" in md
    assert "Medium" in md  # intigriti header includes severity


def test_render_immunefi():
    md = render_report(
        "immunefi",
        {
            "title": "Critical Auth Bypass",
            "vulnerability_type": "auth_bypass",
            "severity": "critical",
            "cvss_score": "9.5",
            "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
            "cwe_id": "CWE-288",
            "endpoint": "/api/admin",
        },
    )
    assert "Immunefi Vulnerability Report" in md
    assert "auth_bypass".upper() in md
    assert "CWE-288" in md
    assert "ORION Security Intelligence" in md


def test_render_immunefi_with_poc():
    md = render_report(
        "immunefi",
        {
            "title": "SQLi test",
            "vulnerability_type": "sqli",
            "severity": "critical",
            "poc": {
                "curl": "curl -X GET 'http://example.com?id=1'",
                "nuclei_template": "id: test\ninfo:\n  severity: critical\n",
            },
        },
    )
    assert "cURL" in md
    assert "nuclei_template" not in md  # not in rendered output without the key

    # nuclei should be rendered in immunefi
    import re

    assert re.search(r"Automated Verification", md)


def test_render_with_js_fetch_and_httpie():
    md = render_report(
        "bugcrowd",
        {
            "title": "Test",
            "vulnerability_type": "idor",
            "severity": "medium",
            "poc": {
                "curl": "curl ...",
                "javascript": "fetch(...)",
                "httpie": "http GET ...",
            },
        },
    )
    assert "JavaScript (Fetch API)" in md
    assert "HTTPie" in md
    assert "cURL" in md


def test_render_report_from_finding_minimal():
    data = render_report_from_finding(
        {
            "id": 1,
            "title": "IDOR in profile",
            "description": "Unauthorized access to user data",
            "vulnerability_type": "idor",
            "severity": "high",
            "notes": "",
        }
    )
    assert data["title"] == "IDOR in profile"
    assert data["cvss_score"] != ""
    assert data["cwe_id"] == "CWE-639"


def test_render_report_from_finding_with_endpoint_target():
    data = render_report_from_finding(
        {
            "id": 2,
            "title": "SSRF check",
            "description": "",
            "vulnerability_type": "ssrf",
            "severity": "medium",
            "notes": "",
        },
        endpoint={"path": "/api/fetch", "method": "POST", "parsed_params": {"url": "test"}},
        target={"name": "example", "domain": "example.com"},
    )
    assert data["endpoint"] == "/api/fetch"
    assert data["method"] == "POST"
    assert data["program"] == "example.com"
    assert data["scope_check"] == "In scope — example"


def test_render_report_from_finding_with_notes():
    import json

    data = render_report_from_finding(
        {
            "id": 3,
            "title": "XSS in search",
            "description": "Reflected XSS",
            "vulnerability_type": "xss",
            "severity": "high",
            "notes": json.dumps(
                {"reproduction_steps": ["Go to /search", "Inject <script>"], "business_impact": "Account takeover"}
            ),
        }
    )
    assert "Go to /search" in str(data.get("reproduction_steps", []))


def test_platform_list_includes_immunefi():
    platforms = platform_list()
    assert "immunefi" in platforms
    assert "hackerone" in platforms
    assert "bugcrowd" in platforms
    assert "intigriti" in platforms


def test_render_unknown_platform_raises():
    import pytest

    with pytest.raises(ValueError, match="Unknown platform"):
        render_report("unknown_platform", {})


def test_render_bacl_impact_specific():
    md = render_report("hackerone", {"title": "BACL test", "vulnerability_type": "bacl", "severity": "high"})
    assert "Cross-user" in md or "cross-tenant" in md


def test_render_business_logic_impact_specific():
    md = render_report(
        "intigriti", {"title": "Flow test", "vulnerability_type": "business_logic", "severity": "critical"}
    )
    assert "financial impact" in md.lower()


def test_render_prompt_injection_impact_specific():
    md = render_report("hackerone", {"title": "PI test", "vulnerability_type": "prompt_injection", "severity": "high"})
    assert "tool" in md.lower()


class TestQuantifyImpact:
    def test_explicit_users_win(self):
        from cores.reports.templates import quantify_impact

        q = quantify_impact(
            {
                "vulnerability_type": "idor",
                "severity": "high",
                "users_affected": 1200,
                "reproduction_steps": ["a", "b", "c"],
            }
        )
        assert q["users_scope"] == "measured"
        assert q["has_numbers"] is True
        assert q["reproducibility"] == "steps_documented"
        assert "1200" in q["severity_argument"]

    def test_mass_signals_and_data_classes(self):
        from cores.reports.templates import quantify_impact

        q = quantify_impact(
            {
                "vulnerability_type": "bacl",
                "severity": "critical",
                "description": "collection endpoint allows bulk enumeration of emails and session tokens",
                "evidence": ["GET /api/users?cursor= enumerated 500 ids"],
                "repro_rate": 1.0,
            }
        )
        assert q["users_scope"] == "many_users"
        assert "PII" in q["data_classes"]
        assert "credentials" in q["data_classes"]
        assert q["reproducibility"] == "measured_rate"
        assert q["has_numbers"] is False  # inferred, not measured: honest flag
        assert len(q["severity_argument"]) > 50

    def test_unknown_when_no_evidence(self):
        from cores.reports.templates import quantify_impact

        q = quantify_impact({"vulnerability_type": "xss", "severity": "low", "description": "vague"})
        assert q["users_scope"] == "unknown"
        assert q["reproducibility"] == "unproven"
        assert q["data_classes"] == []
