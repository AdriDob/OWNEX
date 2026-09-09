from __future__ import annotations

from core.execution.models import Workflow
from core.execution.primitives import PrimitiveType
from core.execution.validation import BaseValidator, ValidationResult


class TimeoutValidator(BaseValidator):
    """Validates timeout configurations across the workflow.

    Checks:
    - Node timeout does not exceed enclosing retry total timeout
    - Retry total time does not exceed workflow hard limit
    - Timeout values are positive
    - Trigger nodes with timeout have reasonable values
    - Parallel branches don't collectively exceed limits
    """

    name = "timeout"

    MAX_WORKFLOW_TIMEOUT_MS = 3_600_000  # 1 hour
    MAX_TRIGGER_TIMEOUT_MS = 86_400_000  # 24 hours

    def validate(self, workflow: Workflow) -> ValidationResult:
        result = ValidationResult(validator_name=self.name)
        node_map = {n.id: n for n in workflow.nodes}

        # ── Track enclosing retry contexts ───────────────────────
        retry_stack: list[dict] = []  # list of retry configs

        for node in workflow.nodes:
            node_timeout = node.timeout_ms

            # ── 1. Timeout values must be positive ────────────────
            if node_timeout is not None and node_timeout <= 0:
                result.errors.append(
                    self._error(
                        "TIMEOUT_NON_POSITIVE",
                        f"Node '{node.label or node.id}' has non-positive timeout: {node_timeout}ms",
                        node_id=node.id,
                        timeout_ms=node_timeout,
                    )
                )
                result.passed = False

            # ── 2. Workflow hard limit ────────────────────────────
            if node_timeout and node_timeout > self.MAX_WORKFLOW_TIMEOUT_MS:
                result.errors.append(
                    self._error(
                        "TIMEOUT_EXCEEDS_WORKFLOW_LIMIT",
                        f"Node timeout {node_timeout}ms exceeds workflow hard limit {self.MAX_WORKFLOW_TIMEOUT_MS}ms",
                        node_id=node.id,
                        node_timeout=node_timeout,
                        max_timeout=self.MAX_WORKFLOW_TIMEOUT_MS,
                    )
                )
                result.passed = False

            # ── 3. Retry context: total retry time vs node timeout ──
            if retry_stack and node_timeout:
                total_retry_ms = self._compute_retry_total(retry_stack[-1])
                if node_timeout < total_retry_ms:
                    result.errors.append(
                        self._error(
                            "TIMEOUT_LESS_THAN_RETRY_TOTAL",
                            f"Node timeout {node_timeout}ms is less than enclosing retry's "
                            f"total possible time {total_retry_ms}ms (retries × delay)",
                            node_id=node.id,
                            node_timeout=node_timeout,
                            retry_total_ms=total_retry_ms,
                        )
                    )
                    result.passed = False

            # ── 4. Trigger nodes ─────────────────────────────────
            if node.type == PrimitiveType.TRIGGER.value:
                trigger_timeout = node_timeout or node.config.get("timeout_ms")
                if trigger_timeout and trigger_timeout > self.MAX_TRIGGER_TIMEOUT_MS:
                    result.warnings.append(
                        self._warning(
                            "TIMEOUT_TRIGGER_EXCESSIVE",
                            f"Trigger node timeout {trigger_timeout}ms exceeds recommended max "
                            f"{self.MAX_TRIGGER_TIMEOUT_MS}ms",
                            node_id=node.id,
                            trigger_timeout=trigger_timeout,
                            recommended_max=self.MAX_TRIGGER_TIMEOUT_MS,
                        )
                    )

            # ── 5. Wait/Delay nodes ──────────────────────────────
            if node.type in (PrimitiveType.WAIT.value, PrimitiveType.DELAY.value):
                wait_ms = node.config.get("duration_ms", 0)
                if wait_ms > self.MAX_WORKFLOW_TIMEOUT_MS:
                    result.warnings.append(
                        self._warning(
                            "TIMEOUT_WAIT_EXCESSIVE",
                            f"Wait node '{node.label or node.id}' duration {wait_ms}ms "
                            f"exceeds workflow timeout limit {self.MAX_WORKFLOW_TIMEOUT_MS}ms",
                            node_id=node.id,
                            duration_ms=wait_ms,
                            max_timeout=self.MAX_WORKFLOW_TIMEOUT_MS,
                        )
                    )

            # ── Track retry context ──────────────────────────────
            if node.type == PrimitiveType.RETRY.value:
                retry_stack.append(node.config)
        # ── end for ───────────────────────────────────────────────

        # ── 6. Parallel branch cumulative timeout ────────────────
        for node in workflow.nodes:
            if node.type == PrimitiveType.PARALLEL.value:
                branches = node.config.get("branches", [])
                if branches:
                    branch_timeouts = []
                    for br_id in branches:
                        br_node = node_map.get(br_id)
                        if br_node and br_node.timeout_ms:
                            branch_timeouts.append(br_node.timeout_ms)
                    if branch_timeouts:
                        max_branch = max(branch_timeouts)
                        branch_count = len(branch_timeouts)
                        if max_branch * branch_count > self.MAX_WORKFLOW_TIMEOUT_MS:
                            result.suggestions.append(
                                self._suggestion(
                                    "TIMEOUT_PARALLEL_AGGREGATE",
                                    f"Parallel branch aggregate timeout may exceed practical limits "
                                    f"(max branch: {max_branch}ms × {branch_count} branches)",
                                    node_id=node.id,
                                    max_branch_timeout=max_branch,
                                    branch_count=branch_count,
                                )
                            )

        return result

    @staticmethod
    def _compute_retry_total(retry_config: dict) -> int:
        """Compute worst-case total time for a retry block."""
        max_retries = retry_config.get("max_retries", 3)
        base_delay = retry_config.get("base_delay_ms", 1000)
        max_delay = retry_config.get("max_delay_ms", 60000)
        multiplier = retry_config.get("backoff_multiplier", 2.0)

        total = 0
        for attempt in range(max_retries):
            delay = min(base_delay * (multiplier**attempt), max_delay)
            total += delay
        return total
