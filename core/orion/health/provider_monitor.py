"""Provider Health Monitor — unified health tracking for all LLM providers.

Usage:
    from core.orion.health.provider_monitor import get_provider_monitor
    monitor = get_provider_monitor()
    status = await monitor.check_all()
    print(status.dashboard())

Architecture:
    OWNEX
     |
    Provider Monitor
     |
     +-- OmniRoute (localhost:20128)
     +-- FCC Proxy (localhost:8082)
     +-- OpenCode (api.opencode.ai)
     +-- Ollama (localhost:11434)
     +-- Gemini (optional, via API key)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger("ownex.provider_monitor")

STATUS_FILE = os.path.expanduser("~/.orion/provider_status.json")


class ProviderState(Enum):
    CONNECTED = "connected"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class ProviderHealth:
    name: str
    state: ProviderState
    latency_ms: float = 0.0
    models_count: int = 0
    models_list: list[str] = field(default_factory=list)
    last_success: str = ""
    last_error: str = ""
    endpoint: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "latency_ms": round(self.latency_ms, 1),
            "models_count": self.models_count,
            "models_list": self.models_list[:10],
            "last_success": self.last_success,
            "last_error": self.last_error,
            "endpoint": self.endpoint,
            "extra": self.extra,
        }

    @property
    def is_ok(self) -> bool:
        return self.state == ProviderState.CONNECTED


@dataclass
class MonitorReport:
    overall: ProviderState
    providers: dict[str, ProviderHealth]
    timestamp: str = ""
    healthy_count: int = 0
    total_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": self.overall.value,
            "providers": {k: v.to_dict() for k, v in self.providers.items()},
            "timestamp": self.timestamp or datetime.now(UTC).isoformat(),
            "healthy_count": self.healthy_count,
            "total_count": self.total_count,
        }

    def dashboard(self) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("  PROVIDER HEALTH MONITOR")
        lines.append("=" * 60)

        icon_map = {
            ProviderState.CONNECTED: "OK",
            ProviderState.DEGRADED: "!!",
            ProviderState.FAILED: "XX",
            ProviderState.UNKNOWN: "??",
        }
        label_map = {
            ProviderState.CONNECTED: "CONNECTED",
            ProviderState.DEGRADED: "DEGRADED",
            ProviderState.FAILED: "FAILED",
            ProviderState.UNKNOWN: "UNKNOWN",
        }

        for name, p in sorted(self.providers.items()):
            icon = icon_map.get(p.state, "??")
            label = label_map.get(p.state, "UNKNOWN")
            models_str = f"{p.models_count} models" if p.models_count > 0 else "no models"
            latency_str = f"{p.latency_ms:.0f}ms" if p.latency_ms > 0 else "N/A"
            error_str = f"  error: {p.last_error}" if p.last_error else ""
            lines.append(f"  {icon} {name:<15} {label:<12} {models_str:<20} {latency_str}{error_str}")

        overall_icon = icon_map.get(self.overall, "??")
        overall_label = label_map.get(self.overall, "UNKNOWN")
        lines.append("-" * 60)
        lines.append(f"  OVERALL: {overall_icon} {overall_label}  ({self.healthy_count}/{self.total_count} healthy)")
        lines.append(f"  Timestamp: {self.timestamp}")
        lines.append("=" * 60)
        return "\n".join(lines)


class ProviderMonitor:
    def __init__(self) -> None:
        self._history: list[MonitorReport] = []
        self._last_report: MonitorReport | None = None

    async def check_all(self) -> MonitorReport:
        checks = {
            "omniroute": self._check_omniroute(),
            "fcc_proxy": self._check_fcc(),
            "opencode": self._check_opencode(),
            "ollama": self._check_ollama(),
        }
        results = await asyncio.gather(*checks.values(), return_exceptions=True)

        providers: dict[str, ProviderHealth] = {}
        for name, result in zip(checks.keys(), results, strict=False):
            if isinstance(result, Exception):
                providers[name] = ProviderHealth(
                    name=name,
                    state=ProviderState.FAILED,
                    last_error=str(result),
                )
            else:
                providers[name] = result

        healthy = sum(1 for p in providers.values() if p.is_ok)
        total = len(providers)

        if healthy == total:
            overall = ProviderState.CONNECTED
        elif healthy > 0:
            overall = ProviderState.DEGRADED
        else:
            overall = ProviderState.FAILED

        report = MonitorReport(
            overall=overall,
            providers=providers,
            timestamp=datetime.now(UTC).isoformat(),
            healthy_count=healthy,
            total_count=total,
        )

        self._last_report = report
        self._history.append(report)
        if len(self._history) > 100:
            self._history = self._history[-100:]

        self._persist(report)
        return report

    async def _check_omniroute(self) -> ProviderHealth:
        start = time.monotonic()
        endpoint = "http://localhost:20128/v1/models"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(endpoint)
                elapsed = (time.monotonic() - start) * 1000
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m["id"] for m in data.get("data", []) if m.get("id")]
                    return ProviderHealth(
                        name="omniroute",
                        state=ProviderState.CONNECTED,
                        latency_ms=elapsed,
                        models_count=len(models),
                        models_list=models,
                        endpoint=endpoint,
                        last_success=datetime.now(UTC).isoformat(),
                        extra={"container": "omniroute (docker)", "port": 20128},
                    )
                else:
                    return ProviderHealth(
                        name="omniroute",
                        state=ProviderState.FAILED,
                        latency_ms=elapsed,
                        last_error=f"HTTP {resp.status_code}: {resp.text[:200]}",
                        endpoint=endpoint,
                    )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return ProviderHealth(
                name="omniroute",
                state=ProviderState.FAILED,
                latency_ms=elapsed,
                last_error=str(e),
                endpoint=endpoint,
            )

    async def _check_fcc(self) -> ProviderHealth:
        start = time.monotonic()
        endpoint = "http://localhost:8082/health"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(endpoint)
                elapsed = (time.monotonic() - start) * 1000
                if resp.status_code == 200:
                    state = ProviderState.CONNECTED
                    error = ""
                else:
                    state = ProviderState.FAILED
                    error = f"HTTP {resp.status_code}"

                models = []
                try:
                    mresp = await client.get(
                        "http://localhost:8082/v1/models",
                        headers={"x-api-key": "orion-dev-local"},
                        timeout=3.0,
                    )
                    if mresp.status_code == 200:
                        models = [m["id"] for m in mresp.json().get("data", []) if m.get("id")]
                except Exception:
                    pass

                return ProviderHealth(
                    name="fcc_proxy",
                    state=state,
                    latency_ms=elapsed,
                    models_count=len(models),
                    models_list=models,
                    endpoint=endpoint,
                    last_success=datetime.now(UTC).isoformat() if state == ProviderState.CONNECTED else "",
                    last_error=error,
                    extra={"port": 8082, "auth_token": "orion-dev-local (configured)"},
                )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return ProviderHealth(
                name="fcc_proxy",
                state=ProviderState.FAILED,
                latency_ms=elapsed,
                last_error=str(e),
                endpoint=endpoint,
            )

    async def _check_opencode(self) -> ProviderHealth:
        start = time.monotonic()
        endpoint = "https://api.opencode.ai/v1/models"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(endpoint)
                elapsed = (time.monotonic() - start) * 1000
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        models = [m["id"] for m in data.get("data", []) if m.get("id")]
                    except Exception:
                        models = ["deepseek-v4-flash-free (via OmniRoute)"]

                    return ProviderHealth(
                        name="opencode",
                        state=ProviderState.CONNECTED,
                        latency_ms=elapsed,
                        models_count=len(models),
                        models_list=models,
                        endpoint=endpoint,
                        last_success=datetime.now(UTC).isoformat(),
                        extra={"via": "OmniRoute proxy at localhost:20128"},
                    )
                else:
                    return ProviderHealth(
                        name="opencode",
                        state=ProviderState.DEGRADED,
                        latency_ms=elapsed,
                        last_error=f"HTTP {resp.status_code} (API may have changed)",
                        endpoint=endpoint,
                        extra={"fallback": "Use via OmniRoute (oc/deepseek-v4-flash-free)"},
                    )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return ProviderHealth(
                name="opencode",
                state=ProviderState.DEGRADED,
                latency_ms=elapsed,
                last_error=str(e),
                endpoint=endpoint,
                extra={"fallback": "Use via OmniRoute (oc/deepseek-v4-flash-free)"},
            )

    async def _check_ollama(self) -> ProviderHealth:
        start = time.monotonic()
        endpoint = "http://localhost:11434/api/tags"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(endpoint)
                elapsed = (time.monotonic() - start) * 1000
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m["name"] for m in data.get("models", []) if m.get("name")]
                    return ProviderHealth(
                        name="ollama",
                        state=ProviderState.CONNECTED,
                        latency_ms=elapsed,
                        models_count=len(models),
                        models_list=models,
                        endpoint=endpoint,
                        last_success=datetime.now(UTC).isoformat(),
                        extra={"port": 11434},
                    )
                else:
                    return ProviderHealth(
                        name="ollama",
                        state=ProviderState.FAILED,
                        latency_ms=elapsed,
                        last_error=f"HTTP {resp.status_code}",
                        endpoint=endpoint,
                    )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return ProviderHealth(
                name="ollama",
                state=ProviderState.FAILED,
                latency_ms=elapsed,
                last_error=str(e),
                endpoint=endpoint,
            )

    def _persist(self, report: MonitorReport) -> None:
        try:
            path = Path(STATUS_FILE)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report.to_dict(), indent=2))
        except Exception as e:
            logger.warning("Failed to persist provider status: %s", e)

    def get_last_report(self) -> MonitorReport | None:
        return self._last_report

    def get_history(self, limit: int = 10) -> list[MonitorReport]:
        return self._history[-limit:]


_monitor: ProviderMonitor | None = None


def get_provider_monitor() -> ProviderMonitor:
    global _monitor
    if _monitor is None:
        _monitor = ProviderMonitor()
    return _monitor


async def quick_status() -> dict[str, Any]:
    monitor = get_provider_monitor()
    report = await monitor.check_all()
    return report.to_dict()


def print_dashboard() -> None:
    report = asyncio.run(get_provider_monitor().check_all())
    print(report.dashboard())
