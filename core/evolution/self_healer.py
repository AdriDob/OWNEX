"""Self Healer — Detect, diagnose, and repair system issues automatically."""

from __future__ import annotations

import logging
from typing import Any

import psutil

logger = logging.getLogger("ownex.evolution.healer")


class SelfHealer:
    def __init__(self) -> None:
        self._checks: list[dict[str, Any]] = []

    def diagnose(self) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        issues.extend(self._check_system_resources())
        issues.extend(self._check_providers())
        issues.extend(self._check_disk_space())
        issues.extend(self._check_database())
        return issues

    def _check_system_resources(self) -> list[dict[str, Any]]:
        issues = []
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        if cpu > 90:
            issues.append(self._make_issue("CPU alto", f"CPU al {cpu}%", risk=6.0, evidence=f"cpu={cpu}%"))
        if mem.percent > 85:
            issues.append(
                self._make_issue("Memoria alta", f"RAM al {mem.percent}%", risk=5.0, evidence=f"mem={mem.percent}%")
            )
        return issues

    def _check_providers(self) -> list[dict[str, Any]]:
        issues = []
        try:
            import asyncio

            from core.orion.health.provider_monitor import get_provider_monitor

            report = asyncio.run(get_provider_monitor().check_all())
            for name, p in report.providers.items():
                if not p.is_ok:
                    issues.append(
                        self._make_issue(
                            f"Provider offline: {name}",
                            f"{name} no responde: {p.last_error}",
                            risk=7.0,
                            evidence=f"{name}: {p.last_error}",
                            impact=["providers", "routing"],
                        )
                    )
        except Exception as e:
            issues.append(
                self._make_issue(
                    "Provider monitor falló",
                    f"No se pudo verificar providers: {e}",
                    risk=4.0,
                )
            )
        return issues

    def _check_disk_space(self) -> list[dict[str, Any]]:
        issues = []
        usage = psutil.disk_usage("/")
        if usage.percent > 90:
            issues.append(
                self._make_issue(
                    "Disco casi lleno",
                    f"Disco al {usage.percent}% ({usage.free // (2**30)} GB libres)",
                    risk=8.0,
                    evidence=f"disk={usage.percent}%",
                    rollback="Liberar espacio manualmente",
                )
            )
        return issues

    def _check_database(self) -> list[dict[str, Any]]:
        issues = []
        try:
            from database.db import SessionLocal

            session = SessionLocal()
            session.execute(session.bind.dialect.statement_compiler.dialect.statement("SELECT 1"))
            session.close()
        except Exception as e:
            issues.append(
                self._make_issue(
                    "Base de datos no responde",
                    f"Conexión a DB falló: {e}",
                    risk=9.0,
                    evidence=str(e),
                    impact=["database", "storage"],
                    rollback="Verificar service db y permisos",
                )
            )
        return issues

    def _make_issue(
        self,
        title: str,
        description: str,
        risk: float = 3.0,
        evidence: str = "",
        impact: list[str] | None = None,
        rollback: str = "",
    ) -> dict[str, Any]:
        return {
            "title": title,
            "description": description,
            "risk": risk,
            "evidence": evidence,
            "impact": impact or ["system"],
            "rollback": rollback,
        }
