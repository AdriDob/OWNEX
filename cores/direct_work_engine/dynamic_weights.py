"""Dynamic Category Weights — la evidencia de conversión decide la mezcla.

Decisión owner 2026-08-26 (plan final): ni primario estático ni 50/50 fijo.
Los pesos del recommender arrancan orientados a caja rápida y migran hacia
lo que el HISTORIAL REAL demuestra que paga.

Reglas:
- Arranque (sin evidencia): CASHFLOW/SOFTWARE 80% · SECURITY 20%
- Cada categoría con resultados reales gana peso proporcional a su
  EV/hora-humana realizada (accepted+paid), suavizado por laplace.
- Límites: ningún motor baja de 15% ni sube de 85% (nunca ciego total).
- UNKNOWN jamás suma evidencia (honestidad económica).
"""

from __future__ import annotations

MIN_WEIGHT = 0.15
MAX_WEIGHT = 0.85
PRIOR_ACCEPTED = 2.0  # smoothing laplaceano
PRIOR_HOURS = 4.0


def compute_dynamic_weights(
    category_outcomes: list[dict],
    *,
    accepted_key: str = "accepted",
    paid_key: str = "paid",
    hours_key: str = "hours",
    ev_key: str = "ev_usd",
    fast_categories: tuple[str, ...] = (
        "ai_evaluation",
        "data_annotation",
        "qa_automation",
        "dev_bounty",
        "oss_bounties",
        "open_source",
        "software_engineering",
        "backend",
        "technical_writing",
        "documentation",
        "code_review",
        "prompt_engineering",
    ),
) -> dict[str, float]:
    """Pesos por MOTOR (fast-cash vs security/frontier/extreme) desde evidencia.

    ``category_outcomes``: registros de resultados reales por oportunidad,
    p.ej. desde calibración o feedback loop. Cada dict debe traer al menos
    ``category`` y los keys de arriba (ausentes = sin señal).
    """
    fast_ev = PRIOR_ACCEPTED * 10.0  # prior proporcional a rates curados ($35/h piso)
    sec_ev = PRIOR_ACCEPTED * 2.5  # security paga más por hit pero menos frecuente
    fast_hours = PRIOR_HOURS
    sec_hours = PRIOR_HOURS

    for rec in category_outcomes:
        cat = str(rec.get("category", "")).lower()
        is_fast = any(cat.startswith(fc.split("_")[0]) or cat == fc for fc in fast_categories)
        # solo cuenta evidencia dura: aceptado Y con horas registradas
        if not (rec.get(accepted_key) or rec.get(paid_key)):
            continue
        hours = float(rec.get(hours_key) or 0)
        ev = float(rec.get(ev_key) or 0)
        if hours <= 0 or ev <= 0:
            continue
        if is_fast:
            fast_ev += ev
            fast_hours += hours
        else:
            sec_ev += ev
            sec_hours += hours

    raw_fast = fast_ev / fast_hours
    raw_sec = sec_ev / sec_hours
    share = raw_fast / (raw_fast + raw_sec)

    share = max(MIN_WEIGHT, min(MAX_WEIGHT, share))
    return {"fast_cash": round(share, 3), "security_upside": round(1 - share, 3)}
