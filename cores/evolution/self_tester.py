"""Self Tester — Run tests, lint, type checking, benchmarks before/after changes."""

from __future__ import annotations

import logging
import subprocess
import time
from typing import Any

logger = logging.getLogger("ownex.evolution.tester")


class SelfTester:
    def run_all(self) -> dict[str, Any]:
        results = {
            "tests": self._run_tests(),
            "lint": self._run_lint(),
            "type_check": self._run_type_check(),
            "timestamp": time.time(),
        }
        results["passed"] = all(r.get("passed", False) for r in results.values() if isinstance(r, dict))
        return results

    def _run_tests(self) -> dict[str, Any]:
        try:
            start = time.time()
            result = subprocess.run(
                ["python", "-m", "pytest", "-q", "--timeout=30"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            duration = time.time() - start
            passed = result.returncode == 0
            return {
                "passed": passed,
                "output": result.stdout[-300:] if result.stdout else "",
                "errors": result.stderr[-300:] if result.stderr else "",
                "duration_seconds": round(duration, 1),
            }
        except subprocess.TimeoutExpired:
            return {"passed": False, "output": "", "errors": "TIMEOUT", "duration_seconds": 120}
        except Exception as e:
            return {"passed": False, "output": "", "errors": str(e), "duration_seconds": 0}

    def _run_lint(self) -> dict[str, Any]:
        try:
            result = subprocess.run(
                ["ruff", "check", "core/", "api/", "--quiet"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            passed = result.returncode == 0
            return {"passed": passed, "output": result.stdout[:300], "errors": result.stderr[:300]}
        except FileNotFoundError:
            return {"passed": False, "output": "", "errors": "ruff not installed"}
        except Exception as e:
            return {"passed": False, "output": "", "errors": str(e)}

    def _run_type_check(self) -> dict[str, Any]:
        try:
            result = subprocess.run(
                ["mypy", "core/evolution/", "--ignore-missing-imports", "--no-error-summary"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            passed = result.returncode == 0
            return {"passed": passed, "output": result.stdout[:300], "errors": result.stderr[:300]}
        except FileNotFoundError:
            return {"passed": True, "output": "", "errors": "mypy not installed (skipped)"}
        except Exception as e:
            return {"passed": False, "output": "", "errors": str(e)}
