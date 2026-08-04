"""Tool Ecosystem Management — inventory + keep/remove decisions.

Implements the FINALIZATION PROTOCOL Tool Ecosystem Management layer over the real
``cores.tools`` TOOL_REGISTRY (the wrappers the pipeline actually runs).

For every registered wrapper this exposes:

    Tool Name / Purpose (install_hint) / Version (min_version) / License /
    Security Status / Usage Frequency (recorded on each run) /
    Maintenance Cost / Keep / Remove Decision

Usage frequency is persisted in a small JSON file under the CATEYE data dir and is
incremented automatically by ``BaseTool.run`` (see base.py). Keep/remove decisions
are curated per tool (dangerous/unused tools are candidates for removal).
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.tools.ecosystem")

# Curated metadata per wrapped tool: license, security risk, maintenance cost,
# keep/remove decision. Purpose/version come from the tool classes themselves.
_TOOL_META: dict[str, dict[str, Any]] = {
    "amass": {"license": "Apache-2.0", "security_risk": "LOW", "maintenance_cost": "MEDIUM", "keep": True},
    "shodan": {"license": "MIT", "security_risk": "LOW", "maintenance_cost": "LOW", "keep": True},
    "subfinder": {"license": "MIT", "security_risk": "LOW", "maintenance_cost": "LOW", "keep": True},
    "uncover": {"license": "MIT", "security_risk": "LOW", "maintenance_cost": "LOW", "keep": True},
    "httpx": {"license": "MIT", "security_risk": "LOW", "maintenance_cost": "LOW", "keep": True},
    "naabu": {"license": "MIT", "security_risk": "LOW", "maintenance_cost": "LOW", "keep": True},
    "nuclei": {"license": "MIT", "security_risk": "LOW", "maintenance_cost": "LOW", "keep": True},
    "katana": {"license": "MIT", "security_risk": "LOW", "maintenance_cost": "LOW", "keep": True},
    "gau": {"license": "MIT", "security_risk": "LOW", "maintenance_cost": "LOW", "keep": True},
    "ffuf": {"license": "MIT", "security_risk": "LOW", "maintenance_cost": "LOW", "keep": True},
    "linkfinder": {"license": "MIT", "security_risk": "LOW", "maintenance_cost": "LOW", "keep": True},
    "dalfox": {"license": "MIT", "security_risk": "LOW", "maintenance_cost": "LOW", "keep": True},
    "sqlmap": {"license": "GPL-2.0", "security_risk": "MEDIUM", "maintenance_cost": "MID", "keep": True},
    "trufflehog": {"license": "AGPL-3.0", "security_risk": "LOW", "maintenance_cost": "MEDIUM", "keep": True},
    "gitleaks": {"license": "MIT", "security_risk": "LOW", "maintenance_cost": "MEDIUM", "keep": True},
    "garak": {"license": "Apache-2.0", "security_risk": "MEDIUM", "maintenance_cost": "HIGH", "keep": True},
    "browser_use": {"license": "Apache-2.0", "security_risk": "MEDIUM", "maintenance_cost": "HIGH", "keep": True},
    "censys": {"license": "MIT", "security_risk": "LOW", "maintenance_cost": "LOW", "keep": True},
    "slither": {"license": "AGPL-3.0", "security_risk": "LOW", "maintenance_cost": "MEDIUM", "keep": True},
}


@dataclass
class ToolInventoryEntry:
    """One row of the Tool Ecosystem inventory."""

    name: str
    purpose: str
    version: str
    license: str
    security_status: str
    usage_frequency: int
    maintenance_cost: str
    decision: str  # keep | remove
    installed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "purpose": self.purpose,
            "version": self.version,
            "license": self.license,
            "security_status": self.security_status,
            "usage_frequency": self.usage_frequency,
            "maintenance_cost": self.maintenance_cost,
            "installed": self.installed,
            "decision": self.decision,
        }


class ToolUsageTracker:
    """Persisted usage-frequency counter keyed by tool wrapper name."""

    def __init__(self, path: Path | str | None = None):
        default = Path(__file__).resolve().parents[2] / "data" / "tool_usage.json"
        self._path = Path(path) if path else default
        self._usage: dict[str, int] = self._load()

    def _load(self) -> dict[str, int]:
        try:
            if self._path.exists():
                return json.loads(self._path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Tool usage state unreadable: %s", exc)
        return {}

    def record(self, name: str) -> None:
        self._usage[name] = self._usage.get(name, 0) + 1
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(self._usage, indent=2), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Tool usage state not persisted: %s", exc)

    def frequency(self) -> dict[str, int]:
        return self._usage

    def snapshot(self) -> dict[str, int]:
        return dict(self._usage)


class ToolEcosystem:
    """Inventory over the real TOOL_REGISTRY with protocol metadata + decisions."""

    def __init__(self, usage: ToolUsageTracker | None = None):
        self._usage = usage or ToolUsageTracker()

    def inventory(self) -> list[dict[str, Any]]:
        from cores.tools.extra import TOOL_REGISTRY

        entries: list[ToolInventoryEntry] = []
        for name, tool_cls in sorted(TOOL_REGISTRY.items()):
            meta = _TOOL_META.get(
                name, {"license": "unknown", "security_risk": "UNKNOWN", "maintenance_cost": "LOW", "keep": True}
            )
            purpose = getattr(tool_cls, "install_hint", "") or getattr(tool_cls, "name", name)
            version = getattr(tool_cls, "min_version", "") or "-"
            usage_count = self._usage.frequency().get(name, 0)

            # Decision: curated keep-remove, plus hard rules.
            decision = "keep" if meta.get("keep", True) else "remove"
            if meta.get("security_risk") in ("HIGH", "CRITICAL"):
                decision = "remove"
            installed = bool(shutil.which(name)) or name in {"browser_use", "garak", "censys"}

            entries.append(
                ToolInventoryEntry(
                    name=name,
                    purpose=purpose,
                    version=version,
                    license=meta.get("license", "unknown"),
                    security_status=meta.get("security_risk", "UNKNOWN"),
                    usage_frequency=usage_count,
                    maintenance_cost=meta.get("maintenance_cost", "LOW"),
                    decision=decision,
                    installed=installed,
                )
            )

        return [e.to_dict() for e in entries]

    def summary(self) -> dict[str, Any]:
        rows = self.inventory()
        return {
            "total": len(rows),
            "installed": sum(1 for r in rows if r["installed"]),
            "keep": sum(1 for r in rows if r["decision"] == "keep"),
            "remove_candidates": [r["name"] for r in rows if r["decision"] == "remove"],
            "most_used": sorted(rows, key=lambda r: r["usage_frequency"], reverse=True)[:5] if rows else [],
        }


_ECOSYSTEM: ToolEcosystem | None = None


def get_tool_ecosystem() -> ToolEcosystem:
    global _ECOSYSTEM
    if _ECOSYSTEM is None:
        _ECOSYSTEM = ToolEcosystem()
    return _ECOSYSTEM


def record_tool_usage(name: str) -> None:
    """Increments usage frequency for a tool run in the background."""
    try:
        get_tool_ecosystem()._usage.record(name)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Tool usage not recorded for %s: %s", name, exc)
