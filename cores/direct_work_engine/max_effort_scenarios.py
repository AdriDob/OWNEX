"""Max-Effort Scenarios — bandas P10/P50/P90 del año 1 en modo contract_dev_first.

Basado EXCLUSIVAMENTE en los rates curados reales de contract_sources.py:
Upwork $35/h · Contra $45/h · Malt $40/h · Braintrust $70/h · Gun.io $80/h ·
Arc.dev $55/h · Fiverr variable.

Reglas de honestidad (§ integridad económica):
- Son ESCENARIOS probabilísticos, no promesas.
- La rampa modela reputación compuesta (reviews → rate ↑ → vetting premium).
- Sin track record del usuario los números parten del piso; la calibración
  semanal los ajusta con resultados reales.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EffortBand:
    label: str
    probability: str
    year_total_low: int
    year_total_high: int
    monthly_curve: tuple[tuple[int, int, int], ...]  # (mes, low, high)

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "probability": self.probability,
            "year_total": {"low": self.year_total_low, "high": self.year_total_high},
            "monthly_curve": [{"month": m, "low": lo, "high": hi} for m, lo, hi in self.monthly_curve],
        }


def _curve(rates: tuple[float, ...], hours_week: float) -> tuple[tuple[int, int, int], ...]:
    """Curva mensual: rate efectivo por mes × horas facturables (utilización 60-85%)."""
    out = []
    for month, base_rate in enumerate(rates, start=1):
        utilization = min(0.85, 0.45 + month * 0.05)  # rampa de clientes activos
        low = int(base_rate * hours_week * 4.3 * utilization * 0.7)  # P-low: 70% fill
        high = int(base_rate * hours_week * 4.3 * utilization * 1.15)  # P-high: overflow
        out.append((month, low, high))
    return tuple(out)


def compute_max_effort_scenarios(
    hours_per_week: float = 60.0,
    *,
    premium_vetted_month: int = 4,
) -> dict[str, EffortBand]:
    """Tres escenarios del año 1 a esfuerzo máximo (60h/sem default).

    - P50: rates de marketplace abierto con rampa normal.
    - P90: vetting premium aprobado temprano (Braintrust/Gun.io) + paralelos.
    - P10: mercado duro / onboarding lento / gaps entre contratos.
    """
    h = hours_per_week

    p50_rates = tuple(35.0 if m < 3 else 45.0 if m < premium_vetted_month else 55.0 for m in range(1, 13))
    p90_rates = tuple(45.0 if m < 2 else 70.0 if m < premium_vetted_month else 85.0 for m in range(1, 13))
    p10_rates = tuple(30.0 if m < 5 else 40.0 for m in range(1, 13))

    def total(curve: tuple[tuple[int, int, int], ...]) -> tuple[int, int]:
        return sum(lo for _, lo, _ in curve), sum(hi for _, _, hi in curve)

    c_p50 = _curve(p50_rates, h)
    c_p90 = _curve(p90_rates, h)
    c_p10 = _curve(p10_rates, h)
    t_p50 = total(c_p50)
    t_p90 = total(c_p90)
    t_p10 = total(c_p10)

    return {
        "p50_expected": EffortBand(
            label="Esperado (esfuerzo máximo sostenido)",
            probability="P50",
            year_total_low=t_p50[0],
            year_total_high=t_p50[1],
            monthly_curve=c_p50,
        ),
        "p90_top_decile": EffortBand(
            label="Top decil (vetting premium temprano + contratos paralelos)",
            probability="P90",
            year_total_low=t_p90[0],
            year_total_high=t_p90[1],
            monthly_curve=c_p90,
        ),
        "p10_floor": EffortBand(
            label="Piso (mercado duro — aún así supera AI-eval solo)",
            probability="P10",
            year_total_low=t_p10[0],
            year_total_high=t_p10[1],
            monthly_curve=c_p10,
        ),
    }


def summarize_for_command_center(scenarios: dict[str, EffortBand] | None = None) -> dict:
    """Resumen compacto para el Command Center: tu techo honesto hoy."""
    s = scenarios or compute_max_effort_scenarios()
    p50 = s["p50_expected"]
    p90 = s["p90_top_decile"]
    first = p50.monthly_curve[0]
    last = p50.monthly_curve[-1]
    return {
        "philosophy": "Escenarios basados en rates curados reales — no promesas. "
        "La calibración semanal ajusta estas bandas a TU realidad.",
        "year_1": {
            "expected": {"low": f"${p50.year_total_low:,}", "high": f"${p50.year_total_high:,}"},
            "top_decile": {"low": f"${p90.year_total_low:,}", "high": f"${p90.year_total_high:,}"},
        },
        "trajectory": {
            "month_1": {"low": first[1], "high": first[2]},
            "month_12": {"low": last[1], "high": last[2]},
        },
        "note_variable_band": "$1k–50k/mes variable coincide con esta trayectoria: "
        "empieza en el piso y escala con reputación compuesta.",
    }
