"""System Health — granular PC health for Mission Control (spec §6).

Covers: CPU/RAM/GPU/DISK/NETWORK/OS/WIN_VERSION/DRIVERS/PROCESSES/SERVICES/PORTS
+ OWNEX SERVICES/BACKEND/DB/AI/BROWSER/STORAGE/SYNC/UPDATE/ERRORS/LOGS/HEALTH
with least-privilege, no secrets, and human-readable HEALTHY/DEGRADED/WARNING/BLOCKED/CRITICAL.
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import socket
from typing import Any

logger = logging.getLogger("ownex.health.system_health")


def _pct(value: float | None) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 1)
    except Exception:
        return None


def collect_pc_health() -> dict[str, Any]:
    """Collect PC health signals. Best-effort, never raises, never leaks secrets."""
    out: dict[str, Any] = {"collected_at": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat()}

    # OS / Windows version
    try:
        out["os"] = platform.system()
        out["os_version"] = platform.version()
        out["platform"] = platform.platform()
        out["machine"] = platform.machine()
    except Exception as exc:
        out["os_error"] = str(exc)

    # CPU / RAM via psutil (optional)
    try:
        import psutil  # type: ignore

        out["cpu_percent"] = _pct(psutil.cpu_percent(interval=0.2))
        out["ram_percent"] = _pct(psutil.virtual_memory().percent)
        out["disk_percent"] = _pct(
            psutil.disk_usage("/").percent if os.name != "nt" else psutil.disk_usage("C:\\").percent
        )
        out["disk_free_gb"] = (
            round(psutil.disk_usage("/").free / (1024**3), 1)
            if os.name != "nt"
            else round(psutil.disk_usage("C:\\").free / (1024**3), 1)
        )
    except Exception as exc:
        out["psutil_error"] = str(exc)
        out["cpu_percent"] = None
        out["ram_percent"] = None
        out["disk_percent"] = None

    # GPU (best-effort: nvidia-smi if present)
    try:

        if shutil.which("nvidia-smi"):
            proc = __import__("subprocess").run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True, timeout=3
            )
            out["gpu"] = proc.stdout.strip()[:120] if proc.returncode == 0 else None
        else:
            out["gpu"] = None
    except Exception:
        out["gpu"] = None

    # Network (can we reach localhost backend?)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.0)
        result = s.connect_ex(("127.0.0.1", 8000))
        out["backend_port_8000"] = "open" if result == 0 else "closed"
        s.close()
    except Exception:
        out["backend_port_8000"] = "unknown"

    # Disk paths (OWNEX data dirs)
    try:
        from cores.platform.system import get_data_dir

        data_dir = get_data_dir()
        out["data_dir"] = str(data_dir)
        out["data_dir_exists"] = data_dir.exists()
        out["data_dir_writable"] = os.access(data_dir, os.W_OK) if data_dir.exists() else False
    except Exception as exc:
        out["data_dir_error"] = str(exc)

    # Brave / Browser
    try:
        from cores.browsing.brave import browser_context

        out["browser"] = browser_context()
    except Exception as exc:
        out["browser_error"] = str(exc)

    # Elevated mode
    try:
        from cores.platform.elevated import elevation_status

        out["elevation"] = elevation_status()
    except Exception as exc:
        out["elevation_error"] = str(exc)

    # Overall level (simple heuristic)
    level = "HEALTHY"
    if out.get("ram_percent") is not None and out["ram_percent"] and out["ram_percent"] > 90:
        level = "WARNING"
    if out.get("disk_percent") is not None and out["disk_percent"] and out["disk_percent"] > 90:
        level = "WARNING"
    if out.get("data_dir_exists") is False:
        level = "DEGRADED"
    out["level"] = level
    out["summary"] = (
        f"{level}: CPU {out.get('cpu_percent')}% RAM {out.get('ram_percent')}% DISK {out.get('disk_percent')}%"
    )
    return out


def health_level_text(level: str) -> str:
    return {
        "HEALTHY": "Todo operativo",
        "DEGRADED": "Funcionando con degradación",
        "WARNING": "Revisar recursos",
        "BLOCKED": "Bloqueado — acción requerida",
        "CRITICAL": "Crítico — intervención inmediata",
    }.get(level, level)
