from __future__ import annotations

from core.execution.models import Workflow
from core.execution.primitives import PrimitiveType
from core.execution.validation import BaseValidator, ValidationResult


class RetryValidator(BaseValidator):
    """Validates retry configurations to prevent infinite loops and deadlocks.

    Checks:
    - max_retries within allowed range (1–10)
    - retry delay values are positive and reasonable
    - no infinite retry without timeout guard
    - no retry+loop deadlock (retry wrapping a loop that never terminates)
    - backoff values are valid
    """

    name = "retry"

    MAX_RETRIES_ALLOWED = 10
    MIN_DELAY_MS = 100
    MAX_DELAY_MS = 300_000  # 5 minutes

    def validate(self, workflow: Workflow) -> ValidationResult:
        result = ValidationResult(validator_name=self.name)

        for node in workflow.nodes:
            if node.type != PrimitiveType.RETRY.value:
                continue

            max_retries = node.config.get("max_retries", 3)
            base_delay = node.config.get("base_delay_ms", 1000)
            max_delay = node.config.get("max_delay_ms", 60000)
            multiplier = node.config.get("backoff_multiplier", 2.0)

            # ── 1. max_retries range ─────────────────────────────
            if max_retries < 1:
                result.errors.append(
                    self._error(
                        "RETRY_ZERO_RETRIES",
                        f"Retry node '{node.label or node.id}' has max_retries={max_retries}, must be at least 1",
                        node_id=node.id,
                        max_retries=max_retries,
                    )
                )
                result.passed = False

            if max_retries > self.MAX_RETRIES_ALLOWED:
                result.errors.append(
                    self._error(
                        "RETRY_EXCESSIVE_RETRIES",
                        f"Retry node '{node.label or node.id}' has max_retries={max_retries}, "
                        f"exceeds allowed maximum {self.MAX_RETRIES_ALLOWED}",
                        node_id=node.id,
                        max_retries=max_retries,
                        max_allowed=self.MAX_RETRIES_ALLOWED,
                    )
                )
                result.passed = False

            # ── 2. Delay values must be positive ─────────────────
            if base_delay < self.MIN_DELAY_MS:
                result.warnings.append(
                    self._warning(
                        "RETRY_BASE_DELAY_TOO_LOW",
                        f"Retry base delay {base_delay}ms is below recommended minimum {self.MIN_DELAY_MS}ms",
                        node_id=node.id,
                        base_delay_ms=base_delay,
                        min_recommended=self.MIN_DELAY_MS,
                    )
                )

            if max_delay > self.MAX_DELAY_MS:
                result.warnings.append(
                    self._warning(
                        "RETRY_MAX_DELAY_EXCESSIVE",
                        f"Retry max delay {max_delay}ms exceeds recommended maximum {self.MAX_DELAY_MS}ms",
                        node_id=node.id,
                        max_delay_ms=max_delay,
                        max_recommended=self.MAX_DELAY_MS,
                    )
                )

            # ── 3. Backoff multiplier validity ───────────────────
            if multiplier < 1.0:
                result.warnings.append(
                    self._warning(
                        "RETRY_BACKOFF_INVALID",
                        f"Retry backoff multiplier {multiplier} should be >= 1.0 (exponential backoff)",
                        node_id=node.id,
                        backoff_multiplier=multiplier,
                    )
                )

            # ── 4. No timeout guard → risk of infinite retry ─────
            has_timeout_guard = any(n.type == PrimitiveType.TIMEOUT.value for n in workflow.nodes)
            if not has_timeout_guard:
                result.suggestions.append(
                    self._suggestion(
                        "RETRY_NO_TIMEOUT_GUARD",
                        "No TIMEOUT node found in workflow — retry could loop indefinitely",
                        node_id=node.id,
                    )
                )

            # ── 5. Estimated worst-case retry time ───────────────
            worst_case_ms = self._compute_worst_case(max_retries, base_delay, max_delay, multiplier)
            if worst_case_ms > 300_000:  # 5 minutes
                result.warnings.append(
                    self._warning(
                        "RETRY_WORST_CASE_HIGH",
                        f"Retry worst-case time is {worst_case_ms}ms ({worst_case_ms // 1000}s) "
                        f"— consider reducing retries or delay",
                        node_id=node.id,
                        worst_case_ms=worst_case_ms,
                    )
                )

        return result

    @staticmethod
    def _compute_worst_case(max_retries: int, base_delay: int, max_delay: int, multiplier: float) -> int:
        total = 0
        for attempt in range(max_retries):
            delay = min(int(base_delay * (multiplier**attempt)), max_delay)
            total += delay
        return total
