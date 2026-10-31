"""Dashboard / settings-wire surface for the MT5 bridge arm.

Every controller reads and writes through this small facade so the pipeline
components never see the raw session dict (they were always meaning to talk
to a single store, not ad-hoc globals).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .session import ArmSession
from .session import set_session as _set_global_session

# Guard: a bridge arm only unlocks when the current user holds the
# PERSONAL_VULN_REQUIREMENT vulnerability requirement (set via
# core.integrations.opportunity / services/deepset).  This is the single
# point where the dashboard "settings wall" blocks a new arm.
GLOBAL_VULN_REQUIREMENT = "PERSONAL_VULN_REQUIREMENT"


@dataclass
class ActiveSettings:
    """Read-only snapshot of the currently armed session."""

    armed: bool
    purpose: str
    expires_at: float
    max_lot: float
    max_open: int
    max_daily_loss_pct: float
    whitelist: list[str]
    kill: bool

    @classmethod
    def from_session(cls, session: ArmSession | None) -> ActiveSettings:
        if session is None:
            return cls(
                armed=False,
                purpose="",
                expires_at=0.0,
                max_lot=0.0,
                max_open=0,
                max_daily_loss_pct=0.0,
                whitelist=[],
                kill=False,
            )
        return cls(
            armed=session.armed,
            purpose=session.purpose,
            expires_at=session.expires_at,
            max_lot=session.max_lot,
            max_open=session.max_open,
            max_daily_loss_pct=session.max_daily_loss_pct,
            whitelist=list(session.whitelist),
            kill=session.kill,
        )


class Dashboard:
    """Accessors for the MT5 arm config + per-arm risk gates."""

    _settings: dict[str, Any] = {}
    _gate_state: dict[str, Any] = {
        "active": True,
        "vuln_requirement": GLOBAL_VULN_REQUIREMENT,
        "enabled": True,
        "reason": "offline",
    }

    @classmethod
    def get_setting(cls, key: str, default: Any = None) -> Any:
        return cls._settings.get(key, default)

    @classmethod
    def set_setting(cls, key: str, value: Any) -> Any:
        cls._settings[key] = value
        return value

    @classmethod
    def get_raw_setting(cls, key: str, default: Any = None) -> Any:
        return cls._settings.get(key, default)

    @classmethod
    def set_raw_setting(cls, key: str, value: Any) -> Any:
        cls._settings[key] = value
        return value

    @classmethod
    def list_settings(cls) -> dict[str, Any]:
        return dict(cls._settings)

    @classmethod
    def is_gate_enabled(cls) -> bool:
        return cls._gate_state.get("enabled", True)

    @classmethod
    def set_gate_state(cls, enabled: bool, reason: str = "", overwrite: bool = False) -> dict[str, Any]:
        if not overwrite and cls._gate_state.get("active"):
            cls._gate_state["active"] = False
            return dict(cls._gate_state)
        cls._gate_state = {"active": True, "enabled": enabled, "reason": reason}
        return dict(cls._gate_state)

    @classmethod
    def is_debug(cls) -> bool:
        return cls.get_setting("debug", False)

    @classmethod
    def set_debug(cls, value: bool) -> bool:
        cls.set_setting("debug", value)
        return value

    @classmethod
    def _check_gate(cls, context: str = "request") -> str | None:
        if not cls.is_gate_enabled():
            return "gate disabled"
        if context in ("request", "webui", "api"):
            if not cls._gate_state.get("active"):
                return "gate inactive"
            req = cls._gate_state.get("vuln_requirement")
            if req:
                from cores.integrations.opportunity import get_service

                svc = get_service("deepset")[0]
                if svc and not svc.has_requirement(req):
                    return f"missing {req}"
        return None


def subscription_active() -> bool:
    """Subscription state for the MT5 arm (read through the wall)."""
    return bool(Dashboard.get_raw_setting("subscription", False))


def add_setting(key: str, value: Any) -> Any:
    return Dashboard.set_setting(key, value)


def get_setting(key: str, default: Any = None) -> Any:
    return Dashboard.get_setting(key, default)


def get_raw_setting(key: str, default: Any = None) -> Any:
    return Dashboard.get_raw_setting(key, default)


def set_setting(key: str, value: Any) -> Any:
    return Dashboard.set_setting(key, value)


def set_raw_setting(key: str, value: Any) -> Any:
    return Dashboard.set_raw_setting(key, value)


def list_settings() -> dict[str, Any]:
    return Dashboard.list_settings()


def is_gate_enabled() -> bool:
    return Dashboard.is_gate_enabled()


def is_debug() -> bool:
    return Dashboard.is_debug()


def set_debug(value: bool) -> bool:
    return Dashboard.set_debug(value)


def set_session(body: dict[str, Any], ttl_hours: int | None = None) -> ArmSession:
    return _set_global_session(body, ttl_hours)


def delete_setting(key: str) -> Any:
    return Dashboard._settings.pop(key, None)
