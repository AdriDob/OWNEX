"""Per-connection permission modes — explicit, revocable, audited autonomy.

Canonical implementation of the OWNEX autonomy ladder (Investment Hub §H).
Each external connection (broker, exchange, data source) has its OWN mode:
there is no global "trading enabled" switch that silently upgrades every
provider.

Ladder (only grows one rung at a time, never by accident):

    DISCONNECTED -> READ_ONLY -> MONITORING -> PAPER_TRADING
                 -> PRE_TRADE_VALIDATION -> CONFIRMATION_REQUIRED
                 -> LIVE_TRADING_AUTHORIZED

Rules enforced here:
  - Default mode for an unknown provider is ``DISCONNECTED`` (deny by default).
  - Escalating to ``LIVE_TRADING_AUTHORIZED`` requires an explicit
    ``acknowledge_risk`` flag from a human action; code paths that forget it
    are rejected. No automatic escalation exists.
  - Downgrade / revoke is ALWAYS allowed and never requires acknowledgement.
  - ``FUNDS_TRANSFER`` and ``WITHDRAW`` capabilities exist only to be denied:
    no mode grants them. OWNEX never moves money.
  - A read permission never implies order permission: LIVE_ORDER is only
    granted by the two highest modes.

State: ``<data_dir>/connections/permissions.json`` (mode per provider).
Audit: ``<data_dir>/connections/permissions_log.jsonl`` (append-only, no secrets).
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from cores.env.config import get_config

logger = logging.getLogger("ownex.connections.permissions")

_SAFE_NAME = re.compile(r"[^a-z0-9_.-]+")
MAX_AUDIT_ENTRIES = 500


class PermissionMode(StrEnum):
    """Autonomy level granted to one external connection."""

    DISCONNECTED = "DISCONNECTED"
    READ_ONLY = "READ_ONLY"
    MONITORING = "MONITORING"
    PAPER_TRADING = "PAPER_TRADING"
    PRE_TRADE_VALIDATION = "PRE_TRADE_VALIDATION"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    LIVE_TRADING_AUTHORIZED = "LIVE_TRADING_AUTHORIZED"


class Capability(StrEnum):
    """What a connector is allowed to do — never inferred from credentials."""

    PUBLIC_DATA_READ = "PUBLIC_DATA_READ"
    PRIVATE_ACCOUNT_READ = "PRIVATE_ACCOUNT_READ"
    PORTFOLIO_READ = "PORTFOLIO_READ"
    TRANSACTION_READ = "TRANSACTION_READ"
    SIGNAL_COMPUTE = "SIGNAL_COMPUTE"
    PAPER_ORDER = "PAPER_ORDER"
    PRE_TRADE_CHECK = "PRE_TRADE_CHECK"
    ORDER_CONFIRM = "ORDER_CONFIRM"
    LIVE_ORDER = "LIVE_ORDER"
    FUNDS_TRANSFER = "FUNDS_TRANSFER"
    WITHDRAW = "WITHDRAW"


# Ordered ladder — index in this tuple is the rung level.
MODE_LADDER: tuple[PermissionMode, ...] = (
    PermissionMode.DISCONNECTED,
    PermissionMode.READ_ONLY,
    PermissionMode.MONITORING,
    PermissionMode.PAPER_TRADING,
    PermissionMode.PRE_TRADE_VALIDATION,
    PermissionMode.CONFIRMATION_REQUIRED,
    PermissionMode.LIVE_TRADING_AUTHORIZED,
)

_READ = frozenset(
    {
        Capability.PUBLIC_DATA_READ,
        Capability.PRIVATE_ACCOUNT_READ,
        Capability.PORTFOLIO_READ,
        Capability.TRANSACTION_READ,
    }
)
_MONITOR = _READ | {Capability.SIGNAL_COMPUTE}
_PAPER = _MONITOR | {Capability.PAPER_ORDER}
_PRE_TRADE = _PAPER | {Capability.PRE_TRADE_CHECK}
_CONFIRM = _PRE_TRADE | {Capability.ORDER_CONFIRM}

MODE_CAPABILITIES: dict[PermissionMode, frozenset[Capability]] = {
    PermissionMode.DISCONNECTED: frozenset(),
    PermissionMode.READ_ONLY: frozenset(_READ),
    PermissionMode.MONITORING: frozenset(_MONITOR),
    PermissionMode.PAPER_TRADING: frozenset(_PAPER),
    PermissionMode.PRE_TRADE_VALIDATION: frozenset(_PRE_TRADE),
    PermissionMode.CONFIRMATION_REQUIRED: frozenset(_CONFIRM),
    PermissionMode.LIVE_TRADING_AUTHORIZED: frozenset(_CONFIRM | {Capability.LIVE_ORDER}),
}

# Capabilities no mode can ever grant — money never leaves through OWNEX.
FORBIDDEN_CAPABILITIES: frozenset[Capability] = frozenset({Capability.FUNDS_TRANSFER, Capability.WITHDRAW})

MODE_DESCRIPTION: dict[PermissionMode, str] = {
    PermissionMode.DISCONNECTED: "Sin conexión — ninguna llamada al proveedor",
    PermissionMode.READ_ONLY: "Solo lectura de datos públicos y de cuenta",
    PermissionMode.MONITORING: "Lectura + cálculo de señales e indicadores",
    PermissionMode.PAPER_TRADING: "Ejecuta estrategias simuladas, sin dinero real",
    PermissionMode.PRE_TRADE_VALIDATION: "Valida órdenes contra el risk engine, no las envía",
    PermissionMode.CONFIRMATION_REQUIRED: "Prepara órdenes; requieren confirmación humana explícita",
    PermissionMode.LIVE_TRADING_AUTHORIZED: "Órdenes reales dentro de límites de riesgo aprobados",
}

DEFAULT_MODE = PermissionMode.DISCONNECTED

# Connections that have an order path in OWNEX (adapters under
# core/investment/adapters). They may not appear in the connections catalog
# but their permission record must still be reachable from the API.
EXECUTION_PROVIDERS: tuple[str, ...] = ("alpaca", "ibkr", "ccxt", "binance", "iol", "ppi")


class PermissionDeniedError(PermissionError):
    """Raised when a capability is used without an explicit permission grant."""


# ── Persistence ───────────────────────────────────────────────────────────────


def _base_dir() -> Path:
    return get_config().data_dir / "connections"


def _state_path() -> Path:
    return _base_dir() / "permissions.json"


def _audit_path() -> Path:
    return _base_dir() / "permissions_log.jsonl"


def _key(provider: str) -> str:
    safe = _SAFE_NAME.sub("_", str(provider).strip().lower()).strip("_")
    return safe or "unknown"


def _load_state() -> dict[str, dict[str, Any]]:
    path = _state_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("permissions.json ilegible (%s) — se asume deny-by-default", exc)
        return {}
    return data if isinstance(data, dict) else {}


def _save_state(state: dict[str, dict[str, Any]]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True))


def _audit(provider: str, event: str, payload: dict[str, Any]) -> None:
    entry = {"ts": datetime.now(UTC).isoformat(), "provider": provider, "event": event, **payload}
    path = _audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


# ── Public API ────────────────────────────────────────────────────────────────


def parse_mode(value: str | PermissionMode) -> PermissionMode:
    """Parse a mode string; unknown values never fall back to a permissive mode."""
    if isinstance(value, PermissionMode):
        return value
    try:
        return PermissionMode(str(value).strip().upper())
    except ValueError as exc:
        valid = ", ".join(m.value for m in MODE_LADDER)
        raise ValueError(f"Modo de permiso inválido: {value!r}. Válidos: {valid}") from exc


def get_mode(provider: str) -> PermissionMode:
    """Current mode for a provider — ``DISCONNECTED`` when unknown."""
    entry = _load_state().get(_key(provider))
    if not isinstance(entry, dict):
        return DEFAULT_MODE
    try:
        return parse_mode(entry.get("mode", DEFAULT_MODE.value))
    except ValueError:
        logger.warning("Modo corrupto para %s — se degrada a DISCONNECTED", provider)
        return DEFAULT_MODE


def get_record(provider: str) -> dict[str, Any]:
    """Mode + metadata for one provider (never contains credentials)."""
    state = _load_state()
    entry = state.get(_key(provider)) if isinstance(state, dict) else None
    mode = get_mode(provider)
    record: dict[str, Any] = {
        "provider": _key(provider),
        "mode": mode.value,
        "description": MODE_DESCRIPTION[mode],
        "capabilities": sorted(c.value for c in capabilities(provider)),
        "updated_at": None,
        "reason": "",
        "acknowledged": False,
    }
    if isinstance(entry, dict):
        record["updated_at"] = entry.get("updated_at")
        record["reason"] = entry.get("reason", "")
        record["acknowledged"] = bool(entry.get("acknowledged", False))
    return record


def set_mode(
    provider: str,
    mode: str | PermissionMode,
    *,
    reason: str = "",
    acknowledge_risk: bool = False,
) -> dict[str, Any]:
    """Change the autonomy mode of one connection.

    Raises ``PermissionDeniedError`` when escalating to ``LIVE_TRADING_AUTHORIZED``
    without an explicit human acknowledgement. Downgrades are always allowed.
    """
    target = parse_mode(mode)
    current = get_mode(provider)
    if target is current:
        return get_record(provider)

    escalating = MODE_LADDER.index(target) > MODE_LADDER.index(current)
    if escalating and target is PermissionMode.LIVE_TRADING_AUTHORIZED and not acknowledge_risk:
        _audit(provider, "escalation_denied", {"from": current.value, "to": target.value})
        raise PermissionDeniedError("LIVE_TRADING_AUTHORIZED requiere confirmación humana explícita (acknowledge_risk)")
    if escalating and MODE_LADDER.index(target) - MODE_LADDER.index(current) > 1:
        # Multi-rung jumps skip validation steps; reject so the ladder stays auditable.
        next_mode = MODE_LADDER[MODE_LADDER.index(current) + 1]
        _audit(provider, "escalation_denied", {"from": current.value, "to": target.value, "reason": "skip"})
        raise PermissionDeniedError(f"Escalado no contiguo no permitido: {current.value} -> {target.value}. Siguiente paso válido: {next_mode.value}")

    state = _load_state()
    state[_key(provider)] = {
        "mode": target.value,
        "updated_at": datetime.now(UTC).isoformat(),
        "reason": reason,
        "acknowledged": bool(acknowledge_risk),
    }
    _save_state(state)
    _audit(
        provider,
        "mode_changed",
        {"from": current.value, "to": target.value, "reason": reason, "acknowledged": bool(acknowledge_risk)},
    )
    logger.info("Permission mode %s: %s -> %s", provider, current.value, target.value)
    return get_record(provider)


def revoke(provider: str, *, reason: str = "revocado") -> dict[str, Any]:
    """Revoke all access for a provider (kill switch, single connection)."""
    state = _load_state()
    state[_key(provider)] = {
        "mode": PermissionMode.DISCONNECTED.value,
        "updated_at": datetime.now(UTC).isoformat(),
        "reason": reason,
        "acknowledged": False,
    }
    _save_state(state)
    _audit(provider, "revoked", {"reason": reason})
    return get_record(provider)


def capabilities(provider: str) -> frozenset[Capability]:
    """Capabilities granted by the provider's current mode."""
    return MODE_CAPABILITIES[get_mode(provider)]


def allows(provider: str, capability: Capability | str) -> bool:
    """True only when the mode explicitly grants the capability."""
    try:
        cap = capability if isinstance(capability, Capability) else Capability(str(capability))
    except ValueError:
        return False
    if cap in FORBIDDEN_CAPABILITIES:
        return False
    return cap in capabilities(provider)


def require(provider: str, capability: Capability | str) -> None:
    """Raise ``PermissionDeniedError`` unless the capability is granted."""
    cap_name = capability.value if isinstance(capability, Capability) else str(capability)
    if allows(provider, capability):
        return
    mode = get_mode(provider)
    _audit(provider, "denied", {"capability": cap_name, "mode": mode.value})
    raise PermissionDeniedError(f"{cap_name} no permitido para '{provider}' en modo {mode.value}")


def require_all(provider: str, caps: Iterable[Capability | str]) -> None:
    """Check several capabilities at once (first denial wins)."""
    for cap in caps:
        require(provider, cap)


def live_orders_allowed(provider: str) -> bool:
    """Explicit read for order gateways — mirrors ``allows(LIVE_ORDER)``."""
    return allows(provider, Capability.LIVE_ORDER)


def snapshot() -> dict[str, Any]:
    """Every provider with an explicit record + the canonical matrix (for UI)."""
    state = _load_state()
    providers = {key: get_record(key) for key in sorted(state)}
    return {
        "providers": providers,
        "matrix": matrix(),
        "ladder": [m.value for m in MODE_LADDER],
        "forbidden_capabilities": sorted(c.value for c in FORBIDDEN_CAPABILITIES),
    }


def matrix() -> list[dict[str, Any]]:
    """Mode -> capability matrix, consumable by the frontend."""
    return [
        {
            "mode": mode.value,
            "description": MODE_DESCRIPTION[mode],
            "capabilities": sorted(c.value for c in MODE_CAPABILITIES[mode]),
            "live_orders": Capability.LIVE_ORDER in MODE_CAPABILITIES[mode],
            "requires_human_ack": mode is PermissionMode.LIVE_TRADING_AUTHORIZED,
        }
        for mode in MODE_LADDER
    ]


def get_audit(limit: int = 100) -> list[dict[str, Any]]:
    """Recent permission events, newest first."""
    path = _audit_path()
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("No se pudo leer permissions_log: %s", exc)
        return []
    return entries[-max(1, min(limit, MAX_AUDIT_ENTRIES)) :][::-1]


def reset_state_for_tests() -> None:
    """Remove persisted permission state (test helper, never called at runtime)."""
    for path in (_state_path(), _audit_path()):
        if path.exists():
            path.unlink()
