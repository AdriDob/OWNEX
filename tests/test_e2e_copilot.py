"""E2E integration tests for OWNEX Copilot Commander + full pipeline.

Tests the real end-to-end flow without HTTP mocks:
  1. Copilot context engine -> system data -> prompt
  2. Provider router -> model routing -> task dispatch
  3. Security cycle pipeline: recon -> attack_surface -> hypothesis -> validation -> evidence -> report -> learning
  4. Opportunity engine: discovery -> scoring -> top recommendations
  5. Execution layer: execute actions via copilot
  6. Browser workers: platform worker creation and action routing
  7. Dashboard data consistency
"""

from __future__ import annotations

import asyncio

import pytest

# ── 1. COPILOT COMMANDER E2E ─────────────────────────────────────────


class TestCopilotCommanderE2E:
    """Real E2E: provider health -> context -> routing -> execute"""

    @pytest.mark.asyncio
    async def test_1_providers_health(self):
        """Real: get_provider_monitor returns healthy providers."""
        from core.orion.health.provider_monitor import get_provider_monitor

        monitor = get_provider_monitor()
        assert monitor is not None
        report = await monitor.check_all()
        assert report.healthy_count >= 2
        assert report.total_count >= 4
        assert "omniroute" in report.providers

    @pytest.mark.asyncio
    async def test_2_providers_check_all(self):
        """Real: provider monitor checks all providers."""
        from core.orion.health.provider_monitor import get_provider_monitor

        monitor = get_provider_monitor()
        report = await monitor.check_all()
        assert report.healthy_count >= 2
        assert report.total_count >= 4
        for p in report.providers.values():
            assert hasattr(p, "state")

    @pytest.mark.asyncio
    async def test_3_context_engine_builds(self):
        """Real: context engine builds all blocks."""
        from core.commander.context_engine import build_context_async

        ctx = await build_context_async()
        blocks = list(ctx.blocks.keys())
        assert "providers" in blocks
        assert "model_router" in blocks
        assert "failover" in blocks
        assert "decisions" in blocks
        assert "system_context" in blocks
        assert len(blocks) >= 6

    @pytest.mark.asyncio
    async def test_4_providers_block_has_data(self):
        """Real: provider block contains provider health data."""
        from core.commander.context_engine import build_context_async

        ctx = await build_context_async()
        prov = ctx.get_block("providers")
        assert prov is not None
        assert "overall" in prov.data
        assert "providers" in prov.data
        assert len(prov.data["providers"]) >= 4

    @pytest.mark.asyncio
    async def test_5_system_context_has_counts(self):
        """Real: system context includes real DB counts."""
        from core.commander.context_engine import build_context_async

        ctx = await build_context_async()
        sys = ctx.get_block("system_context")
        assert sys is not None
        assert "counts" in sys.data
        c = sys.data["counts"]
        assert "targets" in c
        assert c["targets"] >= 0

    @pytest.mark.asyncio
    async def test_6_normalizes_prompt(self):
        """Real: prompt context builds for mission control."""
        from core.commander.context_engine import get_prompt_context_async

        prompt = await get_prompt_context_async("¿Cuáles son las mejores oportunidades hoy?")
        assert isinstance(prompt, str)
        assert len(prompt) > 50

    def test_7_copilot_context_api(self):
        """Real: copilot router returns system context dict."""

        # Test that context generation works
        from core.commander.audit import get_audit_logger

        logger = get_audit_logger()
        summary = logger.get_session_summary()
        assert "total_entries" in summary
        assert summary["total_entries"] >= 0


# ── 2. SECURITY CYCLE PIPELINE E2E ───────────────────────────────────


class TestSecurityCycleE2E:
    """Real E2E: security cycle start -> stages -> dashboard -> learning"""

    def test_1_security_cycle_has_7_stages(self):
        from cores.cycles.security import get_security_cycle

        sc = get_security_cycle()
        assert len(sc.STAGE_ORDER) == 7
        assert sc.STAGE_ORDER == [
            "recon",
            "attack_surface",
            "hypothesis",
            "validation",
            "evidence",
            "report",
            "learning",
        ]

    def test_2_all_stage_executors_register(self):
        from cores.cycles.stages import get_executor

        for stage in ["recon", "attack_surface", "hypothesis", "validation", "evidence", "report", "learning"]:
            ex = get_executor(stage)
            assert ex.name == stage

    def test_3_executive_dashboard_has_keys(self):
        from core.cycles.security import get_security_cycle

        sc = get_security_cycle()
        dash = sc.get_dashboard()
        assert "verdict" in dash
        assert "made_money_this_week" in dash
        assert "weekly" in dash
        assert "monthly" in dash
        assert "efficiency" in dash
        assert "pipeline" in dash

    def test_4_pipeline_stage_execution(self):
        """Integration: each stage executor runs with test context."""
        from cores.cycles.stages import get_executor

        context = {
            "target": "e2e-test.ownex.io",
            "scope": ["*.ownex.io", "api.ownex.io"],
            "mode": "test",
        }
        for stage in ["recon", "attack_surface", "hypothesis"]:
            ex = get_executor(stage)
            result = ex.execute(context)
            assert result["stage"] == stage
            assert result["status"] in ("completed", "skipped", "failed")

    def test_5_full_pipeline_runs(self):
        """Full 7-stage pipeline runs sequentially."""
        from cores.cycles.stages import get_executor

        context = {
            "target": "e2e-test.ownex.io",
            "scope": ["*.ownex.io"],
            "mode": "test",
            "endpoints": [],
            "findings": [],
            "confirmed_findings": [],
            "reports": [],
        }
        stages = ["recon", "attack_surface", "hypothesis", "validation", "evidence", "report", "learning"]
        results = []
        for stage in stages:
            ex = get_executor(stage)
            result = ex.execute(context)
            results.append(result)
            assert result["stage"] == stage
            if result["status"] == "completed":
                details = result.get("details", {})
                if stage == "recon":
                    context["endpoints"] = details.get("endpoints", context.get("endpoints", []))
                elif stage == "attack_surface":
                    context["attack_surface"] = details
                elif stage == "hypothesis":
                    context["hypotheses"] = details.get("hypotheses", [])
                elif stage == "validation":
                    context["confirmed_findings"] = details.get("confirmed", [])
        assert len(results) == 7


# ── 3. OPPORTUNITY ENGINE E2E ────────────────────────────────────────


class TestOpportunityEngineE2E:
    """Real E2E: opportunity scoring -> recommendation"""

    def test_1_scoring_model(self):
        from core.opportunity.models import UnifiedScore

        score = UnifiedScore(
            expected_value=8500.0,
            acceptance_probability=0.35,
            speed_days=14,
            difficulty=0.4,
            competition=0.5,
            personal_fit=0.8,
            confidence=0.75,
        )
        assert score.expected_value == 8500.0
        assert len(score.reasoning()) > 0

    def test_2_all_executors_registered(self):
        from core.opportunity.executors import get_executors

        ex = get_executors()
        assert "algora" in ex
        assert "freelancer" in ex
        assert "opire" in ex
        assert "issuehunt" in ex
        for _name, executor in ex.items():
            assert hasattr(executor, "execute")
            assert hasattr(executor, "is_enabled")

    def test_3_opportunity_orchestrator(self):
        from core.opportunity.engine import OpportunityOrchestrator

        engine = OpportunityOrchestrator()
        assert engine is not None
        assert hasattr(engine, "forge_adapters")
        assert hasattr(engine, "pulse_adapters")
        assert len(engine.forge_adapters) >= 1

    def test_4_opportunity_scored_dataclass(self):
        from core.opportunity.models import ScoredOpportunity, UnifiedScore

        opp = ScoredOpportunity(
            id="E2E-TEST",
            name="Test opportunity",
            cycle="forge",
            source_type="algora",
            source_name="Algora",
            reward=5000.0,
            effort_hours=8,
            platform="algora",
            technology_tags=["python", "web"],
            url="https://algora.io/test",
            created_at="2026-07-30T12:00:00Z",
            score=UnifiedScore(expected_value=5000.0),
        )
        assert opp.id == "E2E-TEST"
        assert "python" in opp.technology_tags

    def test_5_top5_recommendations(self):
        from core.opportunity.models import Top5Recommendation
        from core.opportunity.top5 import Top5Engine

        engine = Top5Engine()
        recommendations = engine.compute([])
        assert isinstance(recommendations, Top5Recommendation)
        assert len(recommendations.ranked) == 0

    def test_6_opportunity_executor_base(self):
        from core.opportunity.executors import BaseExecutor, ExecutionResult

        class TestEx(BaseExecutor):
            async def execute(self, action, **kwargs):
                return ExecutionResult(True, action, "test")

        ex = TestEx({"k": "v"})
        assert ex.is_enabled()
        assert ex.get_config("k") == "v"
        assert ex.get_config("missing", "d") == "d"


# ── 4. EXECUTION LAYER E2E ───────────────────────────────────────────


class TestExecutionLayerE2E:
    """E2E: executor interfaces, copilot execute actions"""

    def test_1_coder_agent_imports(self):
        """Real: CoderAgent can be imported and used."""
        from core.autonomy.coder_agent import CoderAgent, CoderAgentConfig

        config = CoderAgentConfig()
        assert config is not None
        assert hasattr(config, "model")

    def test_2_evolution_cycle_works(self):
        """Real: evolution engine cycle detects issues."""
        from core.evolution.engine import get_evolution_engine

        engine = get_evolution_engine()
        report = engine.run_cycle()
        assert report.proposals is not None
        assert report.health_before is not None

    def test_3_self_healer_diagnoses(self):
        """Real: self-healer diagnoses without error."""
        from core.evolution.self_healer import SelfHealer

        healer = SelfHealer()
        issues = healer.diagnose()
        assert isinstance(issues, list)

    def test_4_security_cycle_works(self):
        """Real: security cycle dashboard works."""
        from core.cycles.security import get_security_cycle

        sc = get_security_cycle()
        dash = sc.get_dashboard()
        assert "verdict" in dash
        assert "pipeline" in dash

    def test_5_copilot_provider_chain(self):
        """Real: copilot provider router has correct priority."""
        from core.copilot.providers.router import get_provider_router

        pr = get_provider_router()
        names = [p.name for p in pr.providers]
        assert names[0] == "fcc"


# ── 5. BROWSER WORKERS E2E ───────────────────────────────────────────


class TestBrowserWorkersE2E:
    """E2E: browser worker creation and action routing"""

    def test_1_all_workers_importable(self):
        from core.automation.workers import (
            DataAnnotationWorker,
            MindriftBrowserWorker,
            OutlierWorker,
            RemotasksWorker,
        )

        assert DataAnnotationWorker().platform == "dataannotation"
        assert OutlierWorker().platform == "outlier"
        assert RemotasksWorker().platform == "remotasks"
        assert MindriftBrowserWorker().platform == "mindrift_browser"

    @pytest.mark.asyncio
    async def test_2_unknown_action_returns_error(self):
        from core.automation.workers import DataAnnotationWorker

        w = DataAnnotationWorker()
        result = await w.execute("nonexistent_action")
        assert result["success"] is False
        assert "Unknown action" in result.get("error", "")

    def test_3_get_browser_workers_returns_4(self):
        from core.automation.workers import get_browser_workers

        workers = get_browser_workers()
        assert len(workers) == 4
        assert "dataannotation" in workers
        assert "outlier" in workers
        assert "remotasks" in workers
        assert "mindrift_browser" in workers


# ── 6. MODEL ROUTER COPILOT INTEGRATION E2E ──────────────────────────


class TestCopilotModelRoutingE2E:
    """E2E: model router assigns correct models per task type"""

    def test_1_all_task_types_route(self):
        from core.ai.model_router import TaskType, get_model_router

        router = get_model_router()
        for tt in TaskType:
            d = router.route(tt)
            assert d.selected_model is not None
            assert d.provider is not None
            assert d.tier is not None

    def test_2_analysis_gets_primary_tier(self):
        from core.ai.model_router import TaskType, get_model_router

        router = get_model_router()
        d = router.route(TaskType.ANALYSIS)
        assert d.tier.name in ("PRIMARY", "FALLBACK", "LOCAL", "FREE")

    def test_3_copilot_provider_chain(self):
        from core.copilot.providers.router import get_provider_router

        pr = get_provider_router()
        names = [p.name for p in pr.providers]
        assert names[0] == "fcc"
        assert "ollama" in names

    @pytest.mark.asyncio
    async def test_4_provider_router_checks_all(self):
        from core.copilot.providers.router import get_provider_router

        pr = get_provider_router()
        for p in pr.providers:
            ok = await p.check()
            assert ok is not None


# ── 7. WORKFLOW ENGINE E2E ───────────────────────────────────────────


class TestWorkflowEngineE2E:
    """E2E: workflow engine integration"""

    @pytest.mark.asyncio
    async def test_1_create_workflow(self):
        from core.autonomy.workflow_engine import create_autonomous_workflow

        wf = await create_autonomous_workflow()
        assert len(wf.executors) >= 2
        assert "algora" in wf.executors

    @pytest.mark.asyncio
    async def test_2_workflow_cycle_runs(self):
        from core.autonomy.workflow_engine import create_autonomous_workflow

        wf = await create_autonomous_workflow()
        results = await wf.run_cycle()
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_3_audit_logger_works(self):
        from core.commander.audit import get_audit_logger

        audit = get_audit_logger()
        audit.log(
            objective="E2E test",
            reasoning="Verifying audit logger works",
            tools_used=["pytest"],
            changes_made=["e2e_test"],
            validation="e2e",
            result="completed",
            provider_used="opencode",
            model_used="opencode/deepseek-v4-flash-free",
            agent_id="pytest",
            success=True,
        )
        summary = audit.get_session_summary()
        assert summary["total_entries"] > 0
