"""Tests F4 — playbooks de IA (JS diffing + report drafting)."""

from __future__ import annotations

from cores.offensive.ai_playbooks import js_diff_analysis, report_draft


class TestJsDiff:
    def test_primer_snapshot_no_marca_nuevos(self):
        js = 'fetch("/api/orders"); var x = "token";'
        out = js_diff_analysis(js)
        assert out["is_first_snapshot"] is True
        assert out["new_routes"] == []
        assert "/api/orders" in out["top_routes"]

    def test_detecta_rutas_nuevas_vs_baseline(self):
        old = 'fetch("/api/orders");'
        new = 'fetch("/api/orders"); fetch("/api/beta/export");'
        out = js_diff_analysis(new, old)
        assert out["is_first_snapshot"] is False
        assert out["new_routes"] == ["/api/beta/export"]

    def test_marca_beta_y_sensibles(self):
        js = 'fetch("/internal/admin"); var token = 1; var secret = 2;'
        out = js_diff_analysis(js)
        assert any("internal" in r for r in out["beta_like_routes"])
        assert out["sensitive_hits"]


class TestReportDraft:
    def test_completo_va_listo(self):
        out = report_draft(
            {
                "title": "IDOR exposes all user PII",
                "vulnerability_type": "idor",
                "endpoint": "GET /api/users/{id}",
                "severity": "high",
                "reproduction_steps": ["A", "B", "C", "D"],
                "poc": {"curl": "curl https://t/x"},
                "evidence": ["screenshot"],
                "impact": "An attacker can access the personal data of any user in the system.",
                "cwe_id": "CWE-639",
                "cvss_score": 7.5,
                "remediation": "Add ownership checks server-side.",
            },
            platform="hackerone",
        )
        assert out["ready_to_send"] is True
        assert out["missing"] == []
        assert out["platform_requirements"]

    def test_exige_escala_en_high(self):
        out = report_draft(
            {
                "title": "X",
                "vulnerability_type": "ssrf",
                "severity": "high",
                "reproduction_steps": ["A", "B", "C"],
                "poc": {"curl": "c"},
                "evidence": ["e"],
                "impact": "Might reach something bad somewhere.",
                "cwe_id": "CWE-918",
                "remediation": "r",
            },
        )
        assert out["ready_to_send"] is False
        assert any("impact_scale" in m for m in out["missing"])

    def test_medium_no_exige_escala(self):
        out = report_draft(
            {
                "title": "X",
                "vulnerability_type": "xss",
                "severity": "medium",
                "reproduction_steps": ["A", "B", "C"],
                "poc": {"curl": "c"},
                "evidence": ["e"],
                "impact": "Self-XSS requires user interaction.",
                "cwe_id": "CWE-79",
                "remediation": "r",
            },
        )
        assert not any("impact_scale" in m for m in out["missing"])

    def test_vacio_es_borrador_con_missing(self):
        out = report_draft({})
        assert out["ready_to_send"] is False
        assert "title" in out["missing"]
        assert "poc_curl" in out["missing"]
        assert out["vulnerability_type"] == "UNKNOWN"

    def test_impact_frame_por_severity(self):
        out = report_draft({"severity": "critical"})
        assert "Production" in out["impact_frame"]
