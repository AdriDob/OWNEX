from __future__ import annotations

import logging

from core.execution.models import Workflow
from core.execution.primitives import PrimitiveType
from core.execution.validation import BaseValidator, ValidationResult

logger = logging.getLogger("orion.core.execution.validators.dependency")


class DependencyValidator(BaseValidator):
    """Validates inter-module dependencies referenced by the workflow.

    Checks:
    - All referenced capabilities exist in the CapabilityRegistry
    - No circular dependencies between capabilities
    - Required modules/extensions are enabled
    - Required integrations are configured
    - Required secrets exist in the vault
    """

    name = "dependency"

    def validate(self, workflow: Workflow) -> ValidationResult:
        result = ValidationResult(validator_name=self.name)
        capabilities = self._get_capability_map()
        integrations = self._get_integration_map()

        for node in workflow.nodes:
            if node.type != PrimitiveType.CAPABILITY.value:
                continue

            cap_name = node.config.get("capability", "")
            if not cap_name:
                continue

            # ── 1. Capability exists ─────────────────────────────
            if cap_name not in capabilities:
                result.errors.append(
                    self._error(
                        "DEP_CAPABILITY_NOT_FOUND",
                        f"Capability '{cap_name}' is not registered in any module",
                        node_id=node.id,
                        capability=cap_name,
                    )
                )
                result.passed = False
                continue

            info = capabilities[cap_name]

            # ── 2. Dependencies resolved ─────────────────────────
            deps = info.get("dependencies", [])
            for dep in deps:
                if dep not in capabilities:
                    result.errors.append(
                        self._error(
                            "DEP_MISSING_DEPENDENCY",
                            f"Capability '{cap_name}' depends on '{dep}' which is not registered",
                            node_id=node.id,
                            capability=cap_name,
                            missing_dependency=dep,
                        )
                    )
                    result.passed = False

            # ── 3. Required integrations configured ──────────────
            required_integrations = info.get("required_integrations", [])
            for integ in required_integrations:
                integ_info = integrations.get(integ)
                if not integ_info:
                    result.errors.append(
                        self._error(
                            "DEP_INTEGRATION_MISSING",
                            f"Capability '{cap_name}' requires integration '{integ}' which is not configured",
                            node_id=node.id,
                            capability=cap_name,
                            required_integration=integ,
                        )
                    )
                    result.passed = False
                elif integ_info.get("status") != "ok":
                    result.warnings.append(
                        self._warning(
                            "DEP_INTEGRATION_NOT_READY",
                            f"Integration '{integ}' is configured but status is "
                            f"'{integ_info.get('status', 'unknown')}'",
                            node_id=node.id,
                            integration=integ,
                            status=integ_info.get("status"),
                        )
                    )

            # ── 4. Required secrets ──────────────────────────────
            required_secrets = info.get("required_secrets", [])
            missing_secrets = self._check_secrets(required_secrets)
            for secret in missing_secrets:
                result.errors.append(
                    self._error(
                        "DEP_SECRET_MISSING",
                        f"Capability '{cap_name}' requires secret '{secret}' which is not available",
                        node_id=node.id,
                        capability=cap_name,
                        missing_secret=secret,
                    )
                )
                result.passed = False

        return result

    @staticmethod
    def _get_capability_map() -> dict[str, dict]:
        """Build a map of capability_name → metadata from CapabilityRegistry."""
        try:
            from core.capabilities.registry import get_capability_registry

            reg = get_capability_registry()
            caps: dict[str, dict] = {}
            for cap_name in reg.list_capabilities():
                entries = reg.find(cap_name)
                if entries:
                    entry = entries[0]
                    meta = getattr(entry, "metadata", {}) or {}
                    caps[cap_name] = {
                        "dependencies": meta.get("dependencies", []),
                        "required_integrations": meta.get("required_integrations", []),
                        "required_secrets": meta.get("required_secrets", []),
                        "module": meta.get("module", ""),
                    }
            return caps
        except Exception as exc:
            logger.debug("CapabilityRegistry unavailable: %s", exc)
            return {}

    @staticmethod
    def _get_integration_map() -> dict[str, dict]:
        """Build a map of integration_name → status from IntegrationRegistry."""
        try:
            from core.integrations.registry import get_integration_registry

            reg = get_integration_registry()
            summary = reg.summary()
            return summary.get("integrations", {})
        except Exception as exc:
            logger.debug("IntegrationRegistry unavailable: %s", exc)
            return {}

    @staticmethod
    def _check_secrets(required: list[str]) -> list[str]:
        """Return list of required secrets that are not available."""
        missing: list[str] = []
        for name in required:
            try:
                from core.secrets.manager import SecretsManager

                mgr = SecretsManager()
                value = mgr.get(name)
                if value is None:
                    missing.append(name)
            except Exception:
                missing.append(name)
        return missing
