from __future__ import annotations

from typing import Any

from core.setup.steps import define_step

INTEGRATIONS_SCHEMA: dict[str, Any] = {
    "type": "integration_list",
    "categories": [
        {
            "id": "platform",
            "label": "Plataformas Bug Bounty",
            "integrations": ["hackerone", "bugcrowd", "intigriti", "immunefi"],
        },
        {
            "id": "ai",
            "label": "Inteligencia Artificial",
            "integrations": ["openai", "gemini", "ollama"],
        },
        {
            "id": "messaging",
            "label": "Mensajería",
            "integrations": ["telegram", "discord", "gmail", "outlook"],
        },
        {
            "id": "exchange",
            "label": "Exchanges",
            "integrations": ["binance", "coinbase", "kraken"],
        },
    ],
}


@define_step(
    step_id="integrations",
    label="Integraciones",
    description="Conectar servicios externos (APIs, exchanges, mensajería)",
    icon="plug",
    order=4,
    required=False,
    schema=INTEGRATIONS_SCHEMA,
)
def execute(state: dict[str, Any]) -> dict[str, Any]:
    integrations = state.get("integrations", {})
    if not isinstance(integrations, dict):
        integrations = {}

    try:
        from core.integrations.registry import init_integration_registry

        registry = init_integration_registry()
        registry.refresh()
        summary = registry.summary()
        by_status = summary.get("by_status", {})

        return {
            "status": "ok",
            "message": f"{summary['total']} integraciones — {by_status.get('connected', 0)} conectadas",
            "data": {
                "total": summary["total"],
                "connected": by_status.get("connected", 0),
                "disconnected": by_status.get("disconnected", 0),
                "error": by_status.get("error", 0),
                "integrations": integrations,
                "registry_summary": summary,
            },
        }
    except Exception as exc:
        return {
            "status": "warning",
            "message": f"No se pudieron verificar integraciones: {exc}",
            "data": {"integrations": integrations, "error": str(exc)},
        }
