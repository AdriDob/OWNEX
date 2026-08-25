"""Availability Intelligence — señal real de task_available (audit P0-4).

Estados del spec (BACKEND ALPHA 1.0 §7): AVAILABLE | LIMITED | UNKNOWN |
UNAVAILABLE | STALE. La disponibilidad entra al ranking económico vía
``economics.TaskAvailability`` (SSOT de EV).

Regla de honestidad: este motor NUNCA inventa disponibilidad. Solo produce
estados "known" a partir de observaciones registradas por productores reales
(adapters que devolvieron items, ciclos de discovery); sin observación →
UNKNOWN; observación vencida → STALE. El multiplicador LIMITED=0.5 es una
POLÍTICA documentada sobre un hecho observado (había pocos items), no una
probabilidad fabricada.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

# Política de mapeo observación→multiplicador (documentada, testeada).
MULTIPLIER_AVAILABLE = 1.0
MULTIPLIER_LIMITED = 0.5
MULTIPLIER_UNAVAILABLE = 0.0

# Freshness: una observación de discovery más vieja que esto es STALE.
FRESHNESS_DAYS = 7
_FRESHNESS_SECONDS = FRESHNESS_DAYS * 86400


class AvailabilityState(StrEnum):
    AVAILABLE = "available"
    LIMITED = "limited"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"
    STALE = "stale"


@dataclass
class Observation:
    """Hecho observado por un productor (adapter/ciclo real)."""

    items_seen: int
    observed_at: float  # epoch seconds
    source: str = "discovery"

    def to_dict(self) -> dict:
        return {
            "items_seen": self.items_seen,
            "observed_at": self.observed_at,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Observation:
        return cls(
            items_seen=int(data.get("items_seen", 0)),
            observed_at=float(data.get("observed_at", 0.0)),
            source=str(data.get("source", "discovery")),
        )


@dataclass(frozen=True)
class PlatformAvailability:
    """Veredicto de disponibilidad para una plataforma."""

    platform: str
    state: AvailabilityState
    reason: str
    observed_at: float | None = None
    items_seen: int | None = None

    def as_dict(self) -> dict:
        return {
            "platform": self.platform,
            "state": self.state.value,
            "reason": self.reason,
            "observed_at": self.observed_at,
            "items_seen": self.items_seen,
        }


def _default_store_path() -> Path:
    """Patrón workbank: OWNEX_DATA_DIR en frozen, ./data en dev."""
    base = os.environ.get("OWNEX_DATA_DIR")
    root = Path(base) if base else Path(__file__).resolve().parents[2] / "data"
    return root / "availability.json"


def state_from_observation(obs: Observation, now: float) -> tuple[AvailabilityState, str]:
    """Clasifica una observación fresca (pura, testeable)."""
    age = now - obs.observed_at
    if age < 0:
        # Reloj futuro: tratar como fresco (observación válida).
        age = 0.0
    if age > _FRESHNESS_SECONDS:
        return AvailabilityState.STALE, (
            f"observación de {obs.source} tiene {age / 86400:.1f} días (> {FRESHNESS_DAYS})"
        )
    if obs.items_seen <= 0:
        return AvailabilityState.UNAVAILABLE, (f"{obs.source} devolvió 0 items hace {int(age / 3600)}h")
    if obs.items_seen < 3:
        return AvailabilityState.LIMITED, (f"{obs.source} observó solo {obs.items_seen} items")
    return (
        AvailabilityState.AVAILABLE,
        f"{obs.source} observó {obs.items_seen} items",
    )


class AvailabilityMonitor:
    """Registro persistente de observaciones + veredicto por plataforma."""

    def __init__(self, store_path: str | Path | None = None) -> None:
        self._path = Path(store_path or _default_store_path())
        self._observations: dict[str, dict] = {}
        try:
            if self._path.exists():
                self._observations = json.loads(self._path.read_text())
        except Exception:
            self._observations = {}

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(self._observations, indent=2))
        except Exception:
            pass  # best-effort: la señal nunca rompe el pipeline

    def record(self, platform: str, items_seen: int, *, source: str = "discovery") -> None:
        """Productor: registrar el resultado de un fetch real."""
        key = platform.strip().lower()
        if not key:
            return
        self._observations[key] = Observation(
            items_seen=max(0, int(items_seen)), observed_at=time.time(), source=source
        ).to_dict()
        self._save()

    def assess(self, platform: str, *, now: float | None = None) -> PlatformAvailability:
        """Veredicto honesto: UNKNOWN si jamás se observó nada."""
        key = platform.strip().lower()
        raw = self._observations.get(key)
        current = now if now is not None else time.time()
        if raw is None:
            return PlatformAvailability(
                platform=key,
                state=AvailabilityState.UNKNOWN,
                reason="sin observaciones registradas",
            )
        obs = Observation.from_dict(raw)
        state, reason = state_from_observation(obs, current)
        return PlatformAvailability(
            platform=key,
            state=state,
            reason=reason,
            observed_at=obs.observed_at,
            items_seen=obs.items_seen,
        )

    def task_availability_for(self, platform: str, *, now: float | None = None):
        """Puente al SSOT económico.

        known SOLO para hechos observados frescos (AVAILABLE/LIMITED/
        UNAVAILABLE). UNKNOWN y STALE → TaskAvailability.unknown() para que
        economics excluya el factor y emita su warning.
        """
        from cores.direct_work_engine.economics import TaskAvailability

        verdict = self.assess(platform, now=now)
        multipliers = {
            AvailabilityState.AVAILABLE: MULTIPLIER_AVAILABLE,
            AvailabilityState.LIMITED: MULTIPLIER_LIMITED,
            AvailabilityState.UNAVAILABLE: MULTIPLIER_UNAVAILABLE,
        }
        multiplier = multipliers.get(verdict.state)
        if multiplier is None:
            return TaskAvailability.unknown(), verdict
        return TaskAvailability.of(multiplier), verdict

    def snapshot(self) -> list[dict]:
        """Inventario observable completo (regla: si no es visible, no existe)."""
        return [self.assess(platform).as_dict() for platform in sorted(self._observations)]


_MONITOR_SINGLETON: AvailabilityMonitor | None = None


def get_availability_monitor() -> AvailabilityMonitor:
    """Singleton del monitor (patrón del proyecto; reset en tests)."""
    global _MONITOR_SINGLETON
    if _MONITOR_SINGLETON is None:
        _MONITOR_SINGLETON = AvailabilityMonitor()
    return _MONITOR_SINGLETON


def reset_availability_monitor() -> None:
    """Hook de tests: fuerza re-creación (respeta OWNEX_DATA_DIR actual)."""
    global _MONITOR_SINGLETON
    _MONITOR_SINGLETON = None
