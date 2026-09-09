"""Design Evolution — Analyze codebase for refactoring opportunities."""

from __future__ import annotations

import logging
import subprocess
from typing import Any

logger = logging.getLogger("ownex.evolution.design")


class DesignEvolution:
    def propose_refactors(self) -> list[dict[str, Any]]:
        proposals: list[dict[str, Any]] = []
        proposals.extend(self._find_dead_code())
        proposals.extend(self._find_large_modules())
        return proposals

    def _find_dead_code(self) -> list[dict[str, Any]]:
        proposals = []
        try:
            result = subprocess.run(
                ["vulture", "core/", "api/", "--min-confidence", "80"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.stdout.strip():
                proposals.append(
                    {
                        "title": "Código muerto detectado",
                        "description": f"Vulture encontró código no utilizado:\n{result.stdout[:500]}",
                        "risk": 2.0,
                        "evidence": result.stdout[:300],
                        "rollback": "git checkout -- <file>",
                        "impact": ["code_quality"],
                    }
                )
        except FileNotFoundError:
            pass
        except subprocess.TimeoutExpired:
            pass
        return proposals

    def _find_large_modules(self) -> list[dict[str, Any]]:
        proposals = []
        try:
            import os

            large = []
            for root, _dirs, files in os.walk("core"):
                for f in files:
                    if f.endswith(".py"):
                        path = os.path.join(root, f)
                        size = os.path.getsize(path)
                        if size > 50000:
                            large.append((path, size))
            for path, size in sorted(large, key=lambda x: -x[1])[:5]:
                proposals.append(
                    {
                        "title": f"Módulo grande: {path}",
                        "description": f"{path} tiene {size // 1024}KB — considerar dividir",
                        "risk": 1.0,
                        "evidence": f"size={size}",
                        "rollback": "No requiere rollback (solo propuesta)",
                        "impact": ["architecture"],
                    }
                )
        except Exception:
            pass
        return proposals
