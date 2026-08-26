"""OAR Observability Sink — registro persistente + métricas agregadas.

Spec: AI FREE-CLOUD ROUTER §18.

Cada llamada a un modelo registra una línea JSONL en
``data/ai_observability.jsonl`` con redacción de secretos OBLIGATORIA
(sk-*, Bearer, x-api-key jamás tocan disco).

Agregados calculables sin cargar todo el archivo:
success_rate · fallback_rate · avg_latency_ms · tokens por tarea · cost.

Append-only con lock; tolerante a disco lleno (nunca rompe la request de IA).
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger("ownex.ai.observability")


# ── Secret Redaction ─────────────────────────────────────────────────

_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]{8,}", re.IGNORECASE),
    re.compile(r"x-api-key[:\s=]+[A-Za-z0-9._\-]{8,}", re.IGNORECASE),
    re.compile(r"api[_-]?key[\"']?\s*[:=]\s*[\"'][A-Za-z0-9._\-]{8,}[\"']", re.IGNORECASE),
)
_REDACTED = "[REDACTED]"


def redact_secrets(text: str) -> str:
    """Redacta patrones de secretos conocidos. Idempotente."""
    if not text:
        return text
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(_REDACTED, text)
    return text


def _redact_obj(obj: object) -> object:
    """Redacción recursiva para dicts/lists anidados (metadata del evento)."""
    if isinstance(obj, str):
        return redact_secrets(obj)
    if isinstance(obj, dict):
        return {k: _redact_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact_obj(v) for v in obj]
    return obj


# ── Event Model ──────────────────────────────────────────────────────


@dataclass(slots=True)
class AIEventRecord:
    """Una observación de llamada IA (spec §18)."""

    timestamp: str
    task: str  # TaskType value
    provider: str
    model: str
    success: bool
    latency_ms: float
    tokens_in: int = 0
    tokens_out: int = 0
    error: str | None = None
    fallback_used: bool = False
    cost_usd: float = 0.0
    cache_hit: bool = False
    quality_feedback: float | None = None  # 0–1 si hay señal real; nunca inventada

    def to_json(self) -> str:
        clean = _redact_obj(asdict(self))
        return json.dumps(clean, ensure_ascii=False, separators=(",", ":"))


# ── Sink ─────────────────────────────────────────────────────────────


def _default_path() -> Path:
    base = os.environ.get("OWNEX_DATA_DIR")
    root = Path(base) if base else Path(__file__).resolve().parents[2] / "data"
    return root / "ai_observability.jsonl"


class ObservabilitySink:
    """JSONL append-only con métricas agregadas sobre ventana reciente."""

    def __init__(self, path: str | Path | None = None, max_events_in_memory: int = 5000) -> None:
        self._path = Path(path or _default_path())
        self._lock = threading.Lock()
        self._recent: list[AIEventRecord] = []
        self._max_memory = max_events_in_memory

    @property
    def path(self) -> Path:
        return self._path

    def record(self, event: AIEventRecord) -> None:
        """Registra un evento. Jamás lanza: disco lleno/permisos → warning."""
        try:
            line = event.to_json()
            with self._lock:
                self._recent.append(event)
                del self._recent[: -self._max_memory]
                self._path.parent.mkdir(parents=True, exist_ok=True)
                with open(self._path, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
        except Exception as exc:  # pragma: no cover — resiliencia ante I/O rota
            logger.warning("ObservabilitySink no pudo escribir: %s", exc)

    def load_history(self, limit: int = 1000) -> list[AIEventRecord]:
        """Lee las últimas N líneas del JSONL (para agregados tras restart)."""
        if not self._path.exists():
            return []
        out: list[AIEventRecord] = []
        try:
            with open(self._path, encoding="utf-8") as fh:
                for raw in fh.readlines()[-limit:]:
                    try:
                        data = json.loads(raw)
                        data.pop("timestamp", None)
                        # reconstrucción defensiva: campos faltantes → default
                        rec = AIEventRecord(
                            timestamp=data.get("timestamp", ""),
                            task=str(data.get("task", "unknown")),
                            provider=str(data.get("provider", "unknown")),
                            model=str(data.get("model", "unknown")),
                            success=bool(data.get("success", False)),
                            latency_ms=float(data.get("latency_ms", 0.0)),
                            tokens_in=int(data.get("tokens_in", 0)),
                            tokens_out=int(data.get("tokens_out", 0)),
                            error=data.get("error"),
                            fallback_used=bool(data.get("fallback_used", False)),
                            cost_usd=float(data.get("cost_usd", 0.0)),
                            cache_hit=bool(data.get("cache_hit", False)),
                            quality_feedback=data.get("quality_feedback"),
                        )
                        out.append(rec)
                    except (json.JSONDecodeError, ValueError, TypeError):
                        continue  # línea corrupta: skip honesto
        except OSError as exc:  # pragma: no cover
            logger.warning("No se pudo leer historial de observabilidad: %s", exc)
        return out


# ── Aggregates (spec §18) ────────────────────────────────────────────


def aggregate(events: list[AIEventRecord], by_task: bool = False) -> dict:
    """Métricas agregadas. Solo datos reales registrados — cero benchmarks fabricados."""
    total = len(events)
    if total == 0:
        agg: dict = {
            "total": 0,
            "success_rate": None,
            "fallback_rate": None,
            "cache_hit_rate": None,
            "avg_latency_ms": None,
            "tokens_total": 0,
            "cost_usd": 0.0,
        }
        if by_task:
            agg["by_task"] = {}
        return agg

    successes = sum(1 for e in events if e.success)
    fallbacks = sum(1 for e in events if e.fallback_used and not e.cache_hit)
    cache_hits = sum(1 for e in events if e.cache_hit)

    agg = {
        "total": total,
        "success_rate": round(successes / total, 3),
        "fallback_rate": round(fallbacks / total, 3),
        "cache_hit_rate": round(cache_hits / total, 3),
        "avg_latency_ms": round(sum(e.latency_ms for e in events) / total, 1),
        "tokens_total": sum(e.tokens_in + e.tokens_out for e in events),
        "cost_usd": round(sum(e.cost_usd for e in events), 6),
    }

    if by_task:
        tasks: dict[str, list[AIEventRecord]] = {}
        for e in events:
            tasks.setdefault(e.task, []).append(e)
        agg["by_task"] = {
            task: {
                "total": len(group),
                "success_rate": round(sum(1 for x in group if x.success) / len(group), 3),
                "avg_latency_ms": round(sum(x.latency_ms for x in group) / len(group), 1),
                "cost_usd": round(sum(x.cost_usd for x in group), 6),
            }
            for task, group in sorted(tasks.items())
        }

    # Por provider: uptime/success relativo observado (§19 learning input)
    providers: dict[str, list[AIEventRecord]] = {}
    for e in events:
        providers.setdefault(e.provider, []).append(e)
    agg["by_provider"] = {
        p: {
            "total": len(g),
            "success_rate": round(sum(1 for x in g if x.success) / len(g), 3),
            "avg_latency_ms": round(sum(x.latency_ms for x in g) / len(g), 1),
            "fallback_rate": round(sum(1 for x in g if x.fallback_used) / len(g), 3),
        }
        for p, g in sorted(providers.items())
    }
    return agg


# ── Singleton ────────────────────────────────────────────────────────

_sink: ObservabilitySink | None = None


def get_observability_sink() -> ObservabilitySink:
    global _sink
    if _sink is None:
        _sink = ObservabilitySink()
    return _sink


def record_ai_event(**kwargs: object) -> None:
    """Conveniencia: record_ai_event(task=..., provider=..., ...)"""
    if "timestamp" not in kwargs:
        kwargs["timestamp"] = datetime.now(UTC).isoformat()
    get_observability_sink().record(AIEventRecord(**kwargs))  # type: ignore[arg-type]
