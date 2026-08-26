"""OAR Resilience Layer — ErrorClassifier + QuotaTracker + DegradedMode.

Spec: AI FREE-CLOUD ROUTER §9-11, §25.

- ErrorClassifier: mapea errores HTTP/excepciones a HealthStatus con política
  de retry explícita (nunca martillar errores permanentes de configuración).
- QuotaTracker: contadores observados por ventana (req/min, req/día, tokens/día).
  Límite desconocido = UNKNOWN → factor 0.85 (penaliza levemente, jamás asume
  ilimitado). Nunca inventa cuotas.
- DegradedMode: estado global del subsistema IA (NORMAL/DEGRADED/OFFLINE_AI)
  publicado al EventBus; el sistema continúa con reglas deterministas cuando
  no hay LLM disponible (spec §25 — resilience sin drama).

Sin I/O de red. Test-first. Thread-safe vía lock simple.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

logger = logging.getLogger("ownex.ai.resilience")


# ── Error Classification (spec §9) ───────────────────────────────────


class RetryPolicy(Enum):
    """Qué hacer ante un error clasificado."""

    RETRY_SAME = "retry_same"  # transitorio — reintentar en el mismo provider tras backoff corto
    FALLBACK = "fallback"  # saltar a siguiente provider de la cadena
    CIRCUIT = "circuit"  # contar para circuit breaker (repetido → abrir)
    PERMANENT = "permanent"  # config rota — NO reintentar ni martillar; alertar


@dataclass(slots=True)
class ClassifiedError:
    """Resultado de clasificar un error de proveedor."""

    status: str  # valor de HealthStatus (sin import circular)
    policy: RetryPolicy
    retry_after_seconds: float | None = None
    reason: str = ""

    @property
    def is_permanent(self) -> bool:
        return self.policy is RetryPolicy.PERMANENT


# Patrones de texto → clasificación (case-insensitive)
_PATTERNS: tuple[tuple[str, str, RetryPolicy], ...] = (
    ("rate limit", "quota_exceeded", RetryPolicy.CIRCUIT),
    ("too many requests", "quota_exceeded", RetryPolicy.CIRCUIT),
    ("quota", "quota_exceeded", RetryPolicy.CIRCUIT),
    ("insufficient", "quota_exceeded", RetryPolicy.PERMANENT),
    ("billing", "quota_exceeded", RetryPolicy.PERMANENT),
    ("credit", "quota_exceeded", RetryPolicy.CIRCUIT),
    ("unauthorized", "auth_failed", RetryPolicy.PERMANENT),
    ("forbidden", "auth_failed", RetryPolicy.PERMANENT),
    ("invalid api key", "auth_failed", RetryPolicy.PERMANENT),
    ("authentication", "auth_failed", RetryPolicy.PERMANENT),
    ("context length", "degraded", RetryPolicy.PERMANENT),
    ("max_tokens", "degraded", RetryPolicy.PERMANENT),
    ("context window", "degraded", RetryPolicy.PERMANENT),
    ("model not found", "unhealthy", RetryPolicy.PERMANENT),
    ("does not exist", "unhealthy", RetryPolicy.PERMANENT),
    ("timeout", "unhealthy", RetryPolicy.RETRY_SAME),
    ("timed out", "unhealthy", RetryPolicy.RETRY_SAME),
    ("connection", "unhealthy", RetryPolicy.FALLBACK),
    ("temporarily", "degraded", RetryPolicy.RETRY_SAME),
)

# Códigos HTTP → (HealthStatus, RetryPolicy)
_STATUS_MAP: dict[int, tuple[str, RetryPolicy]] = {
    401: ("auth_failed", RetryPolicy.PERMANENT),
    403: ("auth_failed", RetryPolicy.PERMANENT),
    402: ("quota_exceeded", RetryPolicy.PERMANENT),
    408: ("unhealthy", RetryPolicy.RETRY_SAME),
    413: ("degraded", RetryPolicy.PERMANENT),  # payload too large ≈ contexto
    422: ("degraded", RetryPolicy.PERMANENT),
    429: ("quota_exceeded", RetryPolicy.CIRCUIT),
    500: ("unhealthy", RetryPolicy.FALLBACK),
    502: ("unhealthy", RetryPolicy.FALLBACK),
    503: ("unhealthy", RetryPolicy.FALLBACK),
    504: ("unhealthy", RetryPolicy.RETRY_SAME),
}


class ErrorClassifier:
    """Clasifica excepciones/errores de proveedores a HealthStatus + política."""

    def classify(
        self,
        error: Exception | str | None,
        status_code: int | None = None,
    ) -> ClassifiedError:
        """Clasifica por código HTTP primero, luego por mensaje, luego default."""
        if error is None and status_code is None:
            return ClassifiedError("unknown", RetryPolicy.FALLBACK, reason="no error info")

        # 1) Código HTTP tiene prioridad (más confiable que parsear texto)
        if status_code is not None:
            mapped = _STATUS_MAP.get(status_code)
            if mapped:
                st, pol = mapped
                retry_after = self._extract_retry_after(str(error)) if pol is RetryPolicy.CIRCUIT else None
                return ClassifiedError(st, pol, retry_after_seconds=retry_after, reason=f"http_{status_code}")

        # 2) Mensaje
        text = str(error or "")
        low = text.lower()
        for needle, status, policy in _PATTERNS:
            if needle in low:
                retry_after = self._extract_retry_after(text) if policy is RetryPolicy.CIRCUIT else None
                return ClassifiedError(status, policy, retry_after_seconds=retry_after, reason=f"pattern:{needle}")

        # 3) Timeout genérico por tipo de excepción
        timeout_types: tuple[type[BaseException], ...]
        try:
            import httpx as _httpx  # lazy: no hard dependency en tests unitarios

            timeout_types = (TimeoutError, _httpx.TimeoutException)
        except ImportError:  # pragma: no cover
            timeout_types = (TimeoutError,)
        if isinstance(error, BaseException) and isinstance(error, timeout_types):
            return ClassifiedError("unhealthy", RetryPolicy.RETRY_SAME, reason="exception_timeout")

        # 4) Default conservador: fallback (no circuit, no permanent)
        return ClassifiedError("unknown", RetryPolicy.FALLBACK, reason="unclassified")

    @staticmethod
    def _extract_retry_after(text: str) -> float | None:
        """Extrae segundos de 'retry after X' si el proveedor lo informa."""
        low = text.lower()
        for marker in ("retry-after", "retry after", "try again in"):
            idx = low.find(marker)
            if idx == -1:
                continue
            tail = text[idx + len(marker) :]
            digits = ""
            for ch in tail:
                if ch.isdigit():
                    digits += ch
                elif digits:
                    break
            if digits:
                try:
                    val = float(digits)
                    # "try again in 2h" etc.: unidad después del número
                    unit = tail.lstrip()[len(digits) :].lstrip()[:1].lower()
                    if unit == "h":
                        return val * 3600
                    if unit == "m" and not tail.lstrip()[len(digits) :].lstrip()[:2].lower().startswith("ms"):
                        return val * 60
                    return val
                except ValueError:  # pragma: no cover
                    continue
        return None


# ── Quota Tracking (spec §11) ────────────────────────────────────────


@dataclass(slots=True)
class QuotaWindow:
    """Ventana deslizante de consumo observado."""

    requests: deque[float] = field(default_factory=deque)
    tokens_today: int = 0
    day_key: str = ""


UNKNOWN_QUOTA_FACTOR = 0.85  # spec: UNKNOWN nunca se trata como ilimitado


class QuotaTracker:
    """Contadores observados de consumo por proveedor.

    Filosofía del spec §11: si el proveedor no informa límites → UNKNOWN;
    registrar consumo observado y penalizar levemente en routing hasta tener
    datos. NUNCA asumir UNLIMITED.
    """

    MINUTE = 60.0
    DAY = 86400.0

    def __init__(self) -> None:
        # RLock: quota_factor() llama observed_rpm() sosteniendo el lock
        self._lock = threading.RLock()
        self._windows: dict[str, QuotaWindow] = defaultdict(QuotaWindow)
        # Límites declarados (None = UNKNOWN). Settable vía headers o config.
        self._limits: dict[str, dict[str, int | None]] = defaultdict(lambda: {"rpm": None, "rpd": None, "tpd": None})

    def set_declared_limit(
        self, provider_id: str, rpm: int | None = None, rpd: int | None = None, tpd: int | None = None
    ) -> None:
        """Registra límites DECLARADOS por el proveedor (o los deja UNKNOWN)."""
        with self._lock:
            lim = self._limits[provider_id]
            if rpm is not None:
                lim["rpm"] = rpm
            if rpd is not None:
                lim["rpd"] = rpd
            if tpd is not None:
                lim["tpd"] = tpd

    def record_request(self, provider_id: str, tokens: int = 0, ts: float | None = None) -> None:
        now = ts if ts is not None else time.time()
        with self._lock:
            win = self._windows[provider_id]
            day_key = datetime.now(UTC).strftime("%Y-%m-%d")
            if win.day_key != day_key:
                win.tokens_today = 0
                win.day_key = day_key
            win.requests.append(now)
            win.tokens_today += max(0, tokens)

    def observed_rpm(self, provider_id: str, ts: float | None = None) -> int:
        now = ts if ts is not None else time.time()
        with self._lock:
            win = self._windows[provider_id]
            cutoff = now - self.MINUTE
            while win.requests and win.requests[0] < cutoff:
                win.requests.popleft()
            return len(win.requests)

    def quota_factor(self, provider_id: str, ts: float | None = None) -> float:
        """Factor multiplicador de score para el router (0.0–1.0).

        - Límite conocido y consumo cerca → factor proporcional al margen.
        - Límite UNKNOWN → 0.85 fijo (leve penalización honesta).
        - Límite excedido → 0.0 (router lo descarta).
        """
        now = ts if ts is not None else time.time()
        with self._lock:
            lim = self._limits[provider_id]
            win = self._windows[provider_id]
            factors: list[float] = []

            for kind, used in (
                ("rpm", float(self.observed_rpm(provider_id, now))),
                ("rpd", float(len([r for r in win.requests if r >= now - self.DAY]))),
            ):
                limit = lim[kind]
                if limit is None or limit <= 0:
                    continue
                ratio = used / float(limit)
                factors.append(max(0.0, 1.0 - ratio))

            if lim["tpd"] is not None and lim["tpd"] > 0:
                factors.append(max(0.0, 1.0 - win.tokens_today / float(lim["tpd"])))

            if not factors:
                return UNKNOWN_QUOTA_FACTOR
            return round(min(factors), 3)

    def snapshot(self, provider_id: str) -> dict:
        """Estado legible para frontend/observability."""
        with self._lock:
            lim = dict(self._limits[provider_id])
            win = self._windows[provider_id]
            return {
                "rpm_observed": self.observed_rpm(provider_id),
                "requests_stored": len(win.requests),
                "tokens_today": win.tokens_today,
                "day": win.day_key or datetime.now(UTC).strftime("%Y-%m-%d"),
                "limits": {k: v for k, v in lim.items()},
                "limits_known": any(v is not None for v in lim.values()),
            }


# ── Degraded Mode (spec §25) ─────────────────────────────────────────


class AISystemMode(Enum):
    NORMAL = "normal"  # al menos un provider LOCAL o FREE healthy
    DEGRADED = "degraded"  # solo fallback local/reglas; calidad reducida
    OFFLINE_AI = "offline_ai"  # sin LLM alguno; sistema continúa determinista


class DegradedMode:
    """Estado global del subsistema IA, publicado al EventBus."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._mode = AISystemMode.NORMAL
        self._since = datetime.now(UTC).isoformat()
        self._reason = ""
        self._events: list[dict] = []

    @property
    def mode(self) -> AISystemMode:
        with self._lock:
            return self._mode

    def evaluate(self, healthy_providers: list[str], tier_of: dict[str, int]) -> AISystemMode:
        """Recalcula modo según providers healthy.

        tier_of: provider_id → ProviderTier numérico (LOCAL=1, FREE=2, ...).
        NORMAL requiere ≥1 provider tier ≤ FREE (1 o 2) healthy.
        Solo CHEAP+ healthy → DEGRADED. Nada healthy → OFFLINE_AI.
        """
        good = [p for p in healthy_providers if tier_of.get(p, 99) <= 2]
        paid_only = [p for p in healthy_providers if tier_of.get(p, 99) > 2]
        if good:
            new_mode, reason = AISystemMode.NORMAL, f"{len(good)} free/local provider(s) healthy"
        elif paid_only:
            new_mode, reason = AISystemMode.DEGRADED, f"solo providers pagos healthy: {paid_only}"
        else:
            new_mode, reason = AISystemMode.OFFLINE_AI, "ningún provider LLM disponible"

        changed = False
        with self._lock:
            if new_mode is not self._mode:
                changed = True
                self._mode = new_mode
                self._since = datetime.now(UTC).isoformat()
            self._reason = reason
            event = {
                "ts": datetime.now(UTC).isoformat(),
                "mode": new_mode.value,
                "reason": reason,
                "healthy": list(healthy_providers),
            }
            if changed:
                self._events.append(event)
                # mantener historial acotado
                del self._events[:-50]

        if changed:
            self._publish(new_mode, reason)
        return new_mode

    @staticmethod
    def _publish(mode: AISystemMode, reason: str) -> None:
        try:
            from cores.events.event_bus import get_event_bus

            get_event_bus().publish("ai:mode_changed", mode=mode.value, reason=reason)
        except Exception as exc:  # pragma: no cover — bus caído no rompe resilience
            logger.warning("No se pudo publicar ai:mode_changed: %s", exc)

    def status(self) -> dict:
        with self._lock:
            return {
                "mode": self._mode.value,
                "since": self._since,
                "reason": self._reason,
            }

    def recent_events(self, limit: int = 10) -> list[dict]:
        with self._lock:
            return list(self._events[-limit:])


# ── Singletons ───────────────────────────────────────────────────────

_error_classifier: ErrorClassifier | None = None
_quota_tracker: QuotaTracker | None = None
_degraded_mode: DegradedMode | None = None


def get_error_classifier() -> ErrorClassifier:
    global _error_classifier
    if _error_classifier is None:
        _error_classifier = ErrorClassifier()
    return _error_classifier


def get_quota_tracker() -> QuotaTracker:
    global _quota_tracker
    if _quota_tracker is None:
        _quota_tracker = QuotaTracker()
    return _quota_tracker


def get_degraded_mode() -> DegradedMode:
    global _degraded_mode
    if _degraded_mode is None:
        _degraded_mode = DegradedMode()
    return _degraded_mode
