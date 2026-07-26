"""
Unified Expected Value Engine — calcula EV/hora para CUALQUIER actividad.

Unifica la lógica de TargetPrioritizer (bug bounty) con decisiones de inversión,
finanzas personales, y trabajo general.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("orion.scheduler.ev_engine")


@dataclass
class EVInput:
    """Inputs para cálculo de EV unificado."""
    # ── Financieros directos ─────────────────────────────────────
    expected_revenue: float = 0.0           # Ingreso esperado si tiene éxito
    probability_success: float = 0.5        # 0-1, probabilidad de éxito
    time_investment_hours: float = 1.0      # Horas que requiere

    # ── Costes y riesgos ────────────────────────────────────────
    risk_level: float = 0.3                 # 0-1, riesgo de pérdida/fracaso
    opportunity_cost: float = 0.0           # EV/hora de la mejor alternativa
    upfront_cost: float = 0.0               # Coste inicial (tools, fees, etc.)

    # ── Valor estratégico / aprendizaje ─────────────────────────
    skill_value: float = 0.0                # Valor de aprendizaje futuro ($/hora equivalente)
    network_value: float = 0.0              # Contactos, reputación ($ equivalente)
    strategic_alignment: float = 0.5        # 0-1, alineación con metas a largo plazo

    # ── Contexto ────────────────────────────────────────────────
    domain: str = "general"                 # bug_bounty, investment, freelance, etc.
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EVResult:
    """Resultado del cálculo de EV."""
    ev_per_hour: float                      # EV neto por hora
    total_ev: float                         # EV total de la actividad
    breakdown: dict[str, float]             # Desglose por componente
    confidence: float                       # 0-1, confianza en la estimación
    recommendation: str                     # "do_now", "schedule", "delegate", "drop", "invest_more"
    rationale: str                          # Explicación legible


class EVCalculator:
    """
    Calculadora de Expected Value unificada.

    Fórmula:
    EV = (Financial_EV × W_fin) + (Risk_Adjusted × W_risk) + (Learning × W_learn)
         + (Network × W_net) + (Strategic × W_strat) - Opportunity_Cost

    Donde:
    - Financial_EV = expected_revenue × probability_success / time_investment_hours
    - Risk_Adjusted = Financial_EV × (1 - risk_level × risk_aversion)
    - Learning/Network/Strategic son bonuses en $/hora equivalentes
    """

    # Pesos por defecto (configurables via settings/memory)
    DEFAULT_WEIGHTS = {
        "financial": 0.50,
        "risk_adjusted": 0.20,
        "learning": 0.15,
        "network": 0.10,
        "strategic": 0.05,
    }

    # Aversión al riesgo (0-1, mayor = más conservador)
    DEFAULT_RISK_AVERSION = 0.5

    # Umbrales de recomendación
    THRESHOLDS = {
        "do_now": 1.5,      # EV > 1.5x opportunity_cost y confidence > 0.7
        "schedule": 1.0,    # EV > opportunity_cost y confidence > 0.5
        "delegate": 0.1,    # EV > 0 pero < opportunity_cost
        "drop": -float("inf"),  # EV <= 0
    }

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        risk_aversion: float | None = None,
    ):
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.risk_aversion = risk_aversion or self.DEFAULT_RISK_AVERSION

        # Normalizar pesos para que sumen 1.0
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}

    def calculate(self, inp: EVInput) -> EVResult:
        """Calcula EV completo para una actividad."""

        # ── 1. Financial EV base ────────────────────────────────
        gross_revenue = inp.expected_revenue * inp.probability_success
        financial_ev_per_hour = gross_revenue / max(inp.time_investment_hours, 0.1)
        financial_ev_total = gross_revenue - inp.upfront_cost

        # ── 2. Risk Adjustment ──────────────────────────────────
        # Kelly-inspired: reduce EV by risk_level * risk_aversion
        risk_multiplier = 1.0 - (inp.risk_level * self.risk_aversion)
        risk_adjusted_per_hour = financial_ev_per_hour * max(risk_multiplier, 0.0)
        risk_adjusted_total = financial_ev_total * max(risk_multiplier, 0.0)

        # ── 3. Strategic Bonuses (en $/hora) ────────────────────
        learning_bonus_per_hour = inp.skill_value * self.weights.get("learning", 0)
        network_bonus_per_hour = inp.network_value * self.weights.get("network", 0)
        strategic_bonus_per_hour = inp.strategic_alignment * 100 * self.weights.get("strategic", 0)
        # 100 = escala base para strategic (100$/hora por alignment=1.0)

        # ── 4. Net EV per hour ──────────────────────────────────
        weighted_financial = financial_ev_per_hour * self.weights.get("financial", 0)
        weighted_risk = risk_adjusted_per_hour * self.weights.get("risk_adjusted", 0)
        weighted_learning = learning_bonus_per_hour
        weighted_network = network_bonus_per_hour
        weighted_strategic = strategic_bonus_per_hour

        ev_per_hour = (
            weighted_financial
            + weighted_risk
            + weighted_learning
            + weighted_network
            + weighted_strategic
            - inp.opportunity_cost  # restar coste de oportunidad al final
        )

        total_ev = ev_per_hour * inp.time_investment_hours

        # ── 5. Confidence ───────────────────────────────────────
        # Basada en: probability_success, inverse risk, data quality
        data_quality = inp.metadata.get("data_quality", 0.5)  # 0-1
        confidence = min(
            inp.probability_success * (1 - inp.risk_level) * (0.5 + 0.5 * data_quality),
            0.95
        )

        # ── 6. Recommendation ───────────────────────────────────
        recommendation, rationale = self._make_recommendation(
            ev_per_hour, inp.opportunity_cost, confidence, inp
        )

        # ── 7. Breakdown ────────────────────────────────────────
        breakdown = {
            "gross_revenue": gross_revenue,
            "financial_ev_per_hour": financial_ev_per_hour,
            "financial_ev_total": financial_ev_total,
            "risk_multiplier": risk_multiplier,
            "risk_adjusted_per_hour": risk_adjusted_per_hour,
            "risk_adjusted_total": risk_adjusted_total,
            "learning_bonus_per_hour": learning_bonus_per_hour,
            "network_bonus_per_hour": network_bonus_per_hour,
            "strategic_bonus_per_hour": strategic_bonus_per_hour,
            "weighted_financial": weighted_financial,
            "weighted_risk": weighted_risk,
            "weighted_learning": weighted_learning,
            "weighted_network": weighted_network,
            "weighted_strategic": weighted_strategic,
            "opportunity_cost": inp.opportunity_cost,
            "ev_per_hour": ev_per_hour,
            "total_ev": total_ev,
        }

        return EVResult(
            ev_per_hour=round(ev_per_hour, 2),
            total_ev=round(total_ev, 2),
            breakdown={k: round(v, 2) for k, v in breakdown.items()},
            confidence=round(confidence, 2),
            recommendation=recommendation,
            rationale=rationale,
        )

    def _make_recommendation(
        self,
        ev_per_hour: float,
        opportunity_cost: float,
        confidence: float,
        inp: EVInput
    ) -> tuple[str, str]:
        """Determina la recomendación basada en EV y confianza."""

        ratio = ev_per_hour / max(opportunity_cost, 0.01) if opportunity_cost > 0 else float("inf")

        if ev_per_hour <= 0:
            return "drop", f"EV negativo ({ev_per_hour:.2f}/h). No vale la pena."

        if ratio >= self.THRESHOLDS["do_now"] and confidence >= 0.7:
            return "do_now", (
                f"EV alto ({ev_per_hour:.2f}/h, {ratio:.1f}x alternativa) "
                f"con confianza {confidence:.0%}. Ejecutar ya."
            )

        if ratio >= self.THRESHOLDS["schedule"] and confidence >= 0.5:
            return "schedule", (
                f"EV positivo ({ev_per_hour:.2f}/h, {ratio:.1f}x alternativa) "
                f"con confianza {confidence:.0%}. Agendar."
            )

        if ratio >= self.THRESHOLDS["delegate"] and confidence >= 0.3:
            return "delegate", (
                f"EV bajo ({ev_per_hour:.2f}/h) pero positivo. "
                f"Considerar delegar o automatizar."
            )

        return "drop", f"EV insuficiente vs alternativa ({ratio:.1f}x). Reevaluar."

    def compare(self, inputs: list[EVInput]) -> list[tuple[EVInput, EVResult]]:
        """Compara múltiples actividades y devuelve ordenadas por EV/hora."""
        results = [(inp, self.calculate(inp)) for inp in inputs]
        results.sort(key=lambda x: x[1].ev_per_hour, reverse=True)
        return results

    def rank_activities(self, activities: list[dict]) -> list[dict]:
        """Rankea actividades desde formato dict (ej. WorkActivity)."""
        inputs = []
        for a in activities:
            inp = EVInput(
                expected_revenue=a.get("revenue_expected", 0),
                probability_success=a.get("probability_success", 0.5),
                time_investment_hours=a.get("hours_estimated", 1),
                risk_level=a.get("risk_level", 0.3),
                opportunity_cost=a.get("opportunity_cost", 0),
                upfront_cost=a.get("upfront_cost", 0),
                skill_value=a.get("skill_value", 0),
                network_value=a.get("network_value", 0),
                strategic_alignment=a.get("strategic_alignment", 0.5),
                domain=a.get("activity_type", "general"),
                tags=a.get("tags", []),
                metadata=a.get("meta", {}),
            )
            inputs.append(inp)

        ranked = self.compare(inputs)
        return [
            {
                **a.__dict__,
                "ev_per_hour": r.ev_per_hour,
                "total_ev": r.total_ev,
                "confidence": r.confidence,
                "recommendation": r.recommendation,
                "rationale": r.rationale,
                "breakdown": r.breakdown,
            }
            for a, r in ranked
        ]


# ── Singleton global ──────────────────────────────────────────────

_ev_calculator: EVCalculator | None = None

def get_ev_calculator() -> EVCalculator:
    global _ev_calculator
    if _ev_calculator is None:
        _ev_calculator = EVCalculator()
    return _ev_calculator


# ── Helpers para dominios específicos ─────────────────────────────

def estimate_bb_success_probability(target_name: str, vuln_type: str, historical_data: dict) -> float:
    """Estima probabilidad de éxito en bug bounty basado en histórico."""
    # TODO: usar RewardLearner + AcceptanceLearner
    base_rates = {
        "idor": 0.35,
        "xss": 0.25,
        "sqli": 0.20,
        "ssrf": 0.30,
        "auth_bypass": 0.40,
    }
    base = base_rates.get(vuln_type, 0.25)

    # Ajustar por target intel
    target_mod = historical_data.get("target_success_rate", 1.0)
    platform_mod = historical_data.get("platform_acceptance", 1.0)

    return min(base * target_mod * platform_mod, 0.9)


def estimate_investment_success(symbol: str, action: str, portfolio_context: dict) -> float:
    """Estima probabilidad de éxito en acción de inversión."""
    # TODO: usar modelos de ATLAS + Riskfolio
    base = {
        "buy": 0.55,
        "sell": 0.60,
        "rebalance": 0.70,
        "hold": 0.80,
    }.get(action, 0.5)

    volatility = portfolio_context.get("volatility", 0.3)
    return max(base - volatility * 0.3, 0.1)


def estimate_freelance_success(client_type: str, project_scope: str, your_rate: float, market_rate: float) -> float:
    """Estima probabilidad de cerrar proyecto freelance."""
    rate_ratio = your_rate / max(market_rate, 1)
    if rate_ratio > 1.5:
        return 0.2
    elif rate_ratio > 1.2:
        return 0.4
    elif rate_ratio > 1.0:
        return 0.6
    return 0.8
