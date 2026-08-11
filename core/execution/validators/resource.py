from __future__ import annotations

import logging

from core.execution.models import Workflow
from core.execution.primitives import PrimitiveType
from core.execution.validation import BaseValidator, ValidationResult

logger = logging.getLogger("orion.core.execution.validators.resource")

# ── Known resource consumption per capability type ───────────────
CAPABILITY_RESOURCE_PROFILES: dict[str, dict[str, float]] = {
    "capability:scan_port": {"cpu": 0.3, "ram_mb": 50, "duration_ms": 30_000, "api_calls": 0, "tokens": 0},
    "capability:scan_subdomain": {"cpu": 0.2, "ram_mb": 30, "duration_ms": 15_000, "api_calls": 0, "tokens": 0},
    "capability:analyze_http": {"cpu": 0.1, "ram_mb": 20, "duration_ms": 5_000, "api_calls": 0, "tokens": 0},
    "capability:analyze_code": {"cpu": 0.4, "ram_mb": 100, "duration_ms": 60_000, "api_calls": 0, "tokens": 0},
    "capability:llm_analyze": {"cpu": 0.1, "ram_mb": 10, "duration_ms": 10_000, "api_calls": 1, "tokens": 2000},
    "capability:llm_decision": {"cpu": 0.1, "ram_mb": 10, "duration_ms": 8_000, "api_calls": 1, "tokens": 1000},
    "capability:send_email": {"cpu": 0.05, "ram_mb": 5, "duration_ms": 2_000, "api_calls": 1, "tokens": 0},
    "capability:webhook": {"cpu": 0.05, "ram_mb": 5, "duration_ms": 3_000, "api_calls": 1, "tokens": 0},
    "capability:query_database": {"cpu": 0.1, "ram_mb": 20, "duration_ms": 1_000, "api_calls": 0, "tokens": 0},
    "capability:execute_command": {"cpu": 0.3, "ram_mb": 50, "duration_ms": 10_000, "api_calls": 0, "tokens": 0},
}

DEFAULT_PROFILE = {"cpu": 0.2, "ram_mb": 30, "duration_ms": 10_000, "api_calls": 1, "tokens": 500}


class ResourceValidator(BaseValidator):
    """Estimates resource consumption before execution.

    Produces a resource budget and cost estimate for the workflow.
    """

    name = "resource"
    TOKEN_COST_PER_1K = 0.002  # $0.002 per 1K tokens (GPT-4o-mini roughly)

    def validate(self, workflow: Workflow) -> ValidationResult:
        result = ValidationResult(validator_name=self.name)
        node_map = {n.id: n for n in workflow.nodes}

        # ── Iterate once, aggregate ──────────────────────────────
        total_cpu = 0.0
        total_ram = 0.0
        total_duration = 0.0
        total_api = 0
        total_tokens = 0
        parallel_duration = 0.0  # track parallel branches separately

        for node in workflow.nodes:
            if node.type in (PrimitiveType.START.value, PrimitiveType.END.value):
                continue

            if node.type == PrimitiveType.WAIT.value or node.type == PrimitiveType.DELAY.value:
                wait_ms = node.config.get("duration_ms", 1000)
                total_duration += wait_ms
                continue

            if node.type == PrimitiveType.CAPABILITY.value:
                cap_name = node.config.get("capability", "")
                profile = CAPABILITY_RESOURCE_PROFILES.get(cap_name, DEFAULT_PROFILE)
                total_cpu += profile.get("cpu", 0.2)
                total_ram += profile.get("ram_mb", 30)
                total_duration += profile.get("duration_ms", 10_000)
                total_api += profile.get("api_calls", 1)
                total_tokens += profile.get("tokens", 500)

            if node.type == PrimitiveType.PARALLEL.value:
                branches = node.config.get("branches", [])
                branch_duration = 0.0
                for br_id in branches:
                    br_node = node_map.get(br_id)
                    if br_node and br_node.type == PrimitiveType.CAPABILITY.value:
                        cap_name = br_node.config.get("capability", "")
                        profile = CAPABILITY_RESOURCE_PROFILES.get(cap_name, DEFAULT_PROFILE)
                        branch_duration = max(branch_duration, profile.get("duration_ms", 10_000))
                parallel_duration += branch_duration

        # Adjust for parallelism: parallel branches run concurrently
        total_duration = max(total_duration, parallel_duration)

        estimated_cost = (total_tokens / 1000) * self.TOKEN_COST_PER_1K

        # ── Populate result ──────────────────────────────────────
        estimated = {
            "cpu": round(total_cpu, 2),
            "ram_mb": int(total_ram),
            "duration_ms": int(total_duration),
            "api_calls": total_api,
            "tokens": total_tokens,
            "cost_usd": round(estimated_cost, 4),
        }

        if total_cpu > 2.0:
            result.warnings.append(
                self._warning(
                    "RES_CPU_HIGH",
                    f"Estimated CPU usage ({round(total_cpu, 2)} cores) is high",
                    details=estimated,
                )
            )

        if total_ram > 200:
            result.warnings.append(
                self._warning(
                    "RES_RAM_HIGH",
                    f"Estimated RAM usage ({int(total_ram)} MB) is high",
                    details=estimated,
                )
            )

        if total_duration > 600_000:  # 10 minutes
            result.warnings.append(
                self._warning(
                    "RES_DURATION_HIGH",
                    f"Estimated duration ({int(total_duration // 1000)}s) is high",
                    details=estimated,
                )
            )

        if total_api > 50:
            result.warnings.append(
                self._warning(
                    "RES_API_CALLS_HIGH",
                    f"Estimated API calls ({total_api}) is high",
                    details=estimated,
                )
            )

        if estimated_cost > 0.50:
            result.warnings.append(
                self._warning(
                    "RES_COST_HIGH",
                    f"Estimated cost (${round(estimated_cost, 4):.4f}) exceeds $0.50",
                    details=estimated,
                )
            )

        result.suggestions.append(
            self._suggestion(
                "RES_ESTIMATE",
                f"Estimated: {estimated['cpu']} CPU, {estimated['ram_mb']}MB RAM, "
                f"{estimated['duration_ms'] // 1000}s, {estimated['api_calls']} API calls, "
                f"${estimated['cost_usd']:.4f} cost",
                details=estimated,
            )
        )

        return result
