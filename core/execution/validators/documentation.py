from __future__ import annotations

from core.execution.models import Workflow
from core.execution.primitives import PrimitiveType
from core.execution.validation import BaseValidator, ValidationResult


class DocumentationValidator(BaseValidator):
    """Validates that every capability referenced in the workflow has proper documentation.

    Checks:
    - Capability has a description in its contract
    - Capability contract declares inputs and outputs
    - Capability contract declares events (published/consumed)
    - Capability contract has usage examples
    - Capability contract has config schema
    - Node-level documentation fields are filled (label, description)
    """

    name = "documentation"

    def validate(self, workflow: Workflow) -> ValidationResult:
        result = ValidationResult(validator_name=self.name)
        contracts = self._get_capability_contracts()

        # ── Check node-level documentation ───────────────────────
        for node in workflow.nodes:
            if not node.label:
                result.suggestions.append(
                    self._suggestion(
                        "DOC_NODE_NO_LABEL",
                        f"Node '{node.id}' has no label — add a descriptive label",
                        node_id=node.id,
                    )
                )

            if node.type not in (PrimitiveType.START.value, PrimitiveType.END.value) and not node.description:
                result.suggestions.append(
                    self._suggestion(
                        "DOC_NODE_NO_DESCRIPTION",
                        f"Node '{node.label or node.id}' has no description",
                        node_id=node.id,
                    )
                )

        # ── Check capability-level documentation ─────────────────
        for node in workflow.nodes:
            if node.type != PrimitiveType.CAPABILITY.value:
                continue

            cap_name = node.config.get("capability", "")
            if not cap_name:
                continue

            contract = contracts.get(cap_name)

            if not contract:
                result.warnings.append(
                    self._warning(
                        "DOC_NO_CONTRACT",
                        f"Capability '{cap_name}' has no registered contract in Documentation Registry",
                        node_id=node.id,
                        capability=cap_name,
                    )
                )
                continue

            # ── Contract description ─────────────────────────────
            if not contract.get("description"):
                result.warnings.append(
                    self._warning(
                        "DOC_CONTRACT_NO_DESCRIPTION",
                        f"Capability '{cap_name}' contract has no description",
                        node_id=node.id,
                        capability=cap_name,
                    )
                )

            # ── Inputs documented ────────────────────────────────
            inputs = contract.get("inputs", [])
            config_schema = contract.get("config_schema", {})
            if not inputs and not config_schema:
                result.suggestions.append(
                    self._suggestion(
                        "DOC_CONTRACT_NO_INPUTS",
                        f"Capability '{cap_name}' contract declares no inputs or config schema",
                        node_id=node.id,
                        capability=cap_name,
                    )
                )

            # ── Outputs documented ───────────────────────────────
            outputs = contract.get("outputs", [])
            if not outputs:
                result.suggestions.append(
                    self._suggestion(
                        "DOC_CONTRACT_NO_OUTPUTS",
                        f"Capability '{cap_name}' contract declares no outputs",
                        node_id=node.id,
                        capability=cap_name,
                    )
                )

            # ── Events documented ────────────────────────────────
            events_pub = contract.get("events_published", [])
            events_con = contract.get("events_consumed", [])
            if not events_pub and not events_con:
                result.suggestions.append(
                    self._suggestion(
                        "DOC_CONTRACT_NO_EVENTS",
                        f"Capability '{cap_name}' contract declares no events (published or consumed)",
                        node_id=node.id,
                        capability=cap_name,
                    )
                )

            # ── Usage examples ───────────────────────────────────
            examples = contract.get("usage_examples", [])
            if not examples:
                result.suggestions.append(
                    self._suggestion(
                        "DOC_CONTRACT_NO_EXAMPLES",
                        f"Capability '{cap_name}' contract has no usage examples",
                        node_id=node.id,
                        capability=cap_name,
                    )
                )

        return result

    @staticmethod
    def _get_capability_contracts() -> dict[str, dict]:
        """Fetch all registered capability contracts from the Documentation Registry."""
        try:
            from core.documentation.registrar import list_all_modules

            contracts: dict[str, dict] = {}
            for mod in list_all_modules():
                for cap in mod.capabilities:
                    contracts[cap.name] = {
                        "description": cap.description,
                        "inputs": getattr(cap, "inputs", []),
                        "outputs": getattr(cap, "outputs", []),
                        "events_published": getattr(cap, "events_published", []),
                        "events_consumed": getattr(cap, "events_consumed", []),
                        "config_schema": getattr(cap, "config_schema", {}),
                        "usage_examples": getattr(cap, "usage_examples", []),
                    }
            return contracts
        except Exception:
            return {}
