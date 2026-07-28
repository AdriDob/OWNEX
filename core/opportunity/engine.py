from __future__ import annotations

from typing import Any

from core.automation.browser_agent import BrowserAgent
from core.autonomy.coder_agent import CoderAgent
from core.autonomy.workflow_engine import AutonomousWorkflow
from core.opportunity.adapters.forge_legacy import (
    AlgoraAdapter,
    OpireAdapter,
    SuperteamAdapter,
)
from core.opportunity.adapters.issuehunt import IssueHuntAdapter
from core.opportunity.adapters.linkedin import LinkedInEasyApplyAdapter
from core.opportunity.adapters.pulse import DataAnnotationAdapter, MindriftAdapter, OutlierAdapter, RemotasksAdapter
from core.opportunity.executors import BaseExecutor
from core.opportunity.executors.algora_executor import AlgoraExecutor
from core.opportunity.executors.freelancer_executor import FreelancerExecutor
from core.opportunity.executors.issuehunt_executor import IssueHuntExecutor
from core.opportunity.executors.mindrift_executor import MindriftExecutor
from core.opportunity.executors.opire_executor import OpireExecutor


class OpportunityOrchestrator:
    """Orquesta la discovery, ejecución y workflow autónomo para ciclos FORGE y PULSE.

    Integra adaptadores, ejecutores y agentes autónomos en un único punto de entrada.
    """

    def __init__(self) -> None:
        # Inicializar adaptadores for each cycle
        self.forge_adapters = [SuperteamAdapter(), OpireAdapter(), AlgoraAdapter(), IssueHuntAdapter()]
        self.pulse_adapters = [
            OutlierAdapter(),
            DataAnnotationAdapter(),
            MindriftAdapter(),
            RemotasksAdapter(),
            LinkedInEasyApplyAdapter(),
        ]

        # Inicializar ejecutores
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
        self.browser_agent = BrowserAgent()
        self.workflow_engine = AutonomousWorkflow()
        self.coder_agent = CoderAgent()

    async def _execute_cycle_instance(self, cycle: str, limit: int = 10) -> list[dict[str, Any]]:
        """Original execute_cycle instance method - renamed to avoid classmethod clash."""
        # 1. Descubrir oportunidades usando adaptadores
        adapters = self.forge_adapters if cycle == "forge" else self.pulse_adapters
        raw_opps: list[dict[str, Any]] = []
        for adapter in adapters:
            try:
                # fetch_opportunities ya puede incluir credential validation
                opps = await adapter.fetch_opportunities()
                raw_opps.extend(opps)
            except Exception as e:
                # log error but continue
                import logging

                logging.getLogger("ownex.orchestrator").error(f"Adapter {adapter.platform} fetch failed: {e}")

        # 2. Priorizar usando el engine de scoring (TargetPrioritizer)
        from core.opportunity.tasks import prioritize_targets

        prioritized = await prioritize_targets(raw_opps, cycle=cycle)

        # 3. Procesar top-N oportunidades con workflow autónomo
        results: list[dict[str, Any]] = []
        for opp in prioritized[:limit]:
            opp_result = await self._process_opportunity(opp, cycle)
            results.append(opp_result)

        return results

    async def _process_opportunity(self, opportunity: dict[str, Any], cycle: str) -> dict[str, Any]:
        """Claim + resolver + entregar una única oportunidad usando adaptadores+ejecutores+agentes.

        Flujo for Forge:
          - Claim usando executor (Freelancer, Algora, Opire, IssueHunt)
          - Si claim exitoso, invocar CoderAgent para resolver problemas técnicos
          - Ejecutar workflow con CoderAgent → generar fix → tests → PR → submit

        Flujo for Pulse:
          - Claim usando browser_agent si necesario (LinkedIn, DataAnnotation, Outlier, Mindrift, Remotasks)
          - Resolver tarea (a través de plataforma específica o CoderAgent para código)
          - Submission final de entrega vía executor o browser
        """
        platform = opportunity.get("platform")
        reward = opportunity.get("reward", 0)
        effort_hours = opportunity.get("effort_hours", 4)
        source = opportunity.get("source_name", "")

        # Seleccionar ejecutor apropiado
        executor: BaseExecutor | None = None
        if cycle == "forge":
            for exe_name, exe in self.forge_executors.items():
                if exe_name in (platform, source):
                    executor = exe
                    break
        else:
            # Use browser_agent for many PULSE platforms (may need platform-specific logic)
            if platform in ("linkedin", "dataannotation", "outlier", "remotasks", "mindrift"):
                executor = self.browser_agent
            else:
                # Fallback a executores estándar
                for exe_name, exe in self.pulse_executors.items():
                    if exe_name == platform:
                        executor = exe
                        break

        # 2. CLAIM (si hay ejecutor)
        claim_result: dict[str, Any] = {"success": False, "error": "No claim executor configured"}
        if executor:
            try:
                # Usar método claim estándar basado en plataforma
                if hasattr(executor, "claim_bounty"):
                    claim_result = await executor.claim_bounty(opportunity.get("id", ""))
                elif hasattr(executor, "claim_issue"):
                    claim_result = await executor.claim_issue(opportunity.get("url", ""))
                elif hasattr(executor, "claim_task"):
                    claim_result = await executor.claim_task(opportunity.get("id", ""))
                elif hasattr(executor, "claim_bounty"):
                    claim_result = await executor.claim_bounty(opportunity.get("id", ""))
            except Exception as e:
                claim_result["error"] = str(e)

        # 3. RESOLVER (CoderAgent para trabajo técnico, browser_agent para aplicación)
        resolution_result: dict[str, Any] = {"success": False, "steps": []}
        if cycle == "forge" and claim_result.get("success"):
            # Invocar CoderAgent para resolver problemas técnicos (issues, avances, PRs)
            try:
                coder_result = await self.coder_agent.solve_github_issue(
                    repo_url=opportunity.get("repo_url", ""),
                    issue_description=opportunity.get("description", ""),
                    reward=float(reward),
                )
                resolution_result.update(coder_result)
            except Exception as e:
                resolution_result["error"] = str(e)

        elif cycle == "pulse" and claim_result.get("success"):
            # Resolver tarea de datos/trabajo específico de la plataforma
            try:
                if platform == "linkedin":
                    # Easy apply para LinkedIn
                    browser_result = await self.browser_agent.easy_apply_linkedin(opportunity)
                    resolution_result.update(browser_result)
                elif platform == "outlier":
                    task_result = await self.browser_agent.claim_and_solve_outlier(opportunity)
                    resolution_result.update(task_result)
                elif platform == "dataannotation":
                    task_result = await self.browser_agent.claim_and_solve_dataannotation(opportunity)
                    resolution_result.update(task_result)
            except Exception as e:
                resolution_result["error"] = str(e)

        # 4. ENTREGAR (submit vía executor o browser)
        delivery_result: dict[str, Any] = {"success": False, "error": "No delivery executor configured"}
        if claim_result.get("success"):
            try:
                if hasattr(executor, "submit_work"):
                    delivery_result = await executor.submit_work(
                        opportunity.get("id", ""),
                        pr_url=opportunity.get("pr_url", ""),
                        description="Automatic submission via OWNEX",
                    )
                elif hasattr(executor, "submit_pr"):
                    delivery_result = await executor.submit_pr(
                        opportunity.get("url", ""), pr_url=opportunity.get("pr_url", "")
                    )
                elif hasattr(executor, "submit_task"):
                    delivery_result = await executor.submit_task(
                        opportunity.get("id", ""),
                        solution_url=opportunity.get("solution_url", ""),
                        description="Automatic submission via OWNEX",
                    )
            except Exception as e:
                delivery_result["error"] = str(e)

        # 5. Calcular métricas finales
        score = 0.0
        if claim_result.get("success"):
            score += 33.33
        if resolution_result.get("success"):
            score += 33.33
        if delivery_result.get("success"):
            score += 33.33

        return {
            "platform": platform,
            "reward": reward,
            "effort_hours": effort_hours,
            "claim": claim_result,
            "resolution": resolution_result,
            "delivery": delivery_result,
            "score": round(score, 2),
            "revenue_potential": reward if delivery_result.get("success") else 0.0,
        }

    @classmethod
    async def execute_cycle(cls, cycle: str = "forge", limit: int = 10) -> list[dict[str, Any]]:
        """Classmethod entry point for the scheduler.

        Creates an instance and calls the instance method.
        Handler reference: ``core.opportunity.engine:OpportunityOrchestrator.execute_cycle``
        """
        orchestrator = cls()
        return await orchestrator._execute_cycle_impl(cycle, limit)

    async def _execute_cycle_impl(self, cycle: str, limit: int = 10) -> list[dict[str, Any]]:
        """Execute a full cycle (forge or pulse) with discovery → claim → resolve → deliver."""
        # We need to rename the original execute_cycle to make room for the classmethod.
        # call the old body logic via delegation
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

        # 2. Priorizar usando el engine de scoring
        from core.opportunity.tasks import prioritize_targets

        prioritized = await prioritize_targets(raw_opps, cycle=cycle)

        # 3. Procesar top-N oportunidades con workflow autónomo
        results: list[dict[str, Any]] = []
        for opp in prioritized[:limit]:
            opp_result = await self._process_opportunity(opp, cycle)
            results.append(opp_result)

        return results

    async def health_check(self) -> dict[str, Any]:
        """Check health de todos los componentes."""
        results: dict[str, Any] = {"status": "healthy", "components": []}

        # Health de adaptadores
        for adapter_list, _ in [(self.forge_adapters, "forge_adapters"), (self.pulse_adapters, "pulse_adapters")]:
            for adapter in adapter_list:
                try:
                    if hasattr(adapter, "health_check"):
                        check = await adapter.health_check()
                        results["components"].append(
                            {
                                "type": "adapter",
                                "platform": adapter.platform,
                                "status": "ok" if check.get("success") else "error",
                                "details": check,
                            }
                        )
                except Exception as e:
                    results["components"].append(
                        {
                            "type": "adapter",
                            "platform": getattr(adapter, "platform", "unknown"),
                            "status": "error",
                            "details": str(e),
                        }
                    )

        # Health de ejecutores
        for _exe_name, exe in self.forge_executors.items():
            try:
                check = await exe.health_check()
                results["components"].append(
                    {
                        "type": "executor",
                        "platform": exe.platform,
                        "status": "ok" if check.get("success") else "error",
                        "details": check,
                    }
                )
            except Exception as e:
                results["components"].append(
                    {
                        "type": "executor",
                        "platform": getattr(exe, "platform", "unknown"),
                        "status": "error",
                        "details": str(e),
                    }
                )

        for _exe_name, exe in self.pulse_executors.items():
            try:
                check = await exe.health_check()
                results["components"].append(
                    {
                        "type": "executor",
                        "platform": exe.platform,
                        "status": "ok" if check.get("success") else "error",
                        "details": check,
                    }
                )
            except Exception as e:
                results["components"].append(
                    {
                        "type": "executor",
                        "platform": getattr(exe, "platform", "unknown"),
                        "status": "error",
                        "details": str(e),
                    }
                )

        # BrowserAgent y workflow engine
        for agent, label in [
            (self.browser_agent, "browser_agent"),
            (self.workflow_engine, "workflow_engine"),
            (self.coder_agent, "coder_agent"),
        ]:
            try:
                if hasattr(agent, "health_check"):
                    check = await agent.health_check()
                    results["components"].append(
                        {"type": label, "status": "ok" if check.get("success") else "error", "details": check}
                    )
            except Exception as e:
                results["components"].append({"type": label, "status": "error", "details": str(e)})

        # Verificar operación normal
        return results
