"""APP FACTORY experiments — NEXA vs FOCUS validation (pre-BUILD).

Complementa asset_factory (que nace en IDEA con gate demanda_observable):
esto mide la demanda observable ANTES de que el asset exista.

Eventos (los 7 + email, nunca PII salvo email_signup):
landing_view → demo_started → goal_created → plan_generated →
plan_saved → return_visit → price_intent (+ email_signup)

Persistencia: JSONL append-only en OWNEX_DATA_DIR/app_factory_events.jsonl
(data-dir aware, path inyectable, best-effort, nunca raisea en lectura).
Overview: conteos por experimento + Demand Score 0-100 o None (UNKNOWN).
Emails: solo conteo en overview, jamás lista cruda.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.app_factory.experiments")

EXPERIMENTS: dict[str, dict[str, Any]] = {
    "nexa": {
        "id": "nexa",
        "name": "NEXA",
        "positioning": "Turn your goals into daily actions.",
        "promise": "Tell NEXA what you want. Get your next action.",
        "pricing": {"monthly": 3.99, "yearly": 39.99, "lifetime": 79.99},
        "landing": "app-validation/experiments/nexa/",
    },
    "focus": {
        "id": "focus",
        "name": "FOCUS",
        "positioning": "Plan your day without fighting your brain.",
        "promise": "Less planning. Less guilt. Just the next thing that matters.",
        "pricing": {"monthly": 4.99, "yearly": 49.99, "lifetime": 99.0},
        "landing": "app-validation/experiments/focus/",
    },
}

VALID_EVENTS = frozenset(
    {
        "landing_view",
        "demo_started",
        "goal_created",
        "plan_generated",
        "plan_saved",
        "return_visit",
        "price_intent",
        "email_signup",
    }
)

PRICE_PRO_ACTION = "clicked_pro"


def _events_path(store_path: str | Path | None = None) -> Path:
    if store_path:
        return Path(store_path)
    base = Path(os.environ.get("OWNEX_DATA_DIR", "data"))
    return base / "app_factory_events.jsonl"


def list_experiments() -> list[dict[str, Any]]:
    """Registry estático NEXA/FOCUS (posicionamiento + pricing hipótesis)."""
    return [dict(v) for v in EXPERIMENTS.values()]


def record_event(
    experiment: str,
    event: str,
    properties: dict[str, Any] | None = None,
    session_id: str = "",
    email: str = "",
    store_path: str | Path | None = None,
) -> dict[str, Any]:
    """Append 1 evento. ValueError si experimento/evento inválido (→422)."""
    exp = (experiment or "").strip().lower()
    evt = (event or "").strip()
    if exp not in EXPERIMENTS:
        raise ValueError(f"experiment debe ser {'|'.join(sorted(EXPERIMENTS))}")
    if evt not in VALID_EVENTS:
        raise ValueError(f"event debe ser uno de {sorted(VALID_EVENTS)}")
    props = dict(properties or {})
    row: dict[str, Any] = {
        "ts": datetime.now(UTC).isoformat(),
        "experiment": exp,
        "event": evt,
        "session_id": (session_id or "")[:64],
        "properties": {k: props[k] for k in list(props)[:20]},
    }
    if evt == "email_signup":
        clean = (email or props.get("email") or "").strip().lower()
        if "@" not in clean or "." not in clean or len(clean) > 254:
            raise ValueError("email inválido")
        row["email"] = clean
    path = _events_path(store_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError as exc:
        logger.warning("app-factory: no se pudo persistir evento: %s", exc)
    return {"ok": True, "experiment": exp, "event": evt}


def _read_events(store_path: str | Path | None = None) -> list[dict[str, Any]]:
    path = _events_path(store_path)
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("experiment") in EXPERIMENTS and row.get("event") in VALID_EVENTS:
                out.append(row)
    except OSError as exc:
        logger.warning("app-factory: no se pudo leer eventos: %s", exc)
    return out


def _clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def demand_score(counts: dict[str, int]) -> float | None:
    """0-100 o None (UNKNOWN sin landing_view). Hipótesis, no ley física."""
    views = counts.get("landing_view", 0)
    if views <= 0:
        return None
    demo = _clamp01(counts.get("demo_started", 0) / views)
    creation = _clamp01(counts.get("goal_created", 0) / views)
    save = _clamp01((counts.get("plan_saved", 0) + counts.get("email_signup", 0)) / 2 / views)
    ret = _clamp01(counts.get("return_visit", 0) / views)
    pay = _clamp01(counts.get("price_pro", 0) / views)
    return round((25 * demo + 20 * creation + 20 * save + 15 * ret + 20 * pay), 1)


def _verdict(views: int, score: float | None, emails: int) -> str:
    if views <= 0:
        return "NO_DATA"
    if views < 50:
        return "TESTING"
    if score is not None and score >= 40 and emails >= 5:
        return "SIGNAL"
    if views >= 100 and (score or 0) < 15:
        return "KILL_CANDIDATE"
    return "TESTING"


def get_overview(store_path: str | Path | None = None) -> dict[str, Any]:
    """Conteos + Demand Score + veredicto por experimento. Nunca raisea."""
    try:
        rows = _read_events(store_path)
    except Exception as exc:  # noqa: BLE001 — overview jamás 500
        logger.warning("app-factory: overview degradado: %s", exc)
        rows = []
    per: dict[str, dict[str, int]] = {exp: {e: 0 for e in VALID_EVENTS} for exp in EXPERIMENTS}
    pro: dict[str, int] = dict.fromkeys(EXPERIMENTS, 0)
    emails: dict[str, int] = dict.fromkeys(EXPERIMENTS, 0)
    for r in rows:
        exp, evt = r["experiment"], r["event"]
        per[exp][evt] += 1
        if evt == "price_intent" and (r.get("properties") or {}).get("action") == PRICE_PRO_ACTION:
            pro[exp] += 1
        if evt == "email_signup":
            emails[exp] += 1
    experiments: dict[str, Any] = {}
    for exp in EXPERIMENTS:
        counts = dict(per[exp])
        counts["price_pro"] = pro[exp]
        score = demand_score(counts)
        views = counts.get("landing_view", 0)
        experiments[exp] = {
            "counts": counts,
            "emails": emails[exp],
            "demand_score": score,
            "verdict": _verdict(views, score, emails[exp]),
        }
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_events": len(rows),
        "experiments": experiments,
    }
