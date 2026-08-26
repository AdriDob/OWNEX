"""Capital Allocation Engine — recommends how to allocate available capital."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("ownex.capital.allocation")


@dataclass
class AllocationRecommendation:
    action: str
    priority: str  # high, medium, low
    rationale: str
    amount: float = 0.0
    expected_impact: float = 0.0
    risk: str = "medium"
    confidence: float = 0.5


@dataclass
class AllocationPlan:
    primary_recommendation: dict[str, Any] | None = None
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    total_allocated: float = 0.0
    remaining_cash: float = 0.0
    rationale: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class AllocationEngine:
    """Recommends how to allocate available capital across strategies."""

    def __init__(self) -> None:
        self._rules = [
            # (condition_fn, action, priority, rationale)
            (
                lambda ctx: ctx.runway_months < 1,
                "build_emergency_reserve",
                "high",
                "Runway crítico (<1 mes): priorizar reserva de emergencia",
            ),
            (
                lambda ctx: ctx.runway_months < 3,
                "reduce_discretionary_burn",
                "high",
                "Runway bajo (<3 meses): recortar gasto discrecional",
            ),
            (
                lambda ctx: ctx.income_concentration > 60,
                "diversify_income",
                "high",
                "Concentración de ingresos >60%: diversificar fuentes",
            ),
            (
                lambda ctx: ctx.crypto_exposure > 30,
                "reduce_crypto_exposure",
                "medium",
                "Exposición crypto >30%: reducir riesgo",
            ),
            (
                lambda ctx: ctx.high_interest_debt > 0,
                "pay_high_interest_debt",
                "high",
                "Deuda alto interés: priorizar pago",
            ),
            (
                lambda ctx: ctx.available_cash > 10000,
                "invest_surplus",
                "medium",
                "Excedente >$10k: invertir en estrategias productivas",
            ),
            (
                lambda ctx: ctx.available_cash > 5000,
                "build_opportunity_fund",
                "medium",
                "Excedente >$5k: crear fondo de oportunidades",
            ),
            (lambda ctx: True, "maintain_cash_buffer", "low", "Mantener buffer de efectivo para oportunidades"),
        ]

    def recommend_allocation(
        self,
        available_capital: float = 0,
        runway_months: float = float("inf"),
        risk_tolerance: str = "moderate",
        income_stability: str = "moderate",
        goals: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate capital allocation recommendations."""
        context = context or {}
        goals = goals or []

        # Build context
        ctx = {
            "available_cash": available_capital,
            "runway_months": runway_months,
            "risk_tolerance": risk_tolerance,
            "income_stability": income_stability,
            "goals": goals,
            **context,
        }

        # Calculate metrics
        ctx["runway_months"] = runway_months
        ctx["income_concentration"] = self._calculate_income_concentration(context)
        ctx["crypto_exposure"] = self._calculate_crypto_exposure(context)
        ctx["high_interest_debt"] = self._get_high_interest_debt(context)
        ctx["available_cash"] = available_capital

        # Apply rules
        recommendations = []
        for condition, action, priority, rationale in self._rules:
            try:
                if condition(ctx):
                    rec = self._create_recommendation(action, priority, rationale, ctx)
                    if rec:
                        recommendations.append(rec)
            except Exception as e:
                logger.warning(f"Rule {action} failed: {e}")

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda r: priority_order.get(r["priority"], 3))

        # Primary recommendation
        primary = recommendations[0] if recommendations else None

        # Calculate totals
        total_allocated = sum(r.get("amount", 0) for r in recommendations)
        remaining = max(0, available_capital - total_allocated)

        return {
            "primary_recommendation": primary,
            "recommendations": recommendations,
            "total_allocated": round(total_allocated, 2),
            "remaining_cash": round(remaining, 2),
            "rationale": f"Basado en {len(recommendations)} reglas evaluadas con tolerancia {risk_tolerance}",
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def _calculate_income_concentration(self, context: dict) -> float:
        """Calculate income concentration (top source %)."""
        # Would use income_sources from context
        return context.get("income_concentration", 0)

    def _calculate_crypto_exposure(self, context: dict) -> float:
        return context.get("crypto_exposure", 0)

    def _get_high_interest_debt(self, context: dict) -> float:
        return context.get("high_interest_debt", 0)

    def _create_recommendation(self, action: str, priority: str, rationale: str, ctx: dict) -> dict | None:
        """Create a recommendation based on action type."""
        recommendations_map = {
            "build_emergency_reserve": {
                "action": "Crear reserva de emergencia",
                "amount": min(ctx.get("available_cash", 0) * 0.5, 5000),
                "expected_impact": 0,
                "risk": "low",
                "confidence": 0.95,
            },
            "reduce_discretionary_burn": {
                "action": "Recortar gasto discrecional",
                "amount": 0,
                "expected_impact": ctx.get("discretionary_burn", 0) * 0.3,
                "risk": "low",
                "confidence": 0.9,
            },
            "diversify_income": {
                "action": "Diversificar fuentes de ingreso",
                "amount": 0,
                "expected_impact": 0,
                "risk": "low",
                "confidence": 0.8,
            },
            "reduce_crypto_exposure": {
                "action": "Reducir exposición crypto",
                "amount": 0,
                "expected_impact": 0,
                "risk": "medium",
                "confidence": 0.85,
            },
            "pay_high_interest_debt": {
                "action": "Pagar deuda de alto interés",
                "amount": min(ctx.get("high_interest_debt", 0), ctx.get("available_cash", 0) * 0.8),
                "expected_impact": ctx.get("high_interest_debt", 0) * 0.2,
                "risk": "low",
                "confidence": 0.95,
            },
            "invest_surplus": {
                "action": "Invertir excedente en estrategias productivas",
                "amount": max(0, ctx.get("available_cash", 0) - 5000),
                "expected_impact": (ctx.get("available_cash", 0) - 5000) * 0.1,
                "risk": "medium",
                "confidence": 0.7,
            },
            "build_opportunity_fund": {
                "action": "Crear fondo de oportunidades",
                "amount": min(ctx.get("available_cash", 0) * 0.3, 3000),
                "expected_impact": 0,
                "risk": "low",
                "confidence": 0.75,
            },
            "maintain_cash_buffer": {
                "action": "Mantener buffer de efectivo",
                "amount": 0,
                "expected_impact": 0,
                "risk": "low",
                "confidence": 0.8,
            },
        }

        base = recommendations_map.get(action)
        if not base:
            return None

        return {
            "action": base["action"],
            "priority": priority,
            "rationale": rationale,
            "amount": round(base.get("amount", 0), 2),
            "expected_impact": round(base.get("expected_impact", 0), 2),
            "risk": base.get("risk", "medium"),
            "confidence": base.get("confidence", 0.5),
        }


_allocation_engine: AllocationEngine | None = None


def get_allocation_engine() -> AllocationEngine:
    global _allocation_engine
    if _allocation_engine is None:
        _allocation_engine = AllocationEngine()
    return _allocation_engine
