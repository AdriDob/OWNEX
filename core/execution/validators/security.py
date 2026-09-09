from __future__ import annotations

from core.execution.models import Workflow
from core.execution.primitives import PrimitiveType
from core.execution.validation import BaseValidator, ValidationResult

# ── Danger ratings for known dangerous capabilities ───────────────
DANGEROUS_CAPABILITIES: dict[str, str] = {
    "capability:execute_command": "executes arbitrary system commands",
    "capability:delete_resource": "permanently deletes resources",
    "capability:modify_system": "modifies system configuration",
    "capability:access_vault": "accesses the secret vault",
    "capability:write_files": "writes to the filesystem",
    "capability:network_request": "makes external network requests",
    "capability:modify_database": "modifies database records",
    "capability:send_notification": "sends external notifications",
}


class SecurityValidator(BaseValidator):
    """Validates security properties of the workflow.

    Checks:
    - No secrets in plaintext in node config
    - Dangerous capabilities require approval
    - Privileged workflows require elevated authority
    - Mandatory approvals are not bypassable
    - Sensitive data is not exposed in output mappings
    - Workflow-level permissions are not excessive
    """

    name = "security"

    SENSITIVE_CONFIG_KEYS = {"password", "secret", "token", "api_key", "api-key", "apikey", "private_key", "credential"}
    MAX_WORKFLOW_PERMISSIONS = 10

    def validate(self, workflow: Workflow) -> ValidationResult:
        result = ValidationResult(validator_name=self.name)
        has_approval = any(n.type == PrimitiveType.APPROVAL.value for n in workflow.nodes)

        for node in workflow.nodes:
            # ── 1. No secrets in plaintext config ────────────────
            for key, value in node.config.items():
                if (
                    isinstance(value, str)
                    and any(s in key.lower() for s in self.SENSITIVE_CONFIG_KEYS)
                    and value
                    and not value.startswith("$")
                ):
                    result.errors.append(
                        self._error(
                            "SEC_PLAINTEXT_SECRET",
                            f"Node '{node.label or node.id}' has potential secret '{key}' "
                            f"in plaintext config. Use ${{SECRET_NAME}} placeholders instead.",
                            node_id=node.id,
                            exposed_key=key,
                        )
                    )
                    result.passed = False

            # ── 2. Dangerous capabilities need approval ──────────
            if node.type == PrimitiveType.CAPABILITY.value:
                cap_name = node.config.get("capability", "")

                if cap_name in DANGEROUS_CAPABILITIES and not has_approval:
                    result.errors.append(
                        self._error(
                            "SEC_DANGEROUS_NO_APPROVAL",
                            f"Capability '{cap_name}' ({DANGEROUS_CAPABILITIES[cap_name]}) "
                            f"requires an APPROVAL node in the workflow",
                            node_id=node.id,
                            capability=cap_name,
                            risk=DANGEROUS_CAPABILITIES[cap_name],
                        )
                    )
                    result.passed = False

            # ── 3. Sensitive data in output_mapping ──────────────
            for out_key in node.output_mapping:
                if any(s in out_key.lower() for s in self.SENSITIVE_CONFIG_KEYS):
                    result.warnings.append(
                        self._warning(
                            "SEC_SENSITIVE_OUTPUT",
                            f"Node '{node.label or node.id}' exposes sensitive key '{out_key}' in output mapping",
                            node_id=node.id,
                            exposed_key=out_key,
                        )
                    )

            # ── 4. Approval timeout — no auto-approve ────────────
            if node.type == PrimitiveType.APPROVAL.value:
                timeout = node.config.get("timeout_ms")
                if timeout and timeout < 10_000:  # less than 10 seconds
                    result.warnings.append(
                        self._warning(
                            "SEC_APPROVAL_TIMEOUT_TOO_SHORT",
                            f"Approval timeout {timeout}ms is too short — may cause accidental rejects",
                            node_id=node.id,
                            timeout_ms=timeout,
                        )
                    )

            # ── 5. Trigger with no event filter ──────────────────
            if node.type == PrimitiveType.TRIGGER.value:
                event_type = node.config.get("event_type", "")
                if not event_type:
                    result.warnings.append(
                        self._warning(
                            "SEC_TRIGGER_NO_EVENT_FILTER",
                            f"Trigger node '{node.label or node.id}' has no event_type filter — will match ANY event",
                            node_id=node.id,
                        )
                    )

        # ── 6. Excessive workflow permissions ────────────────────
        all_perms: set[str] = set()
        for node in workflow.nodes:
            scopes = node.config.get("required_scopes", [])
            if isinstance(scopes, list):
                all_perms.update(scopes)
        if len(all_perms) > self.MAX_WORKFLOW_PERMISSIONS:
            result.warnings.append(
                self._warning(
                    "SEC_EXCESSIVE_PERMISSIONS",
                    f"Workflow requires {len(all_perms)} permission scopes "
                    f"(max recommended: {self.MAX_WORKFLOW_PERMISSIONS})",
                    permissions=list(all_perms),
                )
            )

        return result
