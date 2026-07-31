"""Learning Loop — feedback desde el Validation Engine hacia los reasoners.

Registra outcomes de validaciones por target x vuln_type para que los
reasoners puedan ajustar sus confianzas previas. También expone métricas
agregadas que alimentan el Capital Dashboard.

Pipeline:
  ValidationEngine.record_outcome() → LearningDB.record(...)
    → adjust confidence priors per (target_id, vuln_type)
    → expose aggregate stats
"""

from __future__ import annotations

import json
import logging
import os
import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("orion.core.validation.learning")

# ── Learning data directory ──────────────────────────────────────

LEARNING_DIR = Path(os.environ.get("ORION_DATA_DIR", Path.home() / ".orion" / "data" / "learning"))
LEARNING_FILE = LEARNING_DIR / "outcomes.jsonl"

_LEARNING_LOCK = threading.Lock()

# ── Outcome records ──────────────────────────────────────────────


@dataclass
class ValidationOutcome:
    """Registro de un intento de validación individual."""

    target_id: int
    target_name: str
    vulnerability_type: str
    confidence: float
    promoted: bool
    severity: str
    endpoint_path: str
    method: str
    duration_ms: float
    signals_count: int
    reproducible: bool
    timestamp: str = ""


def _ensure_dir() -> None:
    LEARNING_DIR.mkdir(parents=True, exist_ok=True)


def _serialize_outcome(outcome: ValidationOutcome) -> str:
    return json.dumps({
        "target_id": outcome.target_id,
        "target_name": outcome.target_name,
        "vuln_type": outcome.vulnerability_type,
        "confidence": outcome.confidence,
        "promoted": outcome.promoted,
        "severity": outcome.severity,
        "endpoint_path": outcome.endpoint_path,
        "method": outcome.method,
        "duration_ms": outcome.duration_ms,
        "signals_count": outcome.signals_count,
        "reproducible": outcome.reproducible,
        "timestamp": outcome.timestamp or datetime.now(UTC).isoformat(),
    })


def record_outcome(outcome: ValidationOutcome) -> None:
    """Persiste un outcome en el archivo JSONL."""
    _ensure_dir()
    line = _serialize_outcome(outcome)
    with _LEARNING_LOCK, open(LEARNING_FILE, "a") as f:
        f.write(line + "\n")
    logger.debug(
        "[LEARNING] Recorded: target=%d vuln=%s confidence=%.1f%% promoted=%s",
        outcome.target_id,
        outcome.vulnerability_type,
        outcome.confidence * 100,
        outcome.promoted,
    )


def record_outcomes(batch: list[ValidationOutcome]) -> None:
    """Persiste múltiples outcomes en batch."""
    _ensure_dir()
    lines = [_serialize_outcome(o) for o in batch]
    with _LEARNING_LOCK, open(LEARNING_FILE, "a") as f:
        for line in lines:
            f.write(line + "\n")
    logger.info("[LEARNING] Recorded %d outcomes in batch", len(batch))


# ── Aggregation & priors ─────────────────────────────────────────


def _load_outcomes(limit: int = 10000) -> list[dict[str, Any]]:
    """Carga outcomes del archivo JSONL."""
    if not LEARNING_FILE.exists():
        return []
    outcomes: list[dict[str, Any]] = []
    with _LEARNING_LOCK, open(LEARNING_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    outcomes.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            if len(outcomes) >= limit:
                break
    return outcomes


def _aggregate_by_target_vuln(
    outcomes: list[dict[str, Any]],
) -> dict[tuple[int, str], dict[str, Any]]:
    """Agrupa outcomes por (target_id, vuln_type) y calcula stats."""
    buckets: dict[tuple[int, str], list[dict]] = defaultdict(list)
    for o in outcomes:
        key = (o.get("target_id", 0), o.get("vuln_type", "unknown"))
        buckets[key].append(o)

    result: dict[tuple[int, str], dict[str, Any]] = {}
    for key, items in buckets.items():
        total = len(items)
        promoted = sum(1 for i in items if i.get("promoted", False))
        avg_confidence = sum(i.get("confidence", 0.0) for i in items) / total if total else 0.0
        severities = [i.get("severity", "medium") for i in items]
        result[key] = {
            "total_validations": total,
            "promoted_count": promoted,
            "promotion_rate": promoted / total if total else 0.0,
            "avg_confidence": avg_confidence,
            "avg_severity": max(set(severities), key=severities.count),  # mode
            "last_timestamp": max(i.get("timestamp", "") for i in items),
        }
    return result


def get_prior(
    target_id: int,
    vulnerability_type: str,
    fallback_confidence: float = 0.3,
) -> float:
    """Retorna confianza previa ajustada para un (target, vuln_type).

    Si hay historial, ajusta la confianza según la tasa de promoción previa.
    Si no hay historial, retorna fallback_confidence.
    """
    outcomes = _load_outcomes(limit=5000)
    agg = _aggregate_by_target_vuln(outcomes)
    key = (target_id, vulnerability_type.lower())
    if key not in agg:
        return fallback_confidence
    stats = agg[key]
    if stats["total_validations"] < 3:
        return fallback_confidence
    rate = stats["promotion_rate"]
    avg = stats["avg_confidence"]
    return avg * 0.6 + rate * 0.4


def get_target_stats(target_id: int) -> dict[str, Any]:
    """Retorna stats agregados para un target."""
    outcomes = _load_outcomes(limit=5000)
    target_outcomes = [o for o in outcomes if o.get("target_id") == target_id]
    if not target_outcomes:
        return {
            "target_id": target_id,
            "total_validations": 0,
            "promoted_count": 0,
            "by_vuln_type": {},
        }

    agg = _aggregate_by_target_vuln(target_outcomes)
    by_vuln = {
        vt: stats
        for (tid, vt), stats in agg.items()
        if tid == target_id
    }
    total = sum(s["total_validations"] for s in by_vuln.values())
    promoted = sum(s["promoted_count"] for s in by_vuln.values())
    return {
        "target_id": target_id,
        "total_validations": total,
        "promoted_count": promoted,
        "promotion_rate": promoted / total if total else 0.0,
        "by_vuln_type": by_vuln,
    }


def get_all_stats() -> dict[int, dict[str, Any]]:
    """Retorna stats agregados para todos los targets."""
    outcomes = _load_outcomes(limit=10000)
    if not outcomes:
        return {}

    agg = _aggregate_by_target_vuln(outcomes)
    # Reorganizar por target_id
    by_target: dict[int, dict] = {}
    for (tid, vt), stats in agg.items():
        if tid not in by_target:
            by_target[tid] = {
                "target_id": tid,
                "total_validations": 0,
                "promoted_count": 0,
                "by_vuln_type": {},
            }
        by_target[tid]["by_vuln_type"][vt] = stats
        by_target[tid]["total_validations"] += stats["total_validations"]
        by_target[tid]["promoted_count"] += stats["promoted_count"]

    for _tid, stats in by_target.items():
        t = stats["total_validations"]
        stats["promotion_rate"] = stats["promoted_count"] / t if t else 0.0

    return by_target
