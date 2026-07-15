"""System requirements checker — validates environment before first run."""

from __future__ import annotations

import logging
import shutil
import subprocess  # noqa: S404 — trusted env check
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core import ORION_DIR

logger = logging.getLogger("orion.core.setup.requirements")


@dataclass
class CheckResult:
    name: str
    status: str  # ok, warning, error
    message: str = ""
    detail: str = ""
    category: str = "system"  # system, security, integration


MIN_PYTHON = (3, 10)
MIN_NODE = (18, 0)
MIN_DISK_MB = 500


def check_python() -> CheckResult:
    v = sys.version_info
    ok = (v.major, v.minor) >= MIN_PYTHON
    return CheckResult(
        name="python",
        status="ok" if ok else "error",
        message=f"Python {v.major}.{v.minor}.{v.micro}"
        if ok
        else f"Python {v.major}.{v.minor} — requiere >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]}",
        detail=f"{v.major}.{v.minor}.{v.micro}",
        category="system",
    )


def check_node() -> CheckResult:
    try:
        r = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10)  # noqa: S603,S607
        if r.returncode != 0:
            return CheckResult("node", "warning", "Node no disponible en PATH", category="system")
        raw = r.stdout.strip().lstrip("v")
        parts = [int(x) for x in raw.split(".")[:2]]
        ok = len(parts) == 2 and (parts[0], parts[1]) >= MIN_NODE
        return CheckResult(
            name="node",
            status="ok" if ok else "warning",
            message=f"Node {raw}" if ok else f"Node {raw} — requiere >= {MIN_NODE[0]}.{MIN_NODE[1]}",
            detail=raw,
            category="system",
        )
    except FileNotFoundError:
        return CheckResult("node", "warning", "Node no instalado", category="system")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CheckResult("node", "error", f"Error: {exc}", category="system")


def check_ollama() -> CheckResult:
    try:
        r = subprocess.run(["ollama", "--version"], capture_output=True, text=True, timeout=10)  # noqa: S603,S607
        if r.returncode != 0:
            return CheckResult("ollama", "warning", "Ollama no responde", category="system")
        version = r.stdout.strip() or r.stderr.strip()
        return CheckResult("ollama", "ok", f"Ollama {version}", detail=version, category="system")
    except FileNotFoundError:
        return CheckResult(
            "ollama", "warning", "Ollama no instalado", "apt install ollama o https://ollama.com", "system"
        )


def check_ollama_models() -> CheckResult:
    try:
        r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=15)  # noqa: S603,S607
        if r.returncode == 0:
            models = [line.split()[0] for line in r.stdout.strip().split("\n")[1:] if line.strip()]
            if models:
                return CheckResult(
                    "ollama_models",
                    "ok",
                    f"Modelos: {', '.join(models[:5])}",
                    detail=str(len(models)),
                    category="system",
                )
            return CheckResult(
                "ollama_models",
                "warning",
                "Ollama instalado pero sin modelos",
                "Ejecuta: ollama pull mistral",
                "system",
            )
        return CheckResult("ollama_models", "warning", "Ollama list falló", category="system")
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return CheckResult("ollama_models", "warning", f"No se pudo verificar: {exc}", category="system")


def check_disk() -> CheckResult:
    try:
        stat = shutil.disk_usage(ORION_DIR if ORION_DIR.exists() else Path.home())
        free_mb = stat.free // (1024 * 1024)
        ok = free_mb >= MIN_DISK_MB
        return CheckResult(
            name="disk",
            status="ok" if ok else "error",
            message=f"{free_mb} MB libres" if ok else f"Solo {free_mb} MB libres — requiere >= {MIN_DISK_MB} MB",
            detail=str(free_mb),
            category="system",
        )
    except OSError as exc:
        return CheckResult("disk", "error", f"No se pudo verificar: {exc}", category="system")


def check_permissions() -> CheckResult:
    try:
        ORION_DIR.mkdir(parents=True, exist_ok=True)
        test_file = ORION_DIR / ".setup_test"
        test_file.touch()
        test_file.unlink()
        return CheckResult("permissions", "ok", "Permisos de escritura correctos", category="system")
    except OSError as exc:
        return CheckResult(
            "permissions", "error", f"Sin permisos de escritura en {ORION_DIR}: {exc}", category="system"
        )


def check_vault() -> CheckResult:
    try:
        from core.secrets.manager import get_secrets_manager

        manager = get_secrets_manager()
        health = manager.health()
        if health.get("status") == "ok" or health.get("ok"):
            return CheckResult("vault", "ok", "IdentityVault creado y funcional", category="security")
        return CheckResult("vault", "warning", "Vault existe pero no responde", health.get("error", ""), "security")
    except Exception as exc:
        return CheckResult("vault", "warning", "Vault no inicializado", str(exc)[:200], "security")


def check_secrets() -> CheckResult:
    try:
        from core.secrets.manager import get_secrets_manager

        manager = get_secrets_manager()
        keys = manager.list_keys()
        if keys:
            return CheckResult(
                "secrets", "ok", f"{len(keys)} secreto(s) almacenado(s)", detail=str(keys), category="security"
            )
        return CheckResult(
            "secrets",
            "warning",
            "No hay secretos configurados",
            "Agrega APIs llave en Settings > Integrations",
            "security",
        )
    except Exception as exc:
        return CheckResult("secrets", "warning", "No se pudieron leer secretos", str(exc)[:200], "security")


SYSTEM_CHECKS = [check_python, check_node, check_ollama, check_ollama_models, check_disk, check_permissions]
SECURITY_CHECKS = [check_vault, check_secrets]


def check_all() -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for fn in SYSTEM_CHECKS + SECURITY_CHECKS:
        try:
            r = fn()
            results.append(
                {"name": r.name, "status": r.status, "message": r.message, "detail": r.detail, "category": r.category}
            )
        except Exception as exc:
            results.append(
                {"name": fn.__name__, "status": "error", "message": f"Check falló: {exc}", "category": "system"}
            )

    by_category: dict[str, list[dict[str, Any]]] = {}
    for r in results:
        by_category.setdefault(r["category"], []).append(r)

    errors = [r for r in results if r["status"] == "error"]
    warnings = [r for r in results if r["status"] == "warning"]

    return {
        "status": "error" if errors else ("warning" if warnings else "ok"),
        "total": len(results),
        "errors": len(errors),
        "warnings": len(warnings),
        "ok": len(results) - len(errors) - len(warnings),
        "results": results,
        "by_category": by_category,
    }
