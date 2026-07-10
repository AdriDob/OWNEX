"""Planner — proposes action plans, not just single recommendations."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from core.copilot.context import CopilotContext

logger = logging.getLogger("orion.core.copilot.planner")


class PlanStep:
    """A single step in a plan."""

    def __init__(
        self,
        action: str,
        description: str,
        tool: str = "",
        params: dict[str, Any] | None = None,
        risk: float = 0.0,
    ) -> None:
        self.id = uuid.uuid4().hex[:8]
        self.action = action
        self.description = description
        self.tool = tool
        self.params = params or {}
        self.risk = risk
        self.status = "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "description": self.description,
            "tool": self.tool,
            "params": self.params,
            "risk": self.risk,
            "status": self.status,
        }


class Plan:
    """A multi-step action plan."""

    def __init__(self, context: CopilotContext) -> None:
        self.id = uuid.uuid4().hex[:12]
        self.context = context
        self.steps: list[PlanStep] = []
        self.created_at = datetime.now(timezone.utc)
        self.status = "draft"

    def add_step(self, step: PlanStep) -> None:
        self.steps.append(step)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "app_id": self.context.app_id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "steps": [s.to_dict() for s in self.steps],
            "total_steps": len(self.steps),
            "avg_risk": sum(s.risk for s in self.steps) / max(len(self.steps), 1),
        }


class Planner:
    """Action planner that proposes multi-step investigation plans."""

    def create_plan(self, context: CopilotContext) -> Plan:
        """Create an investigation plan based on context."""
        plan = Plan(context)

        finding = context.finding or {}
        finding_type = (finding.get("vulnerability_type") or finding.get("type") or "").lower()

        if "idor" in finding_type:
            self._plan_idor_investigation(plan, finding)
        elif "ssrf" in finding_type:
            self._plan_ssrf_investigation(plan, finding)
        elif "xss" in finding_type:
            self._plan_xss_investigation(plan, finding)
        elif "sql" in finding_type or "injection" in finding_type:
            self._plan_sqli_investigation(plan, finding)
        elif "auth" in finding_type or "bypass" in finding_type:
            self._plan_auth_bypass_investigation(plan, finding)
        else:
            self._plan_generic_investigation(plan, finding)

        plan.status = "pending"
        return plan

    def _plan_idor_investigation(self, plan: Plan, finding: dict[str, Any]) -> None:
        plan.add_step(
            PlanStep(
                "verify_ownership",
                "Verificar que el recurso pertenece a otro usuario",
                "http",
                {"method": "GET", "check": "ownership"},
                risk=0.3,
            )
        )
        plan.add_step(
            PlanStep(
                "compare_responses",
                "Comparar respuesta autenticada vs. no autenticada",
                "http",
                {"method": "GET", "check": "comparison"},
                risk=0.4,
            )
        )
        plan.add_step(
            PlanStep(
                "check_referer",
                "Revisar endpoints relacionados con el mismo patrón",
                "scan",
                {"type": "related_endpoints"},
                risk=0.2,
            )
        )
        plan.add_step(
            PlanStep(
                "secondary_hypothesis",
                "Ejecutar hipótesis secundaria (IDOR en parámetro alternativo)",
                "http",
                {"method": "GET", "parameter": "alternate_id"},
                risk=0.5,
            )
        )

    def _plan_ssrf_investigation(self, plan: Plan, finding: dict[str, Any]) -> None:
        plan.add_step(
            PlanStep(
                "verify_external_interaction",
                "Verificar interacción con servidor externo controlado",
                "http",
                {"method": "GET", "check": "external_interaction"},
                risk=0.3,
            )
        )
        plan.add_step(
            PlanStep(
                "check_internal_ports",
                "Escanear puertos internos accesibles",
                "scan",
                {"type": "port_scan", "target": "internal"},
                risk=0.6,
            )
        )
        plan.add_step(
            PlanStep(
                "check_cloud_metadata",
                "Verificar acceso a metadata cloud (AWS/GCP/Azure)",
                "http",
                {"method": "GET", "target": "cloud_metadata"},
                risk=0.7,
            )
        )

    def _plan_xss_investigation(self, plan: Plan, finding: dict[str, Any]) -> None:
        plan.add_step(
            PlanStep(
                "verify_reflection",
                "Verificar que el payload se refleja en la respuesta",
                "http",
                {"method": "GET", "check": "reflection"},
                risk=0.3,
            )
        )
        plan.add_step(
            PlanStep(
                "check_context",
                "Analizar contexto de salida (HTML/JS/Attribute)",
                "analyze",
                {"type": "context_analysis"},
                risk=0.2,
            )
        )
        plan.add_step(
            PlanStep(
                "test_bypass",
                "Probar bypass de filtros (encoding, tags alternativos)",
                "http",
                {"method": "GET", "check": "bypass"},
                risk=0.5,
            )
        )

    def _plan_sqli_investigation(self, plan: Plan, finding: dict[str, Any]) -> None:
        plan.add_step(
            PlanStep(
                "verify_timing",
                "Verificar inyección basada en tiempo",
                "http",
                {"method": "GET", "check": "timing"},
                risk=0.3,
            )
        )
        plan.add_step(
            PlanStep(
                "verify_error",
                "Verificar inyección basada en errores",
                "http",
                {"method": "GET", "check": "error_based"},
                risk=0.4,
            )
        )
        plan.add_step(
            PlanStep(
                "extract_data",
                "Intentar extraer datos (versión DB, tablas)",
                "http",
                {"method": "GET", "check": "data_extraction"},
                risk=0.7,
            )
        )

    def _plan_auth_bypass_investigation(self, plan: Plan, finding: dict[str, Any]) -> None:
        plan.add_step(
            PlanStep(
                "verify_bypass",
                "Verificar que el bypass funciona sin credenciales",
                "http",
                {"method": "GET", "check": "no_auth_access"},
                risk=0.4,
            )
        )
        plan.add_step(
            PlanStep(
                "check_role_escalation",
                "Verificar escalación de rol (user→admin)",
                "http",
                {"method": "GET", "check": "role_escalation"},
                risk=0.6,
            )
        )
        plan.add_step(
            PlanStep(
                "check_mfa_bypass",
                "Verificar si el bypass salta MFA",
                "http",
                {"method": "GET", "check": "mfa_bypass"},
                risk=0.5,
            )
        )

    def _plan_generic_investigation(self, plan: Plan, finding: dict[str, Any]) -> None:
        plan.add_step(
            PlanStep(
                "verify_reproducibility",
                "Reproducir el hallazgo",
                "http",
                {"method": "GET"},
                risk=0.3,
            )
        )
        plan.add_step(
            PlanStep(
                "check_impact",
                "Evaluar impacto real",
                "analyze",
                {"type": "impact_assessment"},
                risk=0.4,
            )
        )
        plan.add_step(
            PlanStep(
                "secondary_hypothesis",
                "Ejecutar hipótesis secundaria",
                "analyze",
                {"type": "secondary_hypothesis"},
                risk=0.5,
            )
        )
