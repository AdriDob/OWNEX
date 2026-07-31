"""Orion health checker — collect system-wide health metrics."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Any

import httpx

logger = logging.getLogger("ownex.orion.health.checker")


async def collect_health_metrics() -> dict[str, Any]:
    """Collect health metrics from all ORION subsystems.

    Scheduler handler: ``core.orion.health.checker:collect_health_metrics``
    """
    components: dict[str, Any] = {}

    # 1. Ollama
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:11434/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                components["ollama"] = {
                    "status": "ok",
                    "models": len(models),
                    "model_names": [m.get("name") for m in models[:5]],
                }
            else:
                components["ollama"] = {"status": "error", "code": resp.status_code}
    except Exception as e:
        components["ollama"] = {"status": "error", "error": str(e)}

    # 2. FCC Proxy
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:8082/health", timeout=5)
            if resp.status_code == 200:
                components["fcc_proxy"] = {"status": "ok"}
            else:
                components["fcc_proxy"] = {"status": "error", "code": resp.status_code}
    except Exception as e:
        components["fcc_proxy"] = {"status": "error", "error": str(e)}

    # 3. Rastro API
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:8000/api/health", timeout=5)
            if resp.status_code == 200:
                components["rastro_api"] = {"status": "ok"}
            else:
                components["rastro_api"] = {"status": "error", "code": resp.status_code}
    except Exception as e:
        components["rastro_api"] = {"status": "error", "error": str(e)}

    # 4. Disk
    try:
        stat = os.statvfs("/")
        free_gb = (stat.f_frsize * stat.f_bavail) / (1024**3)
        total_gb = (stat.f_frsize * stat.f_blocks) / (1024**3)
        components["disk"] = {
            "status": "ok" if free_gb > 1 else "warning",
            "free_gb": round(free_gb, 1),
            "total_gb": round(total_gb, 1),
            "usage_pct": round((1 - stat.f_bavail / stat.f_blocks) * 100, 1),
        }
    except Exception as e:
        components["disk"] = {"status": "error", "error": str(e)}

    # 5. Memory
    try:
        with open("/proc/meminfo") as f:
            meminfo = f.read()
        mem_lines = {}
        for line in meminfo.strip().split("\n"):
            parts = line.split(":")
            if len(parts) == 2:
                mem_lines[parts[0].strip()] = parts[1].strip()

        mem_total = int(mem_lines.get("MemTotal", "0").split()[0]) / 1024  # MB
        mem_avail = int(mem_lines.get("MemAvailable", "0").split()[0]) / 1024  # MB
        components["memory"] = {
            "status": "ok" if mem_avail > 512 else "warning",
            "total_mb": round(mem_total, 0),
            "available_mb": round(mem_avail, 0),
            "usage_pct": round((1 - mem_avail / mem_total) * 100, 1),
        }
    except Exception as e:
        components["memory"] = {"status": "error", "error": str(e)}

    # 6. Scheduler
    try:
        from core.scheduler.scheduler import get_core_scheduler

        scheduler = get_core_scheduler()
        components["scheduler"] = {
            "status": "ok",
            "jobs": scheduler.get_jobs(),
        }
    except Exception as e:
        components["scheduler"] = {"status": "error", "error": str(e)}

    # Overall status
    statuses = [c.get("status", "error") for c in components.values()]
    overall = (
        "ok" if all(s == "ok" for s in statuses) else "degraded" if any(s == "warning" for s in statuses) else "error"
    )

    return {
        "overall": overall,
        "components": components,
        "healthy_count": sum(1 for s in statuses if s == "ok"),
        "total_components": len(components),
        "timestamp": datetime.now(UTC).isoformat(),
    }
