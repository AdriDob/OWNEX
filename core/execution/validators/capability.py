from __future__ import annotations

import logging
from typing import Any

from core.execution.models import Workflow
from core.execution.primitives import PrimitiveType
from core.execution.validation import BaseValidator, ValidationResult

logger = logging.getLogger("orion.core.execution.validators.capability")


class CapabilityValidator(BaseValidator):
    """Validates that every CAPABILITY node references a real registered capability.

    Checks:
    - Capability name exists in the CapabilityRegistry
    - Capability timeout is within the declared contract
    - Capability contract has required fields
    - Rollback strategy is compatible with capability
    """

    name = "capability"

    def validate(self, workflow: Workflow) -> ValidationResult:
        result = ValidationResult(validator_name=self.name)
        caps = self._get_registered_capabilities()

        for node in workflow.nodes:
            if node.type != PrimitiveType.CAPABILITY.value:
                continue

            cap_name = node.config.get("capability", "")
            if not cap_name:
                result.errors.append(
                    self._error(
                        "CAP_EMPTY_NAME",
                        f"Capability node '{node.label or node.id}' has no capability name",
                        node_id=node.id,
                    )
                )
                result.passed = False
                continue

            # ── Check capability exists ──────────────────────────
            if cap_name not in caps:
                result.errors.append(
                    self._error(
                        "CAP_NOT_REGISTERED",
                        f"Capability '{cap_name}' is not registered in CapabilityRegistry",
                        node_id=node.id,
                        available=list(caps.keys()),
                    )
                )
                result.passed = False
                continue

            info = caps[cap_name]

            # ── Check contract completeness ──────────────────────
            if not info.get("description"):
                result.warnings.append(
                    self._warning(
                        "CAP_NO_DESCRIPTION",
                        f"Capability '{cap_name}' has no description in its contract",
                        node_id=node.id,
                    )
                )

            # ── Check node timeout vs capability max timeout ──────
            node_timeout = node.timeout_ms or node.config.get("timeout_ms")
            cap_max_timeout = info.get("timeout_ms")
            if node_timeout and cap_max_timeout and node_timeout > cap_max_timeout:
                result.errors.append(
                    self._error(
                        "CAP_TIMEOUT_EXCEEDS_MAX",
                        f"Node timeout ({node_timeout}ms) exceeds capability max ({cap_max_timeout}ms)",
                        node_id=node.id,
                        node_timeout=node_timeout,
                        cap_max_timeout=cap_max_timeout,
                    )
                )
                result.passed = False

            # ── Check rollback compatibility ─────────────────────
            node_rollback = node.config.get("rollback_strategy", "none")
            cap_rollback = info.get("rollback_strategy", "none")
            if node_rollback != "none" and cap_rollback == "none":
                result.warnings.append(
                    self._warning(
                        "CAP_NO_ROLLBACK",
                        f"Node requests rollback '{node_rollback}' but capability '{cap_name}' has no rollback strategy",
                        node_id=node.id,
                        node_rollback=node_rollback,
                        cap_rollback=cap_rollback,
                    )
                )

            # ── Check required config params ─────────────────────
            required = info.get("required_params", [])
            for param in required:
                if param not in node.config.get("params", {}):
                    result.errors.append(
                        self._error(
                            "CAP_MISSING_PARAM",
                            f"Capability '{cap_name}' requires param '{param}'",
                            node_id=node.id,
                            required_param=param,
                        )
                    )
                    result.passed = False

        return result

    @staticmethod
    def _get_registered_capabilities() -> dict[str, dict[str, Any]]:
        """Fetch all registered capabilities from the CapabilityRegistry.

        Returns dict[capability_name, info_dict].
        Gracefully degrades if the registry is unavailable.
        """
        try:
            from core.capabilities.registry import get_capability_registry

            reg = get_capability_registry()
            caps: dict[str, dict[str, Any]] = {}
            for cap_name in reg.list_capabilities():
                entries = reg.find(cap_name)
                if entries:
                    entry = entries[0]
                    caps[cap_name] = {
                        "description": getattr(entry, "description", ""),
                        "timeout_ms": getattr(entry, "timeout_ms", None),
                        "rollback_strategy": getattr(entry, "rollback_strategy", "none"),
                        "required_params": getattr(entry, "required_params", []),
                        "metadata": getattr(entry, "metadata", {}),
                    }
            return caps
        except Exception as exc:
            logger.debug("CapabilityRegistry unavailable: %s", exc)
            return {}
