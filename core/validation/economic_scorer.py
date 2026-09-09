"""Economic Scorer — evalúa si una hipótesis merece una request.

Antes de gastar ancho de banda, rate limit, y tiempo de CPU,
calcula el valor esperado de validar esta hipótesis.

Fuentes:
  - EconomicMemory (ROI histórico por programa/vuln type)
  - Payout averages por severidad y tipo de vulnerabilidad
  - Acceptance rate histórico del reasoner
  - Esfuerzo estimado de validación
"""

from __future__ import annotations

import logging
from typing import Any

from core.validation.models import AttackCandidate, EconomicScore, VulnType

logger = logging.getLogger("orion.core.validation.economic_scorer")

# ── Payout benchmarks por severidad (USD,保守 estimates) ──────
# Basado en promedios públicos de HackerOne/Bugcrowd 2024-2026
PAYOUT_BY_SEVERITY: dict[str, tuple[float, float, float]] = {
    "critical": (2000.0, 10000.0, 3500.0),  # low, high, avg
    "high": (500.0, 4000.0, 1500.0),
    "medium": (150.0, 1000.0, 400.0),
    "low": (50.0, 250.0, 100.0),
    "info": (0.0, 50.0, 0.0),
}

# ── Payout multipliers por vulnerabilidad ─────────────────────
# Relativos a la severidad base. Ej: RCE crítica paga más que
# un XSS reflected de la misma severidad.
VULN_PAYOUT_MULTIPLIER: dict[VulnType, float] = {
    VulnType.IDOR: 1.2,  # IDORs suelen pagar bien
    VulnType.SSRF: 1.5,  # SSRF puede escalar a RCE
    VulnType.XSS: 0.8,  # XSS reflected paga menos
    VulnType.SQLI: 1.8,  # SQLi = acceso a DB
    VulnType.AUTH_BYPASS: 1.3,
    VulnType.CSRF: 0.6,
    VulnType.LFI: 1.2,
    VulnType.CMDI: 2.0,  # RCE-level
    VulnType.RACE_CONDITION: 1.0,
    VulnType.CORS: 0.5,
    VulnType.OPEN_REDIRECT: 0.3,
    VulnType.BUSINESS_LOGIC: 1.0,
    VulnType.GENERIC: 0.5,
}

# ── Acceptance probability por tipo (baseline) ───────────────
# Sin histórico, estimación basada en datos públicos
BASE_ACCEPTANCE: dict[VulnType, float] = {
    VulnType.IDOR: 0.65,
    VulnType.SSRF: 0.55,
    VulnType.XSS: 0.40,
    VulnType.SQLI: 0.50,
    VulnType.AUTH_BYPASS: 0.45,
    VulnType.CSRF: 0.35,
    VulnType.LFI: 0.50,
    VulnType.CMDI: 0.60,
    VulnType.GENERIC: 0.30,
}

# ── Effort estimates por tipo (minutos) ──────────────────────
VALIDATION_EFFORT_MINUTES: dict[VulnType, float] = {
    VulnType.IDOR: 8.0,
    VulnType.SSRF: 10.0,
    VulnType.XSS: 5.0,
    VulnType.SQLI: 15.0,
    VulnType.AUTH_BYPASS: 5.0,
    VulnType.CSRF: 4.0,
    VulnType.LFI: 7.0,
    VulnType.CMDI: 12.0,
    VulnType.GENERIC: 5.0,
}


class EconomicScorer:
    """Evalúa el valor económico de validar un AttackCandidate."""

    def __init__(self) -> None:
        self._economic_memory: Any = None  # lazy import
        self._loaded = False

    def _lazy_load(self) -> None:
        """Carga EconomicMemory si está disponible."""
        if self._loaded:
            return
        try:
            from core.revenue.economic_memory import EconomicMemory

            self._economic_memory = EconomicMemory()
            self._loaded = True
        except ImportError:
            logger.debug("[ECONOMIC] EconomicMemory no disponible — usando defaults")
        except Exception as exc:
            logger.debug("[ECONOMIC] Error loading EconomicMemory: %s", exc)

    def score(self, candidate: AttackCandidate) -> EconomicScore:
        """Calcula el Economic Score para un AttackCandidate."""
        self._lazy_load()
        vuln = candidate.vulnerability_type
        severity = self._estimate_severity(candidate)

        # Payout estimado
        low_p, high_p, avg_p = PAYOUT_BY_SEVERITY.get(severity, (0, 0, 0))
        multiplier = VULN_PAYOUT_MULTIPLIER.get(vuln, 1.0)
        avg_p *= multiplier

        # Acceptance probability
        acceptance = BASE_ACCEPTANCE.get(vuln, 0.3)
        if self._economic_memory:
            acceptance = self._adjust_acceptance(vuln, acceptance)

        # Esfuerzo
        effort = VALIDATION_EFFORT_MINUTES.get(vuln, 10.0)

        # USD/h
        expected_value = avg_p * acceptance
        hours = effort / 60.0
        usd_per_hour = expected_value / hours if hours > 0 else 0.0

        # Prioridad 1-10
        priority = self._compute_priority(avg_p, acceptance, effort, candidate.reasoner_confidence)

        reasoning: list[str] = []
        reasoning.append(f"Vulnerabilidad: {vuln.value}")
        reasoning.append(f"Severidad estimada: {severity}")
        reasoning.append(f"Payout estimado: ${avg_p:.0f} (range ${low_p:.0f}-${high_p:.0f})")
        reasoning.append(f"Multiplicador por tipo: {multiplier}x")
        reasoning.append(f"Probabilidad de aceptación: {acceptance:.0%}")
        reasoning.append(f"Value esperado: ${expected_value:.0f}")
        reasoning.append(f"Esfuerzo estimado: {effort:.0f} min")
        reasoning.append(f"USD/h: ${usd_per_hour:.0f}")
        reasoning.append(f"Confianza del reasoner: {candidate.reasoner_confidence:.0%}")

        return EconomicScore(
            expected_payout_low=low_p,
            expected_payout_high=high_p,
            expected_payout_avg=round(avg_p, 2),
            probability_acceptance=round(acceptance, 2),
            effort_minutes=effort,
            usd_per_hour=round(usd_per_hour, 2),
            priority=priority,
            reasoning=reasoning,
        )

    def _estimate_severity(self, candidate: AttackCandidate) -> str:
        """Estima severidad del candidate basado en método HTTP y tipo."""
        # Por defecto, medium. Subjective basado en señales
        method = candidate.method.upper()
        if method in ("DELETE", "PUT", "PATCH") and candidate.vulnerability_type in (
            VulnType.IDOR,
            VulnType.AUTH_BYPASS,
        ):
            return "high"
        if method == "GET" and candidate.vulnerability_type == VulnType.IDOR:
            return "medium"
        if candidate.vulnerability_type in (VulnType.CMDI, VulnType.SQLI):
            return "critical"
        if candidate.vulnerability_type == VulnType.SSRF:
            return "high"
        return "medium"

    def _adjust_acceptance(self, vuln: VulnType, base: float) -> float:
        """Ajusta acceptance probability con datos históricos si existen."""
        try:
            if self._economic_memory and hasattr(self._economic_memory, "get_acceptance_rate"):
                historical = self._economic_memory.get_acceptance_rate(vuln.value)
                if historical > 0:
                    # Blend: 70% histórico, 30% base
                    return historical * 0.7 + base * 0.3
        except Exception:
            pass
        return base

    def _compute_priority(self, payout: float, acceptance: float, effort: float, confidence: float) -> int:
        """Computa prioridad 1-10."""
        ev = payout * acceptance
        usd_per_hour = ev / (effort / 60.0) if effort > 0 else 0.0

        # Puntaje base
        score = 0
        if usd_per_hour >= 1000:
            score += 4
        elif usd_per_hour >= 500:
            score += 3
        elif usd_per_hour >= 200:
            score += 2
        elif usd_per_hour >= 50:
            score += 1

        if confidence >= 0.7:
            score += 3
        elif confidence >= 0.5:
            score += 2
        elif confidence >= 0.3:
            score += 1

        if ev >= 1000:
            score += 2
        elif ev >= 200:
            score += 1

        # Bonus por effort bajo
        if effort <= 5:
            score += 1

        return max(1, min(10, score))

    def filter_candidates(
        self, candidates: list[AttackCandidate], min_priority: int = 3, max_candidates: int = 10
    ) -> list[AttackCandidate]:
        """Filtra y ordena candidates por prioridad económica."""
        for c in candidates:
            c.economic_score = self.score(c)

        scored = [c for c in candidates if c.economic_score.priority >= min_priority]
        scored.sort(key=lambda c: c.economic_score.priority, reverse=True)
        return scored[:max_candidates]
