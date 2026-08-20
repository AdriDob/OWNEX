"""Execution policies for the self-improvement harness.

The harness must never execute arbitrary system commands. Every rollout runs
inside a policy-limited sandbox: only whitelisted commands, forbidden keywords
are rejected, network is blocked, and payloads are size-limited. Policies are
deterministic so verification stays objective.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.self_improvement.config import SelfImprovementConfig


class PolicyViolationError(Exception):
    """Raised when a solution violates a harness policy."""


class ExecutionPolicy:
    """Validates solutions and commands before they reach the harness."""

    def __init__(self, config: SelfImprovementConfig) -> None:
        self.config = config

    def validate_solution(self, solution: str) -> list[str]:
        """Return a list of policy violations (empty = allowed)."""
        violations: list[str] = []
        lower = solution.lower()
        for kw in self.config.forbidden_keywords:
            if kw in lower:
                violations.append(f"forbidden keyword: {kw}")
        if len(solution.encode("utf-8", errors="replace")) > self.config.workdir_max_bytes:
            violations.append("solution exceeds payload size limit")
        return violations

    def validate_command(self, argv: list[str]) -> list[str]:
        """Return a list of policy violations for a command vector (empty = allowed)."""
        violations: list[str] = []
        if not argv:
            return ["empty command"]
        executable = Path(argv[0]).name
        if executable not in self.config.allowed_commands:
            violations.append(f"command not allowed: {executable}")
        joined = " ".join(argv)
        for kw in self.config.forbidden_keywords:
            if kw in joined:
                violations.append(f"forbidden keyword: {kw}")
        if self.config.allow_network:
            return violations
        # Block network-implying args inside allowed commands.
        for token in ("http://", "https://", "curl", "wget", "requests.", "socket."):
            if token in joined:
                violations.append(f"network access blocked: {token}")
        return violations

    def enforce_solution(self, solution: str) -> None:
        violations = self.validate_solution(solution)
        if violations:
            raise PolicyViolationError("; ".join(violations))

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed_commands": list(self.config.allowed_commands),
            "forbidden_keywords": list(self.config.forbidden_keywords),
            "allow_network": self.config.allow_network,
            "workdir_max_bytes": self.config.workdir_max_bytes,
            "rollout_timeout_seconds": self.config.rollout_timeout_seconds,
        }
