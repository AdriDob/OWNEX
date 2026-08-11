from __future__ import annotations

import importlib
import logging
import os
from pathlib import Path

from core.self_heal.models import HealAction, HealReport

logger = logging.getLogger("ownex.self_heal")


class SelfHealEngine:
    """Autonomous self-healing for OWNEX — validates and repairs its own state."""

    name = "self_heal"

    def __init__(self, project_dir: str | None = None) -> None:
        self.project_dir = Path(project_dir or os.getcwd())
        self.actions_taken: list[HealAction] = []

    def heal(self) -> HealReport:
        """Run full health check and auto-repair cycle."""
        self.actions_taken.clear()

        self._fix_pyproject_trailing_newline()
        self._fix_copilot_provider_store_ownex_dir()
        self._fix_broken_init_files()
        self._fix_missing_capabilities_registry()
        self._fix_import_consistency()
        self._cleanup_pycache()

        return HealReport(
            project_dir=str(self.project_dir),
            actions=self.actions_taken,
        )

    def _record(self, action: HealAction) -> None:
        self.actions_taken.append(action)
        logger.info("[HEAL] %s: %s", action.category, action.description)

    def _fix_pyproject_trailing_newline(self) -> None:
        path = self.project_dir / "pyproject.toml"
        if not path.exists():
            return
        content = path.read_text(encoding="utf-8")
        if content and not content.endswith("\n"):
            path.write_text(content + "\n", encoding="utf-8")
            self._record(
                HealAction(
                    category="file_format",
                    file="pyproject.toml",
                    description="Added missing trailing newline",
                    status="fixed",
                )
            )

    def _fix_copilot_provider_store_ownex_dir(self) -> None:
        path = self.project_dir / "cores" / "ai_router" / "provider_store.py"
        if not path.exists():
            return
        content = path.read_text(encoding="utf-8")
        if 'OWNEX_DIR = "/home/adrie/projects/rastro"' in content:
            fixed = content.replace(
                'OWNEX_DIR = "/home/adrie/projects/rastro"',
                "OWNEX_DIR = os.getcwd()",
            )
            path.write_text(fixed, encoding="utf-8")
            self._record(
                HealAction(
                    category="config",
                    file="cores/ai_router/provider_store.py",
                    description="Replaced hardcoded OWNEX_DIR with os.getcwd()",
                    status="fixed",
                )
            )

    def _fix_broken_init_files(self) -> None:
        broken_patterns = [
            ("core/maintenance/__init__.py", "from core.maintenance.engine"),
        ]
        for rel_path, bad_import in broken_patterns:
            path = self.project_dir / rel_path
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8")
            if bad_import in content:
                fixed = content.replace(bad_import, bad_import)
                if fixed != content:
                    path.write_text(fixed, encoding="utf-8")
                    self._record(
                        HealAction(
                            category="import_fix",
                            file=rel_path,
                            description=f"Checked import: {bad_import}",
                            status="verified",
                        )
                    )

    def _fix_missing_capabilities_registry(self) -> None:
        reg_path = self.project_dir / "core" / "capabilities" / "registry.py"
        if not reg_path.exists():
            return
        content = reg_path.read_text(encoding="utf-8")
        if "has_capability" not in content:
            insert = "\n    def has_capability(self, capability_id: str) -> bool:\n        return capability_id in self._capabilities\n"
            content = content.rstrip() + "\n" + insert
            reg_path.write_text(content, encoding="utf-8")
            self._record(
                HealAction(
                    category="missing_method",
                    file="core/capabilities/registry.py",
                    description="Added has_capability() method to CapabilityRegistry",
                    status="fixed",
                )
            )

    def _fix_import_consistency(self) -> None:
        files_to_check = [
            self.project_dir / "cores" / "capabilities" / "__init__.py",
            self.project_dir / "core" / "capabilities" / "__init__.py",
        ]
        for path in files_to_check:
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8")
            if '""""""' in content:
                fixed = content.replace('""""""', '"""Capability registry module."""')
                if fixed != content:
                    path.write_text(fixed, encoding="utf-8")
                    self._record(
                        HealAction(
                            category="docstring_fix",
                            file=str(path.relative_to(self.project_dir)),
                            description="Fixed malformed docstring",
                            status="fixed",
                        )
                    )

    def _cleanup_pycache(self) -> None:
        cleaned = 0
        for pycache in self.project_dir.rglob("__pycache__"):
            try:
                import shutil

                shutil.rmtree(pycache)
                cleaned += 1
            except OSError:
                pass
        if cleaned > 0:
            self._record(
                HealAction(
                    category="cleanup",
                    file="__pycache__",
                    description=f"Removed {cleaned} __pycache__ directories",
                    status="fixed",
                )
            )

    def validate_imports(self) -> list[dict[str, str]]:
        """Check that all critical modules can be imported."""
        critical_modules = [
            "api.main",
            "core.revenue.engine",
            "core.revenue.tracker",
            "core.capabilities.registry",
            "core.self_heal.engine",
            "core.self_update.engine",
            "cores.events.event_bus",
        ]
        results = []
        for mod in critical_modules:
            try:
                importlib.import_module(mod)
                results.append({"module": mod, "status": "ok"})
            except Exception as e:
                results.append({"module": mod, "status": "broken", "error": str(e)})
        return results

    def validate_files(self) -> list[dict[str, str]]:
        """Check that essential files exist."""
        essential = [
            "pyproject.toml",
            "VERSION",
            "start.sh",
            "start.bat",
            "start.ps1",
            "setup_windows.ps1",
            "README.md",
            "README_INSTALL_WIN11.md",
            ".env.example",
            "api/main.py",
            "core/revenue/engine.py",
            "core/self_heal/engine.py",
            "core/self_update/engine.py",
        ]
        results = []
        for fname in essential:
            path = self.project_dir / fname
            exists = path.exists()
            results.append({"file": fname, "status": "ok" if exists else "missing"})
        return results
