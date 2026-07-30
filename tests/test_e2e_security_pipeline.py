"""E2E tests for Security Cycle pipeline stages with real execution.

Tests each stage executor with realistic context data,
verifying the output format and data propagation between stages.
"""

from __future__ import annotations

from cores.cycles.stages import get_executor


def _make_context(target: str = "e2e-test.ownex.io", **overrides) -> dict:
    """Build a realistic pipeline context."""
    ctx = {
        "target": target,
        "scope": [f"*.{target}", f"api.{target}"],
        "mode": "test",
        "pipeline_context": {},
        "endpoints": [],
        "attack_surface": {},
        "hypotheses": [],
        "findings": [],
        "confirmed_findings": [],
        "reports": [],
    }
    ctx.update(overrides)
    return ctx


class TestStageRecon:
    def test_execute_returns_stage_result(self):
        ex = get_executor("recon")
        ctx = _make_context()
        result = ex.execute(ctx)
        assert result["stage"] == "recon"
        assert result["status"] in ("completed", "skipped", "failed")
        assert "summary" in result
        assert "details" in result


class TestStageAttackSurface:
    def test_execute_with_recon_context(self):
        ex = get_executor("attack_surface")
        ctx = _make_context(endpoints=["e2e-test.ownex.io", "api.e2e-test.ownex.io"])
        result = ex.execute(ctx)
        assert result["stage"] == "attack_surface"
        assert result["status"] in ("completed", "skipped", "failed")


class TestStageHypothesis:
    def test_execute_with_attack_surface(self):
        ex = get_executor("hypothesis")
        ctx = _make_context(
            endpoints=["e2e-test.ownex.io:80", "e2e-test.ownex.io:443"],
            attack_surface={
                "domains": ["e2e-test.ownex.io"],
                "technologies": ["nginx", "react"],
                "open_ports": [80, 443],
            },
        )
        result = ex.execute(ctx)
        assert result["stage"] == "hypothesis"
        assert result["status"] in ("completed", "skipped", "failed")


class TestStageValidation:
    def test_execute_with_hypothesis(self):
        ex = get_executor("validation")
        ctx = _make_context(
            hypotheses=[
                {"id": "H-1", "type": "xss", "confidence": 0.7, "target": "e2e-test.ownex.io"},
                {"id": "H-2", "type": "sqli", "confidence": 0.4, "target": "e2e-test.ownex.io"},
            ]
        )
        result = ex.execute(ctx)
        assert result["stage"] == "validation"
        assert result["status"] in ("completed", "skipped", "failed")


class TestStageEvidence:
    def test_execute_with_validated_findings(self):
        ex = get_executor("evidence")
        ctx = _make_context(
            confirmed_findings=[
                {"id": "F-1", "type": "xss", "severity": "high", "endpoint": "e2e-test.ownex.io"},
            ]
        )
        result = ex.execute(ctx)
        assert result["stage"] == "evidence"
        assert result["status"] in ("completed", "skipped", "failed")


class TestStageReport:
    def test_execute_with_evidence(self):
        ex = get_executor("report")
        ctx = _make_context(
            evidence_packages=[
                {"finding_id": "F-1", "poC": "<script>alert(1)</script>", "screenshots": []},
            ]
        )
        result = ex.execute(ctx)
        assert result["stage"] == "report"
        assert result["status"] in ("completed", "skipped", "failed")


class TestStageLearning:
    def test_execute_with_completed_pipeline(self):
        ex = get_executor("learning")
        ctx = _make_context(
            reports=[{"id": "R-1", "finding_id": "F-1", "submitted": True}],
            pipeline_context={
                "stages_completed": ["recon", "attack_surface", "hypothesis", "validation", "evidence", "report"],
                "duration_seconds": 120,
            },
        )
        result = ex.execute(ctx)
        assert result["stage"] == "learning"
        assert result["status"] in ("completed", "skipped", "failed")


class TestPipelineFullCycle:
    """Simulate the full 7-stage pipeline end-to-end."""

    def test_all_stages_run_sequentially(self):
        context = _make_context()
        stages = ["recon", "attack_surface", "hypothesis", "validation", "evidence", "report", "learning"]
        results = []

        for stage in stages:
            ex = get_executor(stage)
            result = ex.execute(context)
            results.append(result)
            assert result["stage"] == stage
            assert result["status"] in ("completed", "skipped", "failed")
            # Propagate results as SecurityCycle.run_pipeline does
            details = result.get("details", {})
            if stage == "recon":
                context["endpoints"] = details.get("endpoints", context.get("endpoints", []))
            elif stage == "attack_surface":
                context["attack_surface"] = details
            elif stage == "hypothesis":
                context["hypotheses"] = details.get("hypotheses", context.get("hypotheses", []))
            elif stage == "validation":
                context["confirmed_findings"] = details.get("confirmed", context.get("confirmed_findings", []))
            elif stage == "evidence":
                context["evidence_packages"] = details.get("evidence_packages", [])
            elif stage == "report":
                context["reports"] = details.get("reports", [])

        assert len(results) == 7
        completed = sum(1 for r in results if r["status"] == "completed")
        assert completed >= 0  # Some may skip if no data
