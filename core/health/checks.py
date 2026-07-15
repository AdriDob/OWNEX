"""Default health checks — registered on startup."""

from __future__ import annotations

import logging

logger = logging.getLogger("orion.core.health.checks")


def register_default_checks(center: HealthCenter) -> None:  # noqa: F821
    """Register built-in health checks for core subsystems.

    Import and call during startup.
    """

    # ── System checks ────────────────────────────────

    def check_event_bus() -> bool:
        try:
            from core.events.event_bus import get_event_bus

            bus = get_event_bus()
            return bus is not None
        except Exception:
            return False

    def check_scheduler() -> bool:
        try:
            from api.scheduler import scheduler

            return scheduler is not None
        except Exception:
            return False

    def check_database() -> bool:
        try:
            from database.db import get_db

            db = get_db()
            db.execute("SELECT 1")
            return True
        except Exception:
            return False

    def check_identity_vault() -> bool:
        try:
            from cores.identity_vault import get_identity_vault

            vault = get_identity_vault()
            return vault is not None
        except Exception:
            return False

    def check_agent_bus() -> bool:
        try:
            from cores.agents.bus import get_agent_bus

            bus = get_agent_bus()
            return bus is not None
        except Exception:
            return False

    def check_agents_health() -> bool:
        try:
            from cores.agents import get_all_agents

            agents = get_all_agents()
            if not agents:
                return False
            return all(a.health().get("status") == "running" for a in agents)
        except Exception:
            return False

    def check_memory() -> bool:
        try:
            import psutil

            mem = psutil.Process().memory_percent()
            return mem < 80.0
        except Exception:
            return True  # skip if psutil unavailable

    def check_cpu() -> bool:
        try:
            import psutil

            cpu = psutil.Process().cpu_percent(interval=0.3)
            return cpu < 90.0
        except Exception:
            return True  # skip if psutil unavailable

    # ── Background checks ────────────────────────────

    def check_hooks() -> bool:
        try:
            from core.extension.hooks import get_hook_registry

            reg = get_hook_registry()
            return len(reg.list_hooks()) > 0
        except Exception:
            return False

    def check_extension_registry() -> bool:
        try:
            from core.extension.registry import get_extension_registry

            reg = get_extension_registry()
            return reg is not None
        except Exception:
            return False

    # Register
    center.register("event_bus", check_event_bus, "system")
    center.register("scheduler", check_scheduler, "system")
    center.register("database", check_database, "system")
    center.register("identity_vault", check_identity_vault, "system")
    center.register("agent_bus", check_agent_bus, "system")
    center.register("agents_health", check_agents_health, "system")
    center.register("memory", check_memory, "background")
    center.register("cpu", check_cpu, "background")
    center.register("hook_registry", check_hooks, "background")
    center.register("extension_registry", check_extension_registry, "background")

    logger.info("Registered %d default health checks", 10)
