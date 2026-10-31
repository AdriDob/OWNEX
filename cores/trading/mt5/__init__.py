"""MT5 bridge arm — dashboard / settings-wire accessors and risk gating."""

from .dashboard_settings_wall import (
    ActiveSettings,
    Dashboard,
    add_setting,
    delete_setting,
    get_raw_setting,
    get_setting,
    is_debug,
    is_gate_enabled,
    list_settings,
    set_raw_setting,
    set_session,
    set_setting,
    subscription_active,
)
from .risk import GLOBAL_VULN_REQUIREMENT, MT5GateResult

__all__ = [
    "ActiveSettings",
    "Dashboard",
    "GLOBAL_VULN_REQUIREMENT",
    "MT5GateResult",
    "add_setting",
    "delete_setting",
    "get_raw_setting",
    "get_setting",
    "is_debug",
    "is_gate_enabled",
    "list_settings",
    "set_raw_setting",
    "set_setting",
    "set_session",
    "subscription_active",
]
