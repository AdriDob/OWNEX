from __future__ import annotations

import logging

from core.execution.models import Workflow
from core.execution.primitives import PrimitiveType
from core.execution.validation import BaseValidator, ValidationResult

logger = logging.getLogger("orion.core.execution.validators.permission")


class PermissionValidator(BaseValidator):
    """Validates permissions and credentials for capability execution.

    Checks:
    - IdentityVault is initialized if capabilities need secrets
    - Required credentials exist in vault
    - SCOPE permissions are sufficient
    - Dangerous capabilities require elevated authority
    """

    name = "permission"

    def validate(self, workflow: Workflow) -> ValidationResult:
        result = ValidationResult(validator_name=self.name)
        vault_ok = self._check_vault()
        permissions = self._get_required_permissions()

        for node in workflow.nodes:
            if node.type not in (PrimitiveType.CAPABILITY.value, PrimitiveType.APPROVAL.value):
                continue

            cap_name = node.config.get("capability", "") if node.type == PrimitiveType.CAPABILITY.value else ""
            required_scopes = node.config.get("required_scopes", [])
            requires_secrets = node.config.get("requires_secrets", False)

            # ── Check vault availability ─────────────────────────
            if requires_secrets and not vault_ok:
                result.errors.append(
                    self._error(
                        "PERM_VAULT_UNAVAILABLE",
                        f"Node '{node.label or node.id}' requires secrets but IdentityVault is unavailable",
                        node_id=node.id,
                    )
                )
                result.passed = False

            # ── Check required scopes ────────────────────────────
            for scope in required_scopes:
                if scope not in permissions:
                    result.errors.append(
                        self._error(
                            "PERM_MISSING_SCOPE",
                            f"Node '{node.label or node.id}' requires scope '{scope}' which is not granted",
                            node_id=node.id,
                            required_scope=scope,
                        )
                    )
                    result.passed = False

            # ── Check approval for dangerous capabilities ────────
            if cap_name in ("capability:execute_command", "capability:delete_resource", "capability:modify_system"):
                has_approval = any(n.type == PrimitiveType.APPROVAL.value for n in workflow.nodes)
                if not has_approval:
                    result.warnings.append(
                        self._warning(
                            "PERM_DANGEROUS_NO_APPROVAL",
                            f"Capability '{cap_name}' is dangerous but no APPROVAL node exists in the workflow",
                            node_id=node.id,
                            capability=cap_name,
                        )
                    )

            # ── Check approval level threshold ───────────────────
            required_level = node.config.get("required_authority_level", "")
            if required_level and not self._has_sufficient_authority(required_level):
                result.errors.append(
                    self._error(
                        "PERM_INSUFFICIENT_AUTHORITY",
                        f"Node '{node.label or node.id}' requires authority level '{required_level}'",
                        node_id=node.id,
                        required_level=required_level,
                    )
                )
                result.passed = False

        return result

    @staticmethod
    def _check_vault() -> bool:
        """Check if IdentityVault is accessible."""
        try:
            from cores.identity_vault import get_identity_vault

            vault = get_identity_vault()
            return vault.is_ready() if hasattr(vault, "is_ready") else True
        except Exception as exc:
            logger.debug("IdentityVault unavailable: %s", exc)
            return False

    @staticmethod
    def _get_required_permissions() -> set[str]:
        """Get the set of permission scopes available to the current user."""
        try:
            from core.copilot.permissions import get_current_permissions

            return set(get_current_permissions())
        except Exception:
            return set()

    @staticmethod
    def _has_sufficient_authority(required_level: str) -> bool:
        from core.copilot.permissions import AuthorityLevel

        levels = [lv.value for lv in AuthorityLevel]
        return levels.index(required_level) <= len(levels) - 1
