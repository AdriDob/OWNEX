"""Infrastructure Auditor — Audit dependencies, versions, configs, architecture."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.evolution.auditor")


class InfrastructureAuditor:
    def __init__(self) -> None:
        self.project_root = Path(__file__).resolve().parent.parent.parent

    def run(self) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        findings.extend(self._audit_python_deps())
        findings.extend(self._audit_config_files())
        findings.extend(self._audit_disk_layout())
        findings.extend(self._audit_env_vars())
        return findings

    def _audit_python_deps(self) -> list[dict[str, Any]]:
        findings = []
        req_path = self.project_root / "requirements.txt"
        if not req_path.exists():
            findings.append(self._finding("requirements.txt ausente", "Sin requirements.txt", risk=2.0))
            return findings
        try:
            result = subprocess.run(
                ["pip-audit", "--requirement", str(req_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0 and result.stdout.strip():
                findings.append(
                    self._finding(
                        "Dependencias con vulnerabilidades",
                        result.stdout[:500],
                        risk=7.0,
                        evidence=result.stdout[:200],
                        impact=["security"],
                    )
                )
        except FileNotFoundError:
            findings.append(self._finding("pip-audit no instalado", "pip-audit no encontrado", risk=1.0))
        except subprocess.TimeoutExpired:
            findings.append(self._finding("pip-audit timeout", "pip-audit tardó >30s", risk=1.0))
        return findings

    def _audit_config_files(self) -> list[dict[str, Any]]:
        findings = []
        critical = [".env", "pyproject.toml"]
        for f in critical:
            path = self.project_root / f
            if not path.exists():
                findings.append(self._finding(f"Archivo faltante: {f}", "No encontrado", risk=8.0, impact=["config"]))
        return findings

    def _audit_disk_layout(self) -> list[dict[str, Any]]:
        findings = []
        dirs = ["core", "api", "frontend", "bin", ".ai"]
        for d in dirs:
            path = self.project_root / d
            if not path.exists():
                findings.append(self._finding(f"Directorio faltante: {d}", "No encontrado", risk=6.0))
        return findings

    def _audit_env_vars(self) -> list[dict[str, Any]]:
        findings = []
        required = ["DATABASE_URL", "SECRET_KEY"]
        for var in required:
            if not os.getenv(var):
                findings.append(
                    self._finding(
                        f"Variable de entorno faltante: {var}",
                        f"{var} no está definida",
                        risk=5.0,
                        impact=["config", "security"],
                    )
                )
        return findings

    def _finding(
        self, title: str, description: str, risk: float = 3.0, evidence: str = "", impact: list[str] | None = None
    ) -> dict[str, Any]:
        return {
            "title": title,
            "description": description,
            "risk": risk,
            "evidence": evidence,
            "impact": impact or ["infrastructure"],
        }
