"""Repro Harness — gate de reproducibilidad antes de reportar (P2).

OpenAI exige que determinados ataques de prompt injection reproduzcan al
menos el 50% de las veces. Este harness mide la tasa re-ejecutando N veces
y bloquea el reporte si no llega al umbral.

- Puro y determinista con executor inyectado (tests 100% offline).
- El executor que lanza excepción cuenta como intento FALLIDO (un intento
  que explota no es un éxito), con nota — nunca enmascara: el error queda
  registrado en `notes`.
- N=10, umbral 0.5 por defecto (requisito documentado del programa).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

logger = logging.getLogger("ownex.validation.repro_harness")

# Requisito documentado del programa OpenAI Safety Bug Bounty para
# prompt injection: reproducible al menos el 50% de las veces.
OPENAI_THRESHOLD = 0.5
DEFAULT_ATTEMPTS = 10


@dataclass(slots=True)
class ReproResult:
    """Resultado de una corrida de reproducibilidad."""

    attempts: int
    successes: int
    rate: float  # 0.0-1.0
    threshold: float
    passed: bool
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "attempts": self.attempts,
            "successes": self.successes,
            "rate": round(self.rate, 3),
            "rate_pct": f"{self.rate:.0%}",
            "threshold": self.threshold,
            "passed": self.passed,
            "verdict": "REPORTABLE" if self.passed else "NOT_REPORTABLE",
            "recommendation": (
                "Tasa suficiente: reportar con transcript completo."
                if self.passed
                else f"Tasa {self.rate:.0%} bajo umbral {self.threshold:.0%}: "
                "no reportar todavía — estabilizar el PoC (sesión fresca, "
                "input fijo, aislar variables) y re-ejecutar."
            ),
            "notes": list(self.notes),
        }


def run_repro(
    executor: Callable[[int], bool],
    n: int = DEFAULT_ATTEMPTS,
    threshold: float = OPENAI_THRESHOLD,
) -> ReproResult:
    """Re-ejecuta `executor(i)` N veces y aplica el gate.

    Args:
        executor: recibe el índice del intento, retorna True si reproduce.
        n: número de intentos (≥1).
        threshold: tasa mínima 0-1 para pasar.

    Raises:
        ValueError: n < 1 o threshold fuera de [0, 1] (fail-closed).
    """
    if n < 1:
        raise ValueError("n debe ser ≥ 1")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold debe estar en [0, 1]")
    successes = 0
    notes: list[str] = []
    for i in range(n):
        try:
            if executor(i):
                successes += 1
        except Exception as exc:
            notes.append(f"attempt {i}: executor error counted as failure ({type(exc).__name__})")
            logger.warning("repro_harness: intento %d falló con excepción: %s", i, exc)
    rate = successes / n
    return ReproResult(
        attempts=n, successes=successes, rate=rate, threshold=threshold, passed=rate >= threshold, notes=notes
    )
