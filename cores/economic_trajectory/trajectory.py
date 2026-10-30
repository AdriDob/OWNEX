"""Economic Trajectory — REAL / PIPELINE / SCENARIO, nunca mezclados.

SPEC "ECONOMIC TRAJECTORY TRACKER" (owner, 2026-09-28). Reglas duras:

- Solo ``paid``/``net`` es dinero REAL. ``potential``/``expected``/
  ``submitted``/``accepted`` NUNCA se suman como cash.
- Todo futuro es ESCENARIO hasta que existan resultados reales
  (``kind="scenario"`` + ``label="PLANNING_SCENARIO"``).
- La capacidad (available_hours) es CONFIGURABLE; jamás hardcodeada.
- Sin datos → ``None``/``"UNKNOWN"``, jamás 0 inventado como tasa.
- Puro: recibe una lista de oportunidades (RevenueOpportunity-like o dict),
  sin DB ni red. El caller decide de dónde leer.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

# ── Estados económicos (spec §1) ───────────────────────────────────────────
STATE_POTENTIAL = "potential"
STATE_EXPECTED = "expected"
STATE_SUBMITTED = "submitted"
STATE_ACCEPTED = "accepted"
STATE_AWARDED = "awarded"
STATE_PAID = "paid"
STATE_NET = "net"

# Solo estos dos son cash REAL (spec §1: solo PAID representa dinero cobrado).
REAL_CASH_STATES = frozenset({STATE_PAID, STATE_NET})
# Verificables pero NO cash: cuentan para el gap como "pending verificable".
VERIFIABLE_PENDING_STATES = frozenset({STATE_SUBMITTED, STATE_ACCEPTED, STATE_AWARDED})
# Específicos: nunca se agregan al cash ni al gap.
SPECULATIVE_STATES = frozenset({STATE_POTENTIAL, STATE_EXPECTED})

SCENARIO_TIERS = ("conservative", "central", "high")

# Escenarios de planificación iniciales (spec §6-§8). NO son forecasts:
# se recalibran con datos reales vía `calibrate_scenarios()`.
PLANNING_SCENARIOS: dict[str, dict[str, tuple[float, float]]] = {
    "conservative": {"m1_3": (0.0, 800.0), "m1_6": (1000.0, 5000.0), "m7_12": (1000.0, 4000.0)},
    "central": {"m1_3": (800.0, 2500.0), "m1_6": (5000.0, 15000.0), "m7_12": (4000.0, 8000.0)},
    "high": {"m1_3": (3000.0, 5000.0), "m1_6": (20000.0, 40000.0), "m7_12": (10000.0, 20000.0)},
}
# Escenarios largos (spec §9) — siempre como LONG_TERM_SCENARIOS.
LONG_TERM_SCENARIOS: list[dict[str, Any]] = [
    {"id": "lt_2k_5k", "monthly_range": (2000.0, 5000.0)},
    {"id": "lt_5k_12k", "monthly_range": (5000.0, 12000.0)},
    {"id": "lt_15k_30k", "monthly_range": (15000.0, 30000.0)},
    {"id": "lt_30k_50k", "monthly_range": (30000.0, 50000.0)},
]

# Canales canónicos (spec §12).
CHANNELS = (
    "ai_work",
    "oss",
    "security",
    "bug_bounty",
    "web3_security",
    "coding",
    "competitions",
    "ownex",
    "commerce",
    "other",
)

DEFAULT_AVAILABLE_HOURS = 77.0  # inicial de planificación, CONFIGURABLE (spec §2)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _aware(value: object) -> datetime | None:
    """Normaliza a datetime aware (spec §36 timezone correctness). Naive → UTC."""
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    return None


def _as_float(value: object) -> float:
    try:
        out = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    return out if out > 0 else 0.0


@dataclass(slots=True)
class PeriodSnapshot:
    """Un periodo (mes / 90d / 180d / 365d) con las 3 capas separadas."""

    period: str
    realized_cash: float = 0.0
    paid_outcomes: int = 0
    accepted_outcomes: int = 0
    attempts: int = 0
    pipeline_value: float = 0.0
    speculative_value: float = 0.0
    hours_used: float = 0.0

    @property
    def net_cash_per_hour(self) -> float | None:
        # División por cero → UNKNOWN, nunca Infinity ni 0 inventado (spec §36).
        if self.hours_used <= 0 or self.paid_outcomes <= 0:
            return None
        return round(self.realized_cash / self.hours_used, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "period": self.period,
            "realized_cash": round(self.realized_cash, 2),
            "paid_outcomes": self.paid_outcomes,
            "accepted_outcomes": self.accepted_outcomes,
            "attempts": self.attempts,
            "pipeline_value": round(self.pipeline_value, 2),
            "speculative_value": round(self.speculative_value, 2),
            "hours_used": round(self.hours_used, 2),
            "net_cash_per_hour": self.net_cash_per_hour,
        }


@dataclass(slots=True)
class Trajectory:
    """Trayectoria completa. REAL / PIPELINE / SCENARIO jamás en un mismo número."""

    generated_at: str
    available_hours_per_week: float
    real_90d: PeriodSnapshot
    real_180d: PeriodSnapshot
    real_365d: PeriodSnapshot
    pipeline: PeriodSnapshot
    speculative_value: float = 0.0
    calibration: dict[str, Any] = field(default_factory=dict)
    channels: list[dict[str, Any]] = field(default_factory=list)
    scenarios: dict[str, Any] = field(default_factory=dict)
    alerts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "available_hours_per_week": self.available_hours_per_week,
            "real": {
                "d90": self.real_90d.to_dict(),
                "d180": self.real_180d.to_dict(),
                "d365": self.real_365d.to_dict(),
                "net_cash_per_hour": self.real_365d.net_cash_per_hour,
            },
            "pipeline": self.pipeline.to_dict(),
            "speculative": {
                "value": round(self.speculative_value, 2),
                "counted_as_cash": False,
                "label": "NOT_CASH",
            },
            "calibration": self.calibration,
            "channels": self.channels,
            "scenarios": self.scenarios,
            "alerts": self.alerts,
        }


def calibration_level(paid_outcomes: int) -> dict[str, Any]:
    """Nivel de calibración personal (spec §11). Pocos resultados ≠ certeza."""
    n = max(0, int(paid_outcomes or 0))
    if n == 0:
        return {
            "level": 0,
            "label": "NO_DATA",
            "paid_outcomes": 0,
            "net_cash_per_hour": None,
            "note": "0 PAID: $/hora UNKNOWN",
        }
    if n == 1:
        return {
            "level": 1,
            "label": "FIRST_REAL_DATA",
            "paid_outcomes": n,
            "net_cash_per_hour": None,
            "note": "1 PAID: primer dato real, aún no es patrón",
        }
    if n <= 5:
        return {
            "level": 2,
            "label": "EARLY_PATTERN",
            "paid_outcomes": n,
            "net_cash_per_hour": None,
            "note": "3-5 PAID: primer patrón",
        }
    if n <= 9:
        return {
            "level": 2,
            "label": "EARLY_PATTERN",
            "paid_outcomes": n,
            "net_cash_per_hour": None,
            "note": "3-9 PAID: patrón naciente",
        }
    if n <= 29:
        return {
            "level": 3,
            "label": "MEASURABLE_CHANNEL",
            "paid_outcomes": n,
            "net_cash_per_hour": None,
            "note": "10+ PAID: canal medible",
        }
    if n <= 49:
        return {
            "level": 4,
            "label": "RELIABLE_MODEL",
            "paid_outcomes": n,
            "net_cash_per_hour": None,
            "note": "30+ outcomes: modelo confiable",
        }
    return {
        "level": 5,
        "label": "CALIBRATED_ECONOMY",
        "paid_outcomes": n,
        "net_cash_per_hour": None,
        "note": "50+ outcomes: economía calibrada",
    }


def channel_validation(paid: int) -> str:
    """Términos literales del spec §13. 1 pago NO es 'canal validado'."""
    if paid <= 0:
        return "NO_SIGNAL"
    if paid == 1:
        return "PROOF_OF_POSSIBILITY"
    if paid <= 5:
        return "EARLY_SIGNAL"
    if paid <= 29:
        return "REPEATABILITY_SIGNAL"
    return "PLANIFIABLE_CHANNEL"


def _window(rows: list[dict[str, Any]], days: int, now: datetime) -> list[dict[str, Any]]:
    cutoff = now - timedelta(days=days)
    out: list[dict[str, Any]] = []
    for row in rows:
        ts = _aware(row.get("updated_at") or row.get("created_at"))
        if ts is not None and ts >= cutoff:
            out.append(row)
    return out


def _snapshot(period: str, rows: list[dict[str, Any]], hours_used: float) -> PeriodSnapshot:
    snap = PeriodSnapshot(period=period, hours_used=max(0.0, float(hours_used)))
    for row in rows:
        state = str(row.get("revenue_state") or "").strip().lower()
        amount = _as_float(row.get("amount"))
        snap.attempts += 1
        if state in REAL_CASH_STATES:
            snap.realized_cash += amount
            snap.paid_outcomes += 1
        elif state in VERIFIABLE_PENDING_STATES:
            snap.pipeline_value += amount
            if state in (STATE_ACCEPTED, STATE_AWARDED):
                snap.accepted_outcomes += 1
        elif state in SPECULATIVE_STATES:
            snap.speculative_value += amount
    return snap


def build_trajectory(
    opportunities: Iterable[Any],
    hours_by_period: dict[str, float] | None = None,
    available_hours_per_week: float = DEFAULT_AVAILABLE_HOURS,
    now: datetime | None = None,
) -> Trajectory:
    """Construye la trayectoria desde RevenueOpportunity-like o dicts. Puro.

    ``hours_by_period``: {"d90": h, "d180": h, "d365": h} — horas HUMANAS
    verificadas de cada ventana. Ausente = 0 → $/hora UNKNOWN (nunca inventado).
    """
    ref = now or _utcnow()
    rows: list[dict[str, Any]] = []
    for item in opportunities or []:
        if isinstance(item, dict):
            rows.append(item)
        else:
            rows.append(
                {
                    "revenue_state": getattr(item, "revenue_state", ""),
                    "amount": getattr(item, "amount", 0.0),
                    "platform": getattr(item, "platform", ""),
                    "status": getattr(item, "status", ""),
                    "created_at": getattr(item, "created_at", None),
                    "updated_at": getattr(item, "updated_at", None),
                }
            )
    hours = hours_by_period or {}
    real_90 = _snapshot("d90", _window(rows, 90, ref), hours.get("d90", 0.0))
    real_180 = _snapshot("d180", _window(rows, 180, ref), hours.get("d180", 0.0))
    real_365 = _snapshot("d365", _window(rows, 365, ref), hours.get("d365", 0.0))
    pipeline = _snapshot("all_verifiable", rows, hours.get("d365", 0.0))
    calib = calibration_level(real_365.paid_outcomes)
    calib["net_cash_per_hour"] = real_365.net_cash_per_hour
    alerts: list[str] = []
    if real_365.paid_outcomes == 1:
        alerts.append("FIRST_PAID")
    if real_365.paid_outcomes == 0:
        alerts.append("NO_PAID_YET")
    return Trajectory(
        generated_at=ref.isoformat(),
        available_hours_per_week=float(available_hours_per_week),
        real_90d=real_90,
        real_180d=real_180,
        real_365d=real_365,
        pipeline=pipeline,
        speculative_value=real_365.speculative_value,
        calibration=calib,
        channels=channel_economics(rows),
        scenarios=scenarios_block(calib, available_hours_per_week),
        alerts=alerts,
    )


def channel_economics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Métricas por canal (spec §12). CASH solo desde paid/net."""
    buckets: dict[str, dict[str, Any]] = {
        c: {"attempts": 0, "accepted": 0, "awarded": 0, "paid": 0, "cash": 0.0} for c in CHANNELS
    }
    for row in rows:
        raw_channel = str(row.get("channel") or "").strip().lower()
        channel = raw_channel if raw_channel in buckets else "other"
        state = str(row.get("revenue_state") or "").strip().lower()
        amount = _as_float(row.get("amount"))
        slot = buckets[channel]
        slot["attempts"] += 1
        if state in (STATE_ACCEPTED, STATE_AWARDED):
            slot["accepted"] += 1
        if state == STATE_AWARDED:
            slot["awarded"] += 1
        if state in REAL_CASH_STATES:
            slot["paid"] += 1
            slot["cash"] += amount
    out: list[dict[str, Any]] = []
    for channel, slot in buckets.items():
        paid = int(slot["paid"])
        attempts = int(slot["attempts"])
        out.append(
            {
                "channel": channel,
                "attempts": attempts,
                "accepted": int(slot["accepted"]),
                "awarded": int(slot["awarded"]),
                "paid": paid,
                "cash": round(float(slot["cash"]), 2),
                "average_cash": round(float(slot["cash"]) / paid, 2) if paid else None,
                "cash_per_hour": None,  # se completa con horas verificadas del canal
                "acceptance_rate": round(slot["accepted"] / attempts, 3) if attempts else None,
                "validation": channel_validation(paid),
            }
        )
    out.sort(key=lambda c: (-c["paid"], -c["cash"], c["channel"]))
    return out


def gap_to_target(
    target_monthly: float,
    realized_cash: float,
    verifiable_pending: float = 0.0,
    available_hours_per_week: float = DEFAULT_AVAILABLE_HOURS,
) -> dict[str, Any]:
    """Gap engine (spec §18). NUNCA resta potencial ni pipeline especulativo."""
    target = _as_float(target_monthly)
    realized = _as_float(realized_cash)
    pending = _as_float(verifiable_pending)
    gap = max(0.0, target - realized - pending)
    monthly_hours = max(0.0, float(available_hours_per_week or 0.0)) * 4.33
    required_per_hour = round(gap / monthly_hours, 2) if monthly_hours > 0 else None
    return {
        "target_monthly": round(target, 2),
        "realized": round(realized, 2),
        "verifiable_pending": round(pending, 2),
        "speculative_excluded": True,
        "gap": round(gap, 2),
        "monthly_hours_available": round(monthly_hours, 2),
        "required_cash_per_hour": required_per_hour,
        "is_math": True,
        "note": "Cálculo matemático, NO garantía (spec §17).",
    }


def compare_scenario_to_real(
    realized: float,
    tier: str = "central",
    horizon: str = "m1_3",
    custom_scenarios: dict[str, dict[str, tuple[float, float]]] | None = None,
) -> dict[str, Any]:
    """Real vs escenario (spec §20). BELOW / ON TRACK / ABOVE, sin triunfalismo."""
    table = custom_scenarios or PLANNING_SCENARIOS
    tier_key = (tier or "central").strip().lower()
    if tier_key not in SCENARIO_TIERS:
        tier_key = "central"
    band = (table.get(tier_key) or {}).get(horizon)
    if band is None:
        return {"status": "NO_SCENARIO", "tier": tier_key, "horizon": horizon}
    lo, hi = float(band[0]), float(band[1])
    real = _as_float(realized)
    if real < lo:
        status = "BELOW"
    elif real > hi:
        status = "ABOVE"
    else:
        status = "ON_TRACK"
    return {
        "status": status,
        "tier": tier_key,
        "horizon": horizon,
        "realized": round(real, 2),
        "scenario_low": lo,
        "scenario_high": hi,
        "kind": "scenario",
        "label": "PLANNING_SCENARIO",
    }


def scenarios_basis(
    calibration: dict[str, Any] | None = None,
    available_hours_per_week: float | None = None,
) -> dict[str, Any]:
    """Base de cálculo auditable de los escenarios (spec §18/§19/§20).

    NO inventa una fórmula: los escenarios salen de `PLANNING_SCENARIOS`, una
    tabla constante. Lo que se expone aquí son (a) las variables que las bandas
    requerirían para ser alcanzables y (b) el estado de evidencia real de cada
    una, para que nadie lea un rango de planificación como forecast calibrado.

    Regla de honestidad: sin evidencia OBSERVED/CALIBRATED, el estado es
    UNKNOWN y el valor `None` — jamás un supuesto presentado como observado
    (spec §7, §32).
    """
    calib = calibration or {}
    paid = int(calib.get("paid_outcomes", 0) or 0)
    hours = _as_float(available_hours_per_week) if available_hours_per_week is not None else None

    def _unknown(requires: str) -> dict[str, Any]:
        return {"value": None, "evidence": "UNKNOWN", "requires": requires}

    return {
        "formula": None,
        "formula_note": (
            "PLANNING_SCENARIOS es una tabla constante: el código NO deriva los "
            "escenarios de estas variables. Se recalibran solo con datos reales "
            "vía calibrate_scenarios(), que exige >=3 meses."
        ),
        "variables": {
            "capacity_weekly_hours": {
                "value": hours,
                "evidence": "OBSERVED" if hours else "UNKNOWN",
                "source": "mission_hub.daily_minutes * 7 / 60" if hours else None,
            },
            "p_cash": _unknown(">=1 PAID verificado"),
            "acceptance_rate": _unknown(">=1 outcome con veredicto"),
            "time_to_cash": _unknown(">=1 PAID con fecha de cobro"),
            "repeatability": _unknown(">=2 accepted en el mismo canal"),
            "net_cash_per_human_hour": _unknown(">=1 PAID y horas humanas medidas"),
        },
        "per_lane_p_cash": {lane: _unknown(">=1 PAID propio en el lane") for lane in CHANNELS},
        "calibration": {
            "level": int(calib.get("level", 0) or 0),
            "label": calib.get("label", "NO_DATA"),
            "paid_outcomes": paid,
            "net_cash_per_hour": calib.get("net_cash_per_hour"),
            "evidence": "CALIBRATED" if paid >= 3 else ("OBSERVED" if paid == 1 else "UNKNOWN"),
            "recalibrated": False,
            "recalibration_requires_months": 3,
        },
        "excluded_from_cash": {
            "speculative": sorted(SPECULATIVE_STATES),
            "verifiable_pending": sorted(VERIFIABLE_PENDING_STATES),
            "note": "Ninguno de estos estados es caja realizada; PAID/NET si lo son.",
        },
    }


def scenarios_block(
    calibration: dict[str, Any] | None = None,
    available_hours_per_week: float | None = None,
) -> dict[str, Any]:
    """Escenarios siempre etiquetados; largos exigirán evidencia para subir nivel."""
    return {
        "kind": "scenario",
        "label": "PLANNING_SCENARIO",
        "is_forecast": False,
        "horizons": {t: {h: list(v) for h, v in bands.items()} for t, bands in PLANNING_SCENARIOS.items()},
        "basis": scenarios_basis(calibration, available_hours_per_week),
        "long_term": [
            {**item, "monthly_range": list(item["monthly_range"]), "label": "LONG_TERM_SCENARIO"}
            for item in LONG_TERM_SCENARIOS
        ],
    }


def calibrate_scenarios(
    measured_monthly: float | None = None,
    samples: int = 0,
) -> dict[str, Any]:
    """Recalibra escenarios con datos reales (spec §21). Sin datos → NO recalibra."""
    if measured_monthly is None or samples < 3:
        return {"calibrated": False, "reason": "requiere ≥3 meses con datos reales", "scenarios": scenarios_block()}
    measured = _as_float(measured_monthly)
    return {
        "calibrated": True,
        "samples": int(samples),
        "measured_monthly": round(measured, 2),
        "note": "Escenarios recalculados desde lo medido; los rangos originales son hipótesis.",
        "measured_band": (round(measured * 0.6, 2), round(measured * 1.6, 2)),
    }
