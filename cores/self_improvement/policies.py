"""Execution policy for the self-improvement harness.

Was a bare stub (`class ExecutionPolicy: pass`), but `harness.py` calls
`ExecutionPolicy(config)`, `enforce_solution()` and `validate_command()` — so
every `/api/self-improvement/*` endpoint raised TypeError and returned 500.

The denylist is NOT re-declared here: `cores.automation.safety` is the
existing SSOT for destructive commands (BLOCKED_COMMAND_PATTERNS) and this
module delegates to it, so there is exactly one list to maintain.
"""

from __future__ import annotations

import re
from typing import Any

#: Secret-shaped material that must never reach a sandbox file or a prompt.
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{12,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


class PolicyViolationError(Exception):
    """Raised when a solution violates the execution policy."""


class ExecutionPolicy:
    """Validates what the sandboxed harness is about to write or run.

    Fail-closed on what it can see; it does NOT claim the sandbox is safe —
    the harness still runs generated code, so this is a floor, not a proof.
    """

    def __init__(self, config: Any = None) -> None:
        self.config = config

    def validate_solution(self, solution: str) -> list[str]:
        """Return the reasons this solution text is not allowed. Empty = ok."""
        from cores.automation.safety import check_command

        violations: list[str] = []
        for pattern in _SECRET_PATTERNS:
            if pattern.search(solution or ""):
                violations.append(f"secret-shaped material matching {pattern.pattern[:24]}…")
        # A generated solution can carry the destructive command in its *body*
        # (`os.system('rm -rf /')`), where the argv check would never see it.
        # Same denylist as validate_command — one list, two entry points.
        allowed, reason = check_command(solution or "")
        if not allowed:
            violations.append(reason)
        return violations

    def enforce_solution(self, solution: str) -> None:
        """Raise PolicyViolationError if the solution text is not allowed."""
        violations = self.validate_solution(solution)
        if violations:
            raise PolicyViolationError("; ".join(violations))

    def validate_command(self, command: str | list[str]) -> list[str]:
        """Return the reasons this shell command is not allowed. Empty = ok.

        The harness passes an argv **list** (`_verification_command`), so a
        list is joined before it reaches the denylist regexes — otherwise
        `pattern.search(list)` raises TypeError and the rollout dies on a
        validation path that was supposed to protect it.
        """
        from cores.automation.safety import check_command

        cmd = " ".join(command) if isinstance(command, list) else str(command or "")
        allowed, reason = check_command(cmd)
        return [] if allowed else [reason]

    def to_dict(self) -> dict[str, Any]:
        """Serializable snapshot of the policy (no Paths, no secrets).

        Consumer: `SelfImprovementEngine.status()` (engine.py) which is served
        by `GET /api/self-improvement/status`.
        """
        return {
            "max_solution_tokens": getattr(self.config, "max_solution_tokens", None),
            "rollout_timeout_seconds": getattr(self.config, "rollout_timeout_seconds", None),
            "blocks_destructive_commands": True,
            "blocks_secret_material": True,
        }
