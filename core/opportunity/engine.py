from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger("ownex.opportunity.engine")


class OpportunityType(StrEnum):
    SECURITY_BOUNTY = "security_bounty"
    DEV_BOUNTY = "dev_bounty"
    AI_WORK = "ai_work"
    FREELANCE = "freelance"
    DATA_ANNOTATION = "data_annotation"
    CONTENT_CREATION = "content_creation"
    RESEARCH = "research"


class PreparationStatus(StrEnum):
    PENDING = "pending"
    READING_RULES = "reading_rules"
    DOWNLOADING_DOCS = "downloading_docs"
    ANALYZING_DATASETS = "analyzing_datasets"
    GENERATING_STRUCTURE = "generating_structure"
    PREPARING_CODE = "preparing_code"
    CREATING_DRAFTS = "creating_drafts"
    IDENTIFYING_GAPS = "identifying_gaps"
    READY_FOR_USER = "ready_for_user"
    COMPLETED = "completed"


class DecisionMode(StrEnum):
    EXPLANATORY = "explanatory"
    AUTOMATIC = "automatic"
    EXPERT = "expert"


@dataclass
class OpportunityMetrics:
    expected_value: float = 0.0
    time_required_hours: float = 0.0
    success_probability: float = 0.0
    automation_potential: float = 0.0
    strategic_value: float = 0.0
    learning_generated: float = 0.0
    future_reusability: float = 0.0

    @property
    def opportunity_score(self) -> float:
        weights = {
            "ev": 0.30,
            "time": -0.15,
            "success": 0.25,
            "automation": 0.15,
            "strategic": 0.10,
            "learning": 0.05,
        }
        score = (
            weights["ev"] * min(self.expected_value / 1000, 1.0)
            + weights["time"] * min(self.time_required_hours / 40, 1.0)
            + weights["success"] * self.success_probability
            + weights["automation"] * self.automation_potential
            + weights["strategic"] * self.strategic_value
            + weights["learning"] * self.learning_generated
        )
        return max(0.0, min(1.0, score))


@dataclass
class Opportunity:
    id: str
    type: OpportunityType
    title: str
    description: str
    source: str
    url: str | None = None
    reward: float = 0.0
    difficulty: float = 0.5
    confidence: float = 0.5
    estimated_hours: float = 2.0
    skills_required: list[str] = field(default_factory=list)
    platform: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    metrics: OpportunityMetrics = field(default_factory=OpportunityMetrics)
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    decision: DecisionMode = DecisionMode.EXPLANATORY
    preparation_status: PreparationStatus = PreparationStatus.PENDING
    preparation_artifacts: dict[str, Any] = field(default_factory=dict)
    missing_info: list[str] = field(default_factory=list)

    @property
    def score(self) -> float:
        return self.metrics.opportunity_score

    def to_decision_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type.value,
            "score": round(self.score, 4),
            "expected_value": self.metrics.expected_value,
            "time_required_hours": self.metrics.time_required_hours,
            "success_probability": self.metrics.success_probability,
            "automation_potential": self.metrics.automation_potential,
            "strategic_value": self.metrics.strategic_value,
            "learning_generated": self.metrics.learning_generated,
            "recommendation": self._get_recommendation(),
            "preparation_status": self.preparation_status.value,
            "missing_info": self.missing_info,
            "explanation": self._generate_explanation(),
        }

    def _get_recommendation(self) -> str:
        if self.score >= 0.75:
            return "EXECUTE_NOW"
        elif self.score >= 0.50:
            return "PREPARE_AND_REVIEW"
        elif self.score >= 0.30:
            return "MONITOR"
        else:
            return "DISCARD"

    def _generate_explanation(self) -> str:
        parts = []
        parts.append(f"Score: {self.score:.2%}")
        parts.append(f"EV: ${self.metrics.expected_value:,.0f} in ~{self.metrics.time_required_hours:.1f}h")
        parts.append(f"Success: {self.metrics.success_probability:.0%}")
        parts.append(f"Automation: {self.metrics.automation_potential:.0%}")
        if self.metrics.strategic_value > 0.5:
            parts.append(f"Strategic: {self.metrics.strategic_value:.0%}")
        if self.metrics.learning_generated > 0.5:
            parts.append(f"Learning: {self.metrics.learning_generated:.0%}")
        return " | ".join(parts)


class OpportunityScorer:
    def __init__(self) -> None:
        self.history: dict[str, dict] = {}

    def calculate_metrics(self, opp: Opportunity) -> OpportunityMetrics:
        m = OpportunityMetrics()

        m.expected_value = opp.reward * opp.confidence
        m.time_required_hours = opp.estimated_hours
        m.success_probability = opp.confidence * (1.0 - opp.difficulty * 0.5)

        automation_map = {
            OpportunityType.DEV_BOUNTY: 0.9,
            OpportunityType.DATA_ANNOTATION: 0.8,
            OpportunityType.AI_WORK: 0.7,
            OpportunityType.SECURITY_BOUNTY: 0.4,
            OpportunityType.FREELANCE: 0.3,
            OpportunityType.CONTENT_CREATION: 0.6,
            OpportunityType.RESEARCH: 0.5,
        }
        m.automation_potential = automation_map.get(opp.type, 0.5)

        strategic_keywords = ["recurring", "portfolio", "network", "reputation", "skill_building"]
        m.strategic_value = sum(0.15 for kw in strategic_keywords if kw in opp.metadata.get("tags", []))
        m.strategic_value = min(m.strategic_value, 1.0)

        learning_keywords = ["new_platform", "new_tech", "new_domain", "complex", "novel"]
        m.learning_generated = sum(0.12 for kw in learning_keywords if kw in opp.metadata.get("tags", []))
        m.learning_generated = min(m.learning_generated, 1.0)

        reusability = 0.0
        if opp.type in (OpportunityType.DEV_BOUNTY, OpportunityType.SECURITY_BOUNTY):
            reusability += 0.3
        if opp.metadata.get("has_template", False):
            reusability += 0.2
        if opp.metadata.get("repeatable", False):
            reusability += 0.3
        m.future_reusability = min(reusability, 1.0)

        if opp.id in self.history:
            h = self.history[opp.id]
            m.success_probability *= 1.0 + h.get("success_rate", 0.0) * 0.2
            m.success_probability = min(m.success_probability, 1.0)

        return m

    def record_outcome(self, opp_id: str, success: bool, actual_value: float, actual_hours: float) -> None:
        if opp_id not in self.history:
            self.history[opp_id] = {"attempts": 0, "successes": 0, "total_value": 0.0, "total_hours": 0.0}
        h = self.history[opp_id]
        h["attempts"] += 1
        if success:
            h["successes"] += 1
        h["total_value"] += actual_value
        h["total_hours"] += actual_hours


class OpportunityPreparator:
    def __init__(self, decision_mode: DecisionMode = DecisionMode.EXPLANATORY) -> None:
        self.decision_mode = decision_mode

    async def prepare(self, opp: Opportunity) -> Opportunity:
        opp.preparation_status = PreparationStatus.READING_RULES
        opp.preparation_artifacts["rules"] = await self._read_rules(opp)

        opp.preparation_status = PreparationStatus.DOWNLOADING_DOCS
        opp.preparation_artifacts["documentation"] = await self._download_docs(opp)

        opp.preparation_status = PreparationStatus.ANALYZING_DATASETS
        opp.preparation_artifacts["dataset_analysis"] = await self._analyze_datasets(opp)

        opp.preparation_status = PreparationStatus.GENERATING_STRUCTURE
        opp.preparation_artifacts["structure"] = await self._generate_structure(opp)

        opp.preparation_status = PreparationStatus.PREPARING_CODE
        opp.preparation_artifacts["code_skeleton"] = await self._prepare_code(opp)

        opp.preparation_status = PreparationStatus.CREATING_DRAFTS
        opp.preparation_artifacts["drafts"] = await self._create_drafts(opp)

        opp.preparation_status = PreparationStatus.IDENTIFYING_GAPS
        opp.missing_info = await self._identify_gaps(opp)

        opp.preparation_status = PreparationStatus.READY_FOR_USER
        return opp

    async def _read_rules(self, opp: Opportunity) -> dict[str, Any]:
        rules = {
            "platform_rules": f"Rules for {opp.platform}",
            "submission_format": "Standard format",
            "quality_criteria": ["Completeness", "Accuracy", "Originality"],
            "deadline": opp.metadata.get("deadline"),
            "payout_terms": opp.metadata.get("payout_terms", "On acceptance"),
        }
        if self.decision_mode == DecisionMode.EXPLANATORY:
            rules["explanation"] = "Rules define acceptance criteria and payout conditions"
        return rules

    async def _download_docs(self, opp: Opportunity) -> dict[str, Any]:
        docs = {
            "api_docs": f"https://api.{opp.platform}.com/docs",
            "examples": [],
            "best_practices": [],
        }
        if opp.type == OpportunityType.DEV_BOUNTY:
            docs["examples"] = ["similar_pr_1.py", "similar_pr_2.py"]
            docs["best_practices"] = ["Follow repo style", "Write tests", "Update docs"]
        return docs

    async def _analyze_datasets(self, opp: Opportunity) -> dict[str, Any]:
        return {
            "similar_completed": opp.metadata.get("similar_count", 0),
            "avg_reward": opp.metadata.get("avg_reward", opp.reward),
            "avg_time": opp.metadata.get("avg_time", opp.estimated_hours),
            "success_rate": opp.metadata.get("success_rate", opp.confidence),
            "common_pitfalls": ["Incomplete requirements", "Scope creep", "Review delays"],
        }

    async def _generate_structure(self, opp: Opportunity) -> dict[str, Any]:
        structure = {
            "repo_layout": "standard",
            "entry_points": [],
            "test_structure": "pytest",
            "ci_config": "github_actions",
        }
        if opp.type == OpportunityType.DEV_BOUNTY:
            structure["entry_points"] = ["main.py", "cli.py", "handler.py"]
            structure["files_to_modify"] = opp.metadata.get("affected_files", [])
        return structure

    async def _prepare_code(self, opp: Opportunity) -> dict[str, Any]:
        skeleton = {
            "boilerplate": "",
            "interfaces": [],
            "stubs": [],
            "tests": [],
        }
        if opp.type == OpportunityType.DEV_BOUNTY:
            skeleton["boilerplate"] = f"# Solution for: {opp.title}\n# Platform: {opp.platform}\n"
            skeleton["interfaces"] = ["class Solution:", "    def solve(self) -> Result:"]
            skeleton["stubs"] = ["def helper1(): pass", "def helper2(): pass"]
            skeleton["tests"] = ["def test_solution(): assert Solution().solve() == expected"]
        return skeleton

    async def _create_drafts(self, opp: Opportunity) -> dict[str, Any]:
        return {
            "submission_draft": f"## Solution for {opp.title}\n\n### Approach\n\n### Implementation\n\n### Testing\n",
            "pr_description": f"Fixes: {opp.title}\n\n## Changes\n- \n\n## Testing\n- \n",
            "report_outline": f"# Report: {opp.title}\n\n## Executive Summary\n\n## Technical Details\n\n## Impact\n\n## Evidence\n",
        }

    async def _identify_gaps(self, opp: Opportunity) -> list[str]:
        gaps = []
        if not opp.metadata.get("requirements_clear", True):
            gaps.append("Clarify requirements with stakeholder")
        if not opp.metadata.get("access_granted", True):
            gaps.append("Request repository/environment access")
        if opp.type == OpportunityType.DEV_BOUNTY and not opp.metadata.get("test_env_ready", True):
            gaps.append("Set up test environment")
        if opp.reward == 0:
            gaps.append("Confirm payout amount and terms")
        return gaps


class OpportunityEngine:
    def __init__(self, decision_mode: DecisionMode = DecisionMode.EXPLANATORY) -> None:
        self.scorer = OpportunityScorer()
        self.preparator = OpportunityPreparator(decision_mode)
        self.decision_mode = decision_mode
        self.opportunities: dict[str, Opportunity] = {}

    async def ingest(self, raw_opportunities: list[dict[str, Any]]) -> list[Opportunity]:
        for raw in raw_opportunities:
            opp = Opportunity(
                id=raw.get("id", f"opp_{len(self.opportunities)}"),
                type=OpportunityType(raw.get("type", "dev_bounty")),
                title=raw.get("title", "Untitled"),
                description=raw.get("description", ""),
                source=raw.get("source", "unknown"),
                url=raw.get("url"),
                reward=raw.get("reward", 0.0),
                difficulty=raw.get("difficulty", 0.5),
                confidence=raw.get("confidence", 0.5),
                estimated_hours=raw.get("estimated_hours", 2.0),
                skills_required=raw.get("skills", []),
                platform=raw.get("platform", ""),
                metadata=raw.get("metadata", {}),
                decision=self.decision_mode,
            )
            opp.metrics = self.scorer.calculate_metrics(opp)
            self.opportunities[opp.id] = opp

        return list(self.opportunities.values())

    async def rank_and_decide(self, auto_prepare: bool = True) -> list[dict[str, Any]]:
        sorted_opps = sorted(self.opportunities.values(), key=lambda o: o.score, reverse=True)

        results = []
        for opp in sorted_opps:
            if auto_prepare and opp.score >= 0.50 and opp.preparation_status == PreparationStatus.PENDING:
                await self.preparator.prepare(opp)
            results.append(opp.to_decision_dict())

        return results

    def get_by_id(self, opp_id: str) -> Opportunity | None:
        return self.opportunities.get(opp_id)

    def get_top(self, n: int = 5) -> list[Opportunity]:
        return sorted(self.opportunities.values(), key=lambda o: o.score, reverse=True)[:n]

    def record_result(self, opp_id: str, success: bool, actual_value: float, actual_hours: float) -> None:
        self.scorer.record_outcome(opp_id, success, actual_value, actual_hours)
        if opp_id in self.opportunities:
            self.opportunities[opp_id].metrics = self.scorer.calculate_metrics(self.opportunities[opp_id])

    def set_mode(self, mode: DecisionMode) -> None:
        self.decision_mode = mode
        self.preparator.decision_mode = mode
        for opp in self.opportunities.values():
            opp.decision = mode


_ENGINE: OpportunityEngine | None = None


def get_engine(decision_mode: DecisionMode = DecisionMode.EXPLANATORY) -> OpportunityEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = OpportunityEngine(decision_mode)
    return _ENGINE


# =============================================================================
# OpportunityOrchestrator - FORGE/PULSE cycle execution (adapters + executors + autonomous agents)
# =============================================================================


class OpportunityOrchestrator:
    """Orquesta la discovery, ejecución y workflow autónomo para ciclos FORGE y PULSE.

    Integra adaptadores, ejecutores y agentes autónomos en un único punto de entrada.

    Modo Mercenario Técnico:
    - NO busca empleo ("contratame")
    - SÍ busca valor intercambiable por dinero ("resolver problema público → monetizar")
    - Filtro agresivo: SCORE > 80/100 para pasar
    """

    def __init__(self, mercenary_mode: bool = True) -> None:
        self.mercenary_mode = mercenary_mode
        from core.opportunity.mercenary_filter import get_mercenary_filter

        self.mercenary_filter = get_mercenary_filter()

        # Inicializar adaptadores for each cycle
        from core.opportunity.adapters.forge_legacy import (
            AlgoraAdapter,
            OpireAdapter,
            SuperteamAdapter,
        )
        from core.opportunity.adapters.issuehunt import IssueHuntAdapter
        from core.opportunity.adapters.linkedin import LinkedInEasyApplyAdapter
        from core.opportunity.adapters.pulse import (
            DataAnnotationAdapter,
            MindriftAdapter,
            OutlierAdapter,
            RemotasksAdapter,
        )
        from core.opportunity.adapters.security_bounty import (
            BugcrowdAdapter,
            HackerOneAdapter,
            IntigritiAdapter,
            YesWeHackAdapter,
        )

        self.forge_adapters = [
            SuperteamAdapter(),
            OpireAdapter(),
            AlgoraAdapter(),
            IssueHuntAdapter(),
        ]
        self.security_adapters = [
            HackerOneAdapter(),
            BugcrowdAdapter(),
            IntigritiAdapter(),
            YesWeHackAdapter(),
        ]
        self.pulse_adapters = [
            OutlierAdapter(),
            DataAnnotationAdapter(),
            MindriftAdapter(),
            RemotasksAdapter(),
            LinkedInEasyApplyAdapter(),
        ]

        # Inicializar ejecutores
        from core.opportunity.executors import BaseExecutor
        from core.opportunity.executors.algora_executor import AlgoraExecutor
        from core.opportunity.executors.freelancer_executor import FreelancerExecutor
        from core.opportunity.executors.issuehunt_executor import IssueHuntExecutor
        from core.opportunity.executors.mindrift_executor import MindriftExecutor
        from core.opportunity.executors.opire_executor import OpireExecutor

        self.forge_executors: dict[str, BaseExecutor] = {
            "freelancer": FreelancerExecutor(),
            "algora": AlgoraExecutor(),
            "opire": OpireExecutor(),
            "issuehunt": IssueHuntExecutor(),
        }
        self.pulse_executors: dict[str, BaseExecutor] = {
            "mindrift": MindriftExecutor(),
        }

        # Inicializar agentes autónomos
        from core.automation.browser_agent import BrowserAgent
        from core.autonomy.coder_agent import CoderAgent
        from core.autonomy.workflow_engine import AutonomousWorkflow

        self.browser_agent = BrowserAgent()
        self.workflow_engine = AutonomousWorkflow()
        self.coder_agent = CoderAgent()

    async def _execute_cycle_impl(self, cycle: str, limit: int = 10) -> list[dict[str, Any]]:
        """Execute a full cycle (forge or pulse) with discovery → claim → resolve → deliver."""
        return await self.execute_cycle_original(cycle, limit)

    async def execute_cycle_original(self, cycle: str, limit: int = 10) -> list[dict[str, Any]]:
        """Original execute_cycle body - discovery → claim → resolve → deliver."""
        # 1. Descubrir oportunidades usando adaptadores
        adapters = self.forge_adapters if cycle == "forge" else self.pulse_adapters
        raw_opps: list[dict[str, Any]] = []
        for adapter in adapters:
            try:
                opps = await adapter.fetch_opportunities()
                raw_opps.extend(opps)
            except Exception as e:
                import logging

                logging.getLogger("ownex.orchestrator").error(f"Adapter {adapter.platform} fetch failed: {e}")

        # 2. Priorizar usando el engine de scoring (TargetPrioritizer)
        from core.opportunity.tasks import prioritize_targets

        prioritized = await prioritize_targets(raw_opps, cycle=cycle)

        # 3. Ranking accionable — SIN auto-ejecución.
        # La orquestación v5.0.0 (claim→resolve→deliver vía _process_opportunity)
        # se perdió en el churn del árbol core/ y los executors siguen dormidos
        # sin credenciales (PLATFORM_ACCESS); además toda entrega exige
        # aprobación humana. El ciclo produce el RANKING; la ejecución fluye
        # por el Work Bank (prepare → human review).
        execution_disabled_reason = (
            "autonomous execution disabled: platform credentials not configured "
            "(see PLATFORM_ACCESS) and delivery requires human approval"
        )
        results: list[dict[str, Any]] = []
        for rank, opp in enumerate(prioritized[:limit], start=1):
            item = dict(opp)
            item["cycle"] = cycle
            item["rank"] = rank
            item["action_required"] = "human_review"
            item["execution_disabled_reason"] = execution_disabled_reason
            results.append(item)

        return results

    @classmethod
    async def execute_cycle(cls, cycle: str = "forge", limit: int = 10) -> list[dict[str, Any]]:
        """Classmethod entry point for the scheduler.

        Creates an instance and calls the instance method.
        Handler reference: ``core.opportunity.engine:OpportunityOrchestrator.execute_cycle``
        """
        orchestrator = cls()
        return await orchestrator._execute_cycle_impl(cycle, limit)
