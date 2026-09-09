"""Auditors — specialized system checks for quality, security, and health."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("orion.core.copilot.auditor")


class AuditFinding:
    """A single finding from an audit."""

    def __init__(
        self,
        severity: str,
        category: str,
        title: str,
        description: str,
        recommendation: str = "",
    ) -> None:
        self.severity = severity
        self.category = category
        self.title = title
        self.description = description
        self.recommendation = recommendation

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "recommendation": self.recommendation,
        }


class AuditReport:
    """Complete audit report."""

    def __init__(self, auditor_name: str) -> None:
        self.auditor_name = auditor_name
        self.findings: list[AuditFinding] = []
        self.timestamp = datetime.now(UTC)

    def add(self, finding: AuditFinding) -> None:
        self.findings.append(finding)

    def severity_count(self, severity: str) -> int:
        return sum(1 for f in self.findings if f.severity == severity)

    def to_dict(self) -> dict[str, Any]:
        return {
            "auditor": self.auditor_name,
            "timestamp": self.timestamp.isoformat(),
            "total_findings": len(self.findings),
            "severity_counts": {
                "critical": self.severity_count("critical"),
                "high": self.severity_count("high"),
                "medium": self.severity_count("medium"),
                "low": self.severity_count("low"),
                "info": self.severity_count("info"),
            },
            "findings": [f.to_dict() for f in self.findings],
        }


class IAuditor(ABC):
    """Base interface for all auditors."""

    name: str

    @abstractmethod
    def audit(self, system_state: dict[str, Any]) -> AuditReport: ...


class HealthAuditor(IAuditor):
    """Audits system health status."""

    name = "health"

    def audit(self, system_state: dict[str, Any]) -> AuditReport:
        report = AuditReport(self.name)
        health = system_state.get("health", {})

        status = health.get("status", "unknown")
        if status == "red":
            report.add(
                AuditFinding(
                    "critical",
                    "health",
                    "Sistema en estado crítico",
                    f"Health status: {status}. Se requiere intervención inmediata.",
                    "Revisar logs del sistema y servicios de segundo plano",
                )
            )
        elif status == "yellow":
            report.add(
                AuditFinding(
                    "medium",
                    "health",
                    "Sistema en estado de advertencia",
                    f"Health status: {status}. Algunos servicios pueden tener problemas.",
                    "Ejecutar health check completo y revisar servicios degradados",
                )
            )
        elif status == "green":
            report.add(
                AuditFinding(
                    "info",
                    "health",
                    "Sistema saludable",
                    "Todos los servicios reportan estado normal.",
                )
            )

        checks = health.get("checks", [])
        failed_checks = [c for c in checks if c.get("status") in ("error", "critical")]
        for check in failed_checks:
            report.add(
                AuditFinding(
                    "high",
                    "health",
                    f"Health check fallido: {check.get('name', 'unknown')}",
                    check.get("message", "Sin detalles"),
                    "Revisar el componente afectado",
                )
            )

        return report


class ConfigurationAuditor(IAuditor):
    """Audits system configuration completeness."""

    name = "configuration"

    def audit(self, system_state: dict[str, Any]) -> AuditReport:
        report = AuditReport(self.name)
        config = system_state.get("config", {})

        required_keys = ["authority_level", "min_confidence_auto"]
        for key in required_keys:
            if key not in config:
                report.add(
                    AuditFinding(
                        "medium",
                        "configuration",
                        f"Configuración faltante: {key}",
                        f"La clave '{key}' no está presente en la configuración.",
                        f"Agregar '{key}' a la configuración del sistema",
                    )
                )

        env_vars = system_state.get("env", {})
        if "COPILOT_AUTHORITY" not in env_vars:
            report.add(
                AuditFinding(
                    "low",
                    "configuration",
                    "COPILOT_AUTHORITY no configurada",
                    "Usando valor por defecto (observer).",
                    "Configurar COPILOT_AUTHORITY en variables de entorno",
                )
            )

        return report


class SecurityAuditor(IAuditor):
    """Audits security posture."""

    name = "security"

    def audit(self, system_state: dict[str, Any]) -> AuditReport:
        report = AuditReport(self.name)
        findings = system_state.get("findings", {}).get("items", [])

        unverified = [f for f in findings if f.get("status") in ("pending", "unverified")]
        if len(unverified) > 10:
            report.add(
                AuditFinding(
                    "medium",
                    "security",
                    f"Hallazgos sin verificar: {len(unverified)}",
                    "Acumulación de hallazgos sin revisión aumenta el riesgo de omisiones.",
                    "Revisar y clasificar hallazgos pendientes",
                )
            )

        auth = system_state.get("auth", {})
        if not auth.get("csrf_enabled", False):
            report.add(
                AuditFinding(
                    "high",
                    "security",
                    "CSRF middleware desactivado",
                    "La protección CSRF no está activa.",
                    "Activar CSRF middleware en producción",
                )
            )

        return report


class ArchitectureAuditor(IAuditor):
    """Audits module connectivity and architecture health."""

    name = "architecture"

    def audit(self, system_state: dict[str, Any]) -> AuditReport:
        report = AuditReport(self.name)
        modules = system_state.get("modules", {})

        for mod_name, mod_info in modules.items():
            status = mod_info.get("status", "unknown")
            if status == "disconnected":
                report.add(
                    AuditFinding(
                        "high",
                        "architecture",
                        f"Módulo desconectado: {mod_name}",
                        f"El módulo '{mod_name}' no responde.",
                        f"Revisar conexión y estado del módulo {mod_name}",
                    )
                )

        return report


def get_all_auditors() -> list[IAuditor]:
    """Return all registered auditors."""
    return [
        HealthAuditor(),
        ConfigurationAuditor(),
        SecurityAuditor(),
        ArchitectureAuditor(),
    ]
