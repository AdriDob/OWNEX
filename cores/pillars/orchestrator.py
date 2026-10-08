"""5-Pillar Orchestrator — Unifies the 5 zero-barrier income categories.

Pillar 1: Bug Bounty (HackerOne, Bugcrowd, Intigriti)
Pillar 2: AI Tasks (Alignerr, Outlier, Mindrift)
Pillar 3: Dev Bounty (Opire, Algora, IssueHunt)
Pillar 4: QA/Crowdtesting (Testlio, uTest, Testbirds)
Pillar 5: Data Annotation (Scale AI, Appen/CrowdGen)

## Qué es un hecho y qué es una proyección

**Hecho de mercado** (verificable en la página de la plataforma, se declara):
`pay_range`, `platforms`, `barrier`, `time_to_first_pay`.

**Proyección** (depende del tiempo disponible y de la tasa de aceptación
**real del owner**, que todavía no existe): `avg_pay_rate`,
`monthly_potential_low/high`.

Las proyecciones son `None` = UNKNOWN mientras no haya datos reales. Antes
eran literales, y de ellos salían `total_monthly_potential` y
`combined_ev_per_hour` — o sea, un `$5,000 - $39,000/mes` y `$222/hora`
presentados con la precisión de una medición, calculados sobre números
escritos a mano. Medido 2026-10-08: el revenue loop real tiene **0 acciones
registradas**, así que no hay nada que proyectar todavía.

`combined_ev_per_hour` ahora sale del **revenue loop real** cuando hay
acciones, y es `None` cuando no las hay. Es la diferencia entre "el sistema
sabe cuánto ganás por hora" y "el sistema siempre dice $222".
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("ownex.pillars.orchestrator")


def _measured_revenue_per_hour() -> float | None:
    """$/hora-humana REAL, o `None` si nunca se registró una acción.

    Única fuente de verdad: `RevenueLearningLoop`, que es donde el owner
    registra lo que hizo y cuánto le pagaron. Sin acciones no hay tasa: no
    hay forma de calcularla honestamente.
    """
    try:
        from cores.learning.revenue_loop import get_revenue_loop
    except Exception as exc:  # pragma: no cover — import opcional
        logger.debug("revenue loop no disponible: %s", exc)
        return None

    try:
        totals = get_revenue_loop().get_totals()
    except Exception as exc:  # pragma: no cover — datos corruptos
        logger.warning("no se pudo leer el revenue loop: %s", exc)
        return None

    if not totals.get("total_actions"):
        return None
    rate = totals.get("avg_revenue_per_hour")
    return float(rate) if rate is not None else None


def _fmt_money_range(low: float | None, high: float | None) -> str | None:
    """`None` si falta cualquiera de los dos extremos: no se inventa un rango."""
    if low is None or high is None:
        return None
    return f"${low:,.0f} - ${high:,.0f}"


@dataclass
class PillarSummary:
    """Summary of one income pillar.

    `avg_pay_rate` y `monthly_potential_low/high` son proyecciones: `None`
    significa UNKNOWN, no cero. Ver la nota del módulo.
    """

    name: str
    pillar_id: int
    platforms: list[str]
    avg_pay_rate: float | None
    pay_range: str
    barrier: str
    monthly_potential_low: float | None
    monthly_potential_high: float | None
    hours_per_day: float
    time_to_first_pay: str
    skill_requirements: list[str]
    portfolio_required: bool
    interview_required: bool
    repeatable: bool
    automation_potential: float  # 0-1

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "pillar_id": self.pillar_id,
            "platforms": self.platforms,
            "avg_pay_rate": self.avg_pay_rate,
            "pay_range": self.pay_range,
            "barrier": self.barrier,
            "monthly_potential": _fmt_money_range(self.monthly_potential_low, self.monthly_potential_high),
            "monthly_potential_status": ("UNKNOWN" if self.monthly_potential_low is None else "PROJECTED (no medido)"),
            "hours_per_day": self.hours_per_day,
            "time_to_first_pay": self.time_to_first_pay,
            "skill_requirements": self.skill_requirements,
            "portfolio_required": self.portfolio_required,
            "interview_required": self.interview_required,
            "repeatable": self.repeatable,
            "automation_potential": self.automation_potential,
        }


@dataclass
class FivePillarDashboard:
    """Complete 5-pillar dashboard.

     Los totales son `None` mientras las proyecciones por pillar sean
    UNKNOWN: sumar `None` como si fuera 0 devolvería un rango con menos
     pillars de los que hay, que es peor que no devolver nada.
    """

    pillars: list[PillarSummary]
    total_monthly_low: float | None
    total_monthly_high: float | None
    total_hours_per_day: float
    combined_ev_per_hour: float | None
    recommendations: list[str]
    next_best_pillar: str | None
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "pillars": [p.to_dict() for p in self.pillars],
            "total_monthly_potential": _fmt_money_range(self.total_monthly_low, self.total_monthly_high),
            "total_monthly_potential_status": (
                "UNKNOWN"
                if self.total_monthly_low is None
                else "PROJECTED (suma de proyecciones por pillar, no medido)"
            ),
            "total_hours_per_day": self.total_hours_per_day,
            "combined_ev_per_hour": (
                None if self.combined_ev_per_hour is None else round(self.combined_ev_per_hour, 2)
            ),
            "combined_ev_per_hour_source": (
                "MEASURED (RevenueLearningLoop)" if self.combined_ev_per_hour is not None else "UNKNOWN: 0 acciones"
            ),
            "recommendations": self.recommendations,
            "next_best_pillar": self.next_best_pillar,
            "timestamp": self.timestamp,
        }


class FivePillarOrchestrator:
    """Orchestrates all 5 zero-barrier income pillars."""

    def __init__(self) -> None:
        self.pillars = self._init_pillars()

    def _init_pillars(self) -> list[PillarSummary]:
        """Initialize the 5 pillars with real data."""
        return [
            PillarSummary(
                name="Bug Bounty",
                pillar_id=1,
                platforms=["HackerOne", "Bugcrowd", "Intigriti", "YesWeHack", "Immunefi", "Synack"],
                avg_pay_rate=None,
                pay_range="$200 - $50,000/bounty (rango publicado, no un promedio)",
                # Hecho: registrarse en HackerOne/Bugcrowd/Intigriti no cuesta
                # ni exige credencial. La barrera real es el ratio
                # finding/aceptado, que es UNKNOWN hasta tener datos.
                barrier="$0 para entrar; el filtro real es aceptar findings",
                monthly_potential_low=None,
                monthly_potential_high=None,
                hours_per_day=1.5,
                time_to_first_pay="2-8 weeks",
                skill_requirements=["security", "api", "web", "reporting"],
                portfolio_required=False,
                interview_required=False,
                repeatable=True,
                automation_potential=0.75,
            ),
            PillarSummary(
                name="AI Tasks",
                pillar_id=2,
                # Reconciliado 2026-10-08 contra verificación en la página de
                # cada plataforma. Antes decía `barrier="$0"` para las cuatro,
                # lo cual era FALSO para dos de ellas:
                #   · Outlier  → "minimum qualifications typically require
                #     undergraduate-level expertise" (credential)
                #   · Mindrift → "70% of our contributors hold a Master's or
                #     PhD" (credential)
                #   · Alignerr → "No experience needed" (assessment real)
                # La barrera declarada ahora distingue las que sí se pueden
                # tomar sin credencial, en vez de promediar una afirmación
                # falsa sobre cuatro.
                platforms=["Alignerr", "Outlier", "Mindrift"],
                avg_pay_rate=None,
                pay_range="$10 - $200/hour (Alignerr publica $10-35, $15-35, $150)",
                barrier="Mixto: Alignerr $0 (assessment); Outlier y Mindrift piden grado",
                monthly_potential_low=None,
                monthly_potential_high=None,
                hours_per_day=1.0,
                time_to_first_pay="1-2 weeks (declarado por las plataformas; no medido por nosotros)",
                skill_requirements=["reasoning", "ai", "attention_to_detail"],
                portfolio_required=False,
                interview_required=False,
                repeatable=True,
                automation_potential=0.3,
            ),
            PillarSummary(
                name="Dev Bounty",
                pillar_id=3,
                platforms=["Opire", "Algora", "IssueHunt", "Gitcoin", "Dework", "Open Collective"],
                avg_pay_rate=None,
                pay_range="$50 - $2,000/bounty (rango publicado, no un promedio)",
                barrier="$0 para entrar (Opire/Algora/IssueHunt no cobran por registrarse)",
                monthly_potential_low=None,
                monthly_potential_high=None,
                hours_per_day=1.0,
                time_to_first_pay="1-4 weeks",
                skill_requirements=["python", "javascript", "git", "coding"],
                portfolio_required=False,
                interview_required=False,
                repeatable=True,
                automation_potential=0.5,
            ),
            PillarSummary(
                name="QA/Crowdtesting",
                pillar_id=4,
                platforms=["Testlio", "uTest", "Testbirds", "Bugcrowd Discovery"],
                avg_pay_rate=None,
                pay_range="$10 - $100/bug (rango publicado, no un promedio)",
                barrier="$0 para entrar (uTest/Testlio/Testbirds no cobran por registrarse)",
                monthly_potential_low=None,
                monthly_potential_high=None,
                hours_per_day=0.5,
                time_to_first_pay="1-2 weeks",
                skill_requirements=["attention_to_detail", "reporting", "qa"],
                portfolio_required=False,
                interview_required=False,
                repeatable=True,
                automation_potential=0.4,
            ),
            PillarSummary(
                name="Data Annotation",
                pillar_id=5,
                platforms=["Scale AI", "Outlier", "Appen/CrowdGen"],
                avg_pay_rate=None,
                pay_range="$8 - $22/hour (rango publicado, no un promedio)",
                barrier="$0 para entrar (Scale AI/Outlier/Appen no cobran por registrarse)",
                monthly_potential_low=None,
                monthly_potential_high=None,
                hours_per_day=0.5,
                time_to_first_pay="1-2 weeks",
                skill_requirements=["attention_to_detail", "consistency", "patience"],
                portfolio_required=False,
                interview_required=False,
                repeatable=True,
                automation_potential=0.2,
            ),
        ]

    def get_dashboard(self) -> FivePillarDashboard:
        """Dashboard de los 5 pillars.

        El total mensual sólo se calcula si **todos** los pillars tienen
        proyección: sumar rangos donde faltan 2 de 5 daría un total con menos
        pillars de los que existen, que se lee como un número completo.

        `combined_ev_per_hour` **no** se deriva de las proyecciones (eso
        producía `$222/hora` sin ningún dato detrás). Sale del revenue loop
        real, o `None` si nunca se registró una acción.
        """
        lows = [p.monthly_potential_low for p in self.pillars]
        highs = [p.monthly_potential_high for p in self.pillars]
        projected = all(v is not None for v in lows + highs)
        total_low = sum(v for v in lows if v is not None) if projected else None
        total_high = sum(v for v in highs if v is not None) if projected else None
        total_hours = sum(p.hours_per_day for p in self.pillars)

        measured_rate = _measured_revenue_per_hour()

        return FivePillarDashboard(
            pillars=self.pillars,
            total_monthly_low=total_low,
            total_monthly_high=total_high,
            total_hours_per_day=total_hours,
            combined_ev_per_hour=measured_rate,
            recommendations=self._generate_recommendations(),
            # `next_best_pillar` = None. Antes venía de un dict literal de
            # prioridades (`{"AI Tasks": 95, ...}`) impreso con la autoridad
            # de un óptimo calculado — y era consejo **equivocado**: 2 de
            # las 4 plataformas de AI Tasks piden credencial académica
            # (verificado 2026-10-08).
            #
            # Rankear pillars exige el payout POR pillar, y
            # `RevenueLearningLoop` no guarda esa dimensión (registra
            # `opportunity_id`, `action_type`, `title`, `expected_value`,
            # `actual_revenue`). Agregar el campo para después devolver un
            # número es deuda de esquema comprada con una afirmación.
            next_best_pillar=None,
            timestamp=datetime.now(UTC).isoformat(),
        )

    def _generate_recommendations(self) -> list[str]:
        """Recomendaciones accionables.

        Antes la primera era *"Start with AI Tasks — fastest time to first
        pay"*, un literal. Es advice, no una medición: se declara como
        opinion y se apoya en lo verificado, no en lo inventado.
        """
        recs = [
            "Suma de proyecciones NO medida: el potencial mensual por pillar es "
            "UNKNOWN hasta que existan payouts reales registrados",
            "Registra cada acción en el revenue loop (POST /api/learning/action): sin eso, $/hora-humana es UNKNOWN",
            "Track HUMAN_MINUTES/DAY — la tasa real se calcula con tiempo real, no con el tiempo supuesto del plan",
        ]
        # Verificado 2026-10-08: de las 4 plataformas de AI Tasks, 2 piden
        # credencial académica. "Empezá por AI Tasks" era advice engañoso.
        recs.append(
            "Si elegís AI Tasks: sólo Alignerr es assessment sin credencial "
            "(Outlier y Mindrift piden grado). Verificado en sus páginas"
        )
        recs.append(
            "Bug Bounty y Dev Bounty son los de barrera más baja real: registrarse no cuesta ni requiere credencial"
        )
        return recs

    def get_pillar(self, pillar_id: int) -> PillarSummary | None:
        """Get a specific pillar by ID."""
        for p in self.pillars:
            if p.pillar_id == pillar_id:
                return p
        return None

    def get_startup_plan(self) -> dict[str, Any]:
        """Plan día a día de la primera semana.

        Las `actions` son reales (son las plataformas que existen y el tiempo
        de registro típico). Los `expected_income` eran **inventados**:
        `"$0-30"`, `"$10-30"`, `"$0-50"`, `"$0"`, `"$20-80"`, `"$50-150"` —
        seis números escritos a mano que suman ~$80-$310 en la semana 1.
        Ahora `None` con el motivo: sin payouts registrados no hay base para
        proyectar. Una columna de ingresos que es ficción es un plan con el
        que el owner dimensiona su semana.
        """
        return {
            "day_1": {
                "focus": "AI Tasks + Data Annotation",
                "actions": [
                    "Register on Outlier.ai (10 min)",
                    "Register on Scale AI (10 min)",
                    "Pass qualification tests (1-2 hours)",
                    "Complete first tasks (1 hour)",
                ],
                "expected_income": None,
                "expected_income_note": "UNKNOWN: sin payouts registrados no hay base para proyectar",
                "time_required": "2-3 hours",
            },
            "day_2": {
                "focus": "QA/Crowdtesting",
                "actions": [
                    "Register on uTest (10 min)",
                    "Register on Testlio (10 min)",
                    "Complete profiles (20 min)",
                    "Start first test cycle (1 hour)",
                ],
                "expected_income": None,
                "expected_income_note": "UNKNOWN: sin payouts registrados no hay base para proyectar",
                "time_required": "2 hours",
            },
            "day_3": {
                "focus": "Dev Bounty",
                "actions": [
                    "Register on Opire (10 min)",
                    "Register on Algora (10 min)",
                    "Browse available bounties (30 min)",
                    "Start first bounty (1 hour)",
                ],
                "expected_income": None,
                "expected_income_note": "UNKNOWN: sin payouts registrados no hay base para proyectar",
                "time_required": "2 hours",
            },
            "day_4": {
                "focus": "Bug Bounty",
                "actions": [
                    "Register on HackerOne (10 min)",
                    "Register on Bugcrowd (10 min)",
                    "Configure OWNEX with targets (30 min)",
                    "Start first recon (1 hour)",
                ],
                "expected_income": None,
                "expected_income_note": "UNKNOWN: bug bounty no paga antes del primer report aceptado",
                "time_required": "2 hours",
            },
            "day_5": {
                "focus": "Optimize & Diversify",
                "actions": [
                    "Review all platform accounts",
                    "Check qualification status",
                    "Continue best-performing pillar",
                    "Start second task in AI/Data",
                ],
                "expected_income": None,
                "expected_income_note": "UNKNOWN: depende de lo que ya se registró y se pagó",
                "time_required": "2-3 hours",
            },
            "day_6_7": {
                "focus": "Stabilize",
                "actions": [
                    "Establish daily routine",
                    "Set up OWNEX morning briefing",
                    "Track time vs income",
                    "Optimize EV/hour",
                ],
                "expected_income": None,
                "expected_income_note": "UNKNOWN: depende de la tasa de aceptación real",
                "time_required": "2-3 hours/day",
            },
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize orchestrator state."""
        dashboard = self.get_dashboard()
        return {
            "dashboard": dashboard.to_dict(),
            "startup_plan": self.get_startup_plan(),
        }


# Singleton
_five_pillar_orchestrator: FivePillarOrchestrator | None = None


def get_five_pillar_orchestrator() -> FivePillarOrchestrator:
    """Get or create the global 5-pillar orchestrator."""
    global _five_pillar_orchestrator
    if _five_pillar_orchestrator is None:
        _five_pillar_orchestrator = FivePillarOrchestrator()
    return _five_pillar_orchestrator
