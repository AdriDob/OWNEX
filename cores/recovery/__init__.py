"""Recovery — auto-healing engine for failure detection, diagnosis, and recovery.

Provides:
- RecoveryEngine: central coordinator
- CircuitBreaker: per-component protection against infinite recovery loops
- HealthMonitor: periodic background health checks
- HealingRules: failure type -> recovery strategy mapping
- RecoveryStore: SQLite-persisted recovery history
"""

from __future__ import annotations

from cores.recovery.circuit_breaker import CircuitBreaker, CircuitBreakerRegistry, CircuitState
from cores.recovery.engine import RecoveryEngine, get_recovery_engine, reset_recovery_engine
from cores.recovery.healing_rules import HEALING_RULES, FailureType, HealingRule
from cores.recovery.health_monitor import HealthMonitor, get_health_monitor, reset_health_monitor
from cores.recovery.persistence import RecoveryStore, get_recovery_store, reset_recovery_store

__all__ = [
    "RecoveryEngine",
    "get_recovery_engine",
    "reset_recovery_engine",
    "CircuitBreaker",
    "CircuitBreakerRegistry",
    "CircuitState",
    "HealthMonitor",
    "get_health_monitor",
    "reset_health_monitor",
    "FailureType",
    "HealingRule",
    "HEALING_RULES",
    "RecoveryStore",
    "get_recovery_store",
    "reset_recovery_store",
]
